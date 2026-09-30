#!/usr/bin/env python3
"""Validate this adapter's manifests, constrained skill frontmatter, and helpers."""

import ast
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/solution-ai-connect"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate():
    manifest = read_json(PLUGIN / ".codex-plugin/plugin.json")
    upstream = read_json(ROOT / "UPSTREAM.json")
    require(manifest["name"] == "solution-ai-connect", "Unexpected plugin name")
    require(re.fullmatch(r"\d+\.\d+\.\d+\+codex\.\d{14}", manifest["version"]),
            "Expected an upstream version plus Codex UTC build timestamp")
    require(manifest["version"].split("+")[0] == upstream["tag"].removeprefix("v"),
            "Manifest base version must match the recorded upstream tag")
    require(manifest["repository"] == "https://github.com/ContextualIO/solution-ai-connect-codex",
            "Unexpected distribution repository")
    for key in ("skills", "mcpServers"):
        path = (PLUGIN / manifest[key]).resolve()
        require(path.is_relative_to(PLUGIN) and path.exists(), f"Invalid manifest path: {key}")
    marketplace = read_json(ROOT / ".agents/plugins/marketplace.json")
    require(marketplace["name"] == "contextual-io", "Unexpected marketplace identity")
    require(len(marketplace["plugins"]) == 1, "Expected one marketplace entry")
    entry = marketplace["plugins"][0]
    require(entry["name"] == manifest["name"] and entry["source"] == {
        "source": "local", "path": "./plugins/solution-ai-connect",
    }, "Marketplace entry must resolve the bundled plugin")
    require(read_json(PLUGIN / ".mcp.json")["mcpServers"], "Missing MCP servers")
    hooks = read_json(PLUGIN / "hooks/hooks.json")["hooks"]["SessionStart"]
    require(hooks and all(item["hooks"] for item in hooks), "Missing startup hook")

    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    require(bool(skills), "No skills found")
    for path in skills:
        text = path.read_text(encoding="utf-8")
        # The adapter deliberately uses two unquoted single-line YAML scalars.
        # Reject other forms rather than pretending to parse arbitrary YAML.
        match = re.match(r"\A---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n", text)
        require(match is not None, f"Unsupported skill frontmatter: {path.relative_to(ROOT)}")
        name, description = match.groups()
        require(name == path.parent.name and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
                and len(name) <= 64, f"Invalid skill name: {name}")
        require(0 < len(description) <= 1024 and ": " not in description
                and " #" not in description and description[0] not in "{}[]&*!|>'\"%@`"
                and "<" not in description and ">" not in description,
                f"Invalid single-line skill description: {name}")
        require(text[match.end():].strip(), f"Empty skill body: {name}")

    helpers = sorted((PLUGIN / "skills").rglob("*.py")) + sorted((ROOT / "scripts").glob("*.py"))
    for path in helpers:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
    for path in (ROOT / ".codex/agents").glob("*.toml"):
        tomllib.loads(path.read_text(encoding="utf-8"))
    require((ROOT / "LICENSE").read_bytes() == (PLUGIN / "LICENSE").read_bytes(),
            "Root and bundled licenses must agree")
    print(f"Validated plugin and marketplace manifests, {len(skills)} skills, helpers, agents, and licenses.")


if __name__ == "__main__":
    validate()
