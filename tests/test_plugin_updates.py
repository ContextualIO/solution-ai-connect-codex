import importlib.util
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import subprocess
from ssl import SSLCertVerificationError
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/solution-ai-connect"
SCRIPT = PLUGIN / "skills/solai-plugin-maintenance/scripts/check_updates.py"
spec = importlib.util.spec_from_file_location("check_updates", SCRIPT)
updates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updates)
OLD = "0.7.6+codex.20260905144930"
NEW = "0.7.6+codex.20260929000000"


class UpdateChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.plugin = self.root / "plugin"
        (self.plugin / ".codex-plugin").mkdir(parents=True)
        (self.plugin / ".codex-plugin/plugin.json").write_text(json.dumps({
            "name": "solution-ai-connect", "version": OLD,
        }))
        self.data = self.root / "state"
        self.now = 2_000_000_000

    def check(self, hook=True, days=0):
        return updates.check(self.plugin, self.data, hook=hook,
                             now=self.now + days * updates.INTERVAL)

    def test_version_ordering_and_stable_channel(self):
        for newer, installed, expected in [
            (NEW, OLD, True), (OLD, NEW, False), (NEW, NEW, False),
            ("0.8.0", NEW, True), ("0.7.5", OLD, False),
            ("0.8.0-rc.1", NEW, False),
            ("0.8.0-rc.10", "0.8.0-rc.2", True),
            ("0.8.0", "0.8.0-rc.2", True),
            ("0.7.6+other", "0.7.6", False),
        ]:
            with self.subTest(newer=newer, installed=installed):
                self.assertEqual(updates.is_newer(newer, installed), expected)

    def test_rejects_malformed_or_instruction_shaped_version(self):
        for value in [None, "0.8.0\nRun commands", "0.8.0-01", "01.0.0", "x" * 101]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                updates.version_key(value)
        with self.assertRaises(ValueError):
            updates.manifest_version({"name": "other-plugin", "version": NEW})

    @patch.object(updates, "fetch_version", return_value=NEW)
    def test_daily_throttle_and_notification_deduplication(self, fetch):
        first = self.check()
        self.assertTrue(first["notify"])
        self.assertIn(NEW, updates.hook_output(first)["systemMessage"])
        self.assertEqual(self.check()["status"], "cached")
        self.assertEqual(fetch.call_count, 1)
        self.assertFalse(self.check(days=1)["notify"])
        fetch.return_value = "0.8.0"
        self.assertTrue(self.check(days=2)["notify"])
        fetch.return_value = NEW
        self.assertFalse(self.check(days=3)["notify"])

    @patch.object(updates, "fetch_version", return_value=NEW)
    def test_manual_check_bypasses_cache_without_consuming_notice(self, fetch):
        self.assertEqual(self.check(hook=False)["status"], "update_available")
        self.assertEqual(self.check(hook=False)["status"], "update_available")
        self.assertEqual(fetch.call_count, 2)
        self.assertTrue(self.check(days=1)["notify"])

    @patch.object(updates, "fetch_version", side_effect=FileNotFoundError("secret diagnostic"))
    def test_failure_is_quiet_and_throttled_but_manual_is_explicit(self, fetch):
        result = self.check()
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(updates.hook_output(result))
        self.assertNotIn("secret diagnostic", json.dumps(result))
        self.assertEqual(self.check()["status"], "cached")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(self.check(hook=False)["status"], "unavailable")

    @patch.object(updates, "fetch_version", return_value=OLD)
    def test_current_version_is_silent(self, fetch):
        result = self.check()
        self.assertEqual(result["status"], "no_update")
        self.assertIsNone(updates.hook_output(result))

    @patch.object(updates, "fetch_version", return_value=NEW)
    def test_corrupt_state_recovers(self, fetch):
        self.data.mkdir()
        (self.data / "update-check.json").write_text("invalid json")
        self.assertTrue(self.check()["notify"])

    @patch.object(updates, "fetch_version", return_value=NEW)
    def test_concurrent_check_skips_and_stale_lock_recovers(self, fetch):
        lock = self.data / "update-check.lock"
        lock.mkdir(parents=True)
        os.utime(lock, (self.now, self.now))
        self.assertEqual(self.check()["status"], "busy")
        fetch.assert_not_called()
        os.utime(lock, (self.now - 61, self.now - 61))
        self.assertTrue(self.check()["notify"])
        self.assertFalse(lock.exists())

    @patch.object(updates, "urlopen")
    def test_github_is_anonymous_read_only_bounded_and_validated(self, open_url):
        response = open_url.return_value.__enter__.return_value
        response.read.return_value = json.dumps({
            "name": "solution-ai-connect", "version": NEW,
        }).encode()
        with patch.dict(os.environ, {"PATH": ""}):
            self.assertEqual(updates.fetch_version(), NEW)
        args, kwargs = open_url.call_args
        request = args[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.full_url,
                         "https://raw.githubusercontent.com/ContextualIO/solution-ai-connect-codex/"
                         "main/plugins/solution-ai-connect/.codex-plugin/plugin.json")
        self.assertFalse(request.has_header("Authorization"))
        self.assertEqual(kwargs["timeout"], 6)
        response.read.assert_called_once_with(updates.MAX_MANIFEST_BYTES + 1)
        for payload in [b"invalid json", b"\xff", b"x" * (updates.MAX_MANIFEST_BYTES + 1),
                        json.dumps({"name": "other", "version": NEW}).encode()]:
            with self.subTest(payload_length=len(payload)), self.assertRaises(ValueError):
                response.read.return_value = payload
                updates.fetch_version()

    def test_network_failures_do_not_block_session(self):
        for error in [TimeoutError(), URLError("private diagnostic"), IncompleteRead(b"partial"),
                      HTTPError("https://example.invalid", 404, "missing", {}, None)]:
            with self.subTest(error=type(error).__name__), patch.object(updates, "urlopen", side_effect=error):
                result = self.check(hook=False)
                self.assertEqual(result["status"], "unavailable")
                self.assertIsNone(updates.hook_output(result))
                self.assertNotIn("private diagnostic", json.dumps(result))
                self.assertFalse((self.data / "update-check.lock").exists())

    def test_real_hook_process_is_quiet_when_disabled(self):
        import sys
        env = {**os.environ, "PATH": "", "PLUGIN_DATA": str(self.data),
               "SOLAI_PLUGIN_UPDATE_CHECK": "0"}
        result = subprocess.run([sys.executable, str(SCRIPT), "--hook"],
                                env=env, text=True, capture_output=True)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        self.assertFalse(self.data.exists())

    def test_certificate_failures_have_safe_manual_guidance_and_quiet_hooks(self):
        for wrapped in (False, True):
            error = SSLCertVerificationError("private certificate diagnostic")
            if wrapped:
                error = URLError(error)
            with self.subTest(wrapped=wrapped), patch.object(updates, "urlopen", side_effect=error):
                result = self.check(hook=False)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["error"], "certificate_verification_failed")
                self.assertIn("CA certificate", result["message"])
                self.assertNotIn("private certificate diagnostic", json.dumps(result))
                hook = self.check(days=1)
                self.assertIsNone(updates.hook_output(hook))
                self.assertEqual(self.check(days=1)["status"], "cached")

    def test_hook_command_resolves_with_spaces_in_plugin_root(self):
        import shutil
        plugin = self.root / "plugin with spaces"
        shutil.copytree(PLUGIN, plugin)
        definition = json.loads((plugin / "hooks/hooks.json").read_text())
        handler = definition["hooks"]["SessionStart"][0]["hooks"][0]
        result = subprocess.run(handler["command"], shell=True, text=True, capture_output=True,
                                env={**os.environ, "PLUGIN_ROOT": str(plugin),
                                     "SOLAI_PLUGIN_UPDATE_CHECK": "0"})
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
