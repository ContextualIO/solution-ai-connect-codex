#!/usr/bin/env python3
"""Read-only GitHub update check; --hook emits only a new-version notice."""

import argparse
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
from ssl import SSLCertVerificationError
from urllib.error import URLError
from urllib.request import Request, urlopen
import tempfile
import time

REPOSITORY = "ContextualIO/solution-ai-connect-codex"
PLUGIN_NAME = "solution-ai-connect"
MANIFEST = "plugins/solution-ai-connect/.codex-plugin/plugin.json"
INTERVAL = 24 * 60 * 60
TIMEOUT = 6
MAX_MANIFEST_BYTES = 64 * 1024
VERSION = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)


def version_key(value):
    if not isinstance(value, str) or len(value) > 100:
        raise ValueError("Invalid plugin version")
    match = VERSION.fullmatch(value)
    if not match:
        raise ValueError("Invalid plugin version")
    major, minor, patch, pre, build = match.groups()
    identifiers = pre.split(".") if pre else []
    if any(p.isdigit() and len(p) > 1 and p.startswith("0") for p in identifiers):
        raise ValueError("Invalid prerelease version")
    prerelease = tuple((0, int(p)) if p.isdigit() else (1, p) for p in identifiers)
    # Adapter-only releases retain the upstream version and bump this timestamp.
    stamp = re.fullmatch(r"codex\.([0-9]{14})", build or "")
    return (int(major), int(minor), int(patch)), not bool(pre), prerelease, int(stamp[1]) if stamp else 0


def is_newer(candidate, installed):
    remote, local = version_key(candidate), version_key(installed)
    # Stable installations are never prompted to install a prerelease.
    if local[1] and not remote[1]:
        return False
    return remote > local


def manifest_version(document):
    if not isinstance(document, dict) or document.get("name") != PLUGIN_NAME:
        raise ValueError("Unexpected plugin manifest")
    version = document.get("version")
    version_key(version)
    return version


def fetch_version():
    # Public HTTPS only: no CLI dependency, credentials, or remote code execution.
    request = Request(
        f"https://raw.githubusercontent.com/{REPOSITORY}/main/{MANIFEST}",
        headers={"Accept": "application/json", "User-Agent": "solution-ai-connect-update-check"},
    )
    with urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read(MAX_MANIFEST_BYTES + 1)
    if len(payload) > MAX_MANIFEST_BYTES:
        raise ValueError("Plugin manifest exceeds size limit")
    return manifest_version(json.loads(payload))


def read_state(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def check(plugin_root, data_dir, *, hook=False, now=None):
    now = time.time() if now is None else now
    installed = manifest_version(json.loads((plugin_root / ".codex-plugin/plugin.json").read_text()))
    base = {"installed_version": installed, "repository": REPOSITORY}
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = data_dir / "update-check.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        # Recover a lock left by a killed hook; requests time out well before this.
        try:
            if now - lock.stat().st_mtime <= 60:
                return {**base, "status": "busy"}
            lock.rmdir()
            lock.mkdir()
        except OSError:
            return {**base, "status": "busy"}
    try:
        state_path = data_dir / "update-check.json"
        state = read_state(state_path)
        last_check = state.get("last_checked", 0)
        if hook and isinstance(last_check, (int, float)) and 0 <= now - last_check < INTERVAL:
            return {**base, "status": "cached"}
        # Save the attempt before networking, so failures are throttled too.
        state["last_checked"] = now
        write_state(state_path, state)
        try:
            latest = fetch_version()
        except (OSError, ValueError, HTTPException) as error:
            reason = error.reason if isinstance(error, URLError) else error
            if isinstance(reason, SSLCertVerificationError):
                return {**base, "status": "unavailable", "error": "certificate_verification_failed",
                        "message": "Python could not verify GitHub's HTTPS certificate. Repair Python's CA certificate setup using its distributor's instructions; do not disable TLS verification. No GitHub login is required."}
            return {**base, "status": "unavailable",
                    "message": "Could not read the public GitHub manifest. Check network connectivity and repository availability; no GitHub login is required."}
        result = {**base, "latest_version": latest,
                  "status": "update_available" if is_newer(latest, installed) else "no_update"}
        if hook and result["status"] == "update_available":
            notified = state.get("notified_versions", [])
            if not isinstance(notified, list):
                notified = []
            result["notify"] = latest not in notified
            if result["notify"]:
                state["notified_versions"] = notified + [latest]
                write_state(state_path, state)
        return result
    finally:
        lock.rmdir()


def hook_output(result):
    if not result.get("notify"):
        return None
    return {"systemMessage": (
        f"Solution AI Connect {result['latest_version']} is available "
        f"(installed: {result['installed_version']}). "
        "Want to update? Ask ‘update Solution AI Connect’ to review and install it."
    )}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hook", action="store_true", help="Daily, quiet SessionStart check")
    args = parser.parse_args()
    if args.hook and os.environ.get("SOLAI_PLUGIN_UPDATE_CHECK") == "0":
        return 0
    root = Path(__file__).resolve().parents[3]
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    data = Path(os.environ.get("PLUGIN_DATA", str(codex_home / "plugins/data/contextual-io/solution-ai-connect")))
    try:
        result = check(root, data, hook=args.hook)
    except (OSError, ValueError):
        result = {"status": "unavailable", "message": "Could not read the plugin manifest or update-check state."}
    output = hook_output(result) if args.hook else result
    if output is not None:
        print(json.dumps(output))
    # Hook failures must not interrupt the user's session.
    return 0 if args.hook or result["status"] not in ("unavailable", "busy") else 1


if __name__ == "__main__":
    raise SystemExit(main())
