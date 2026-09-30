# Solution AI Connect for Codex

This repository adapts the public Solution AI Connect content for Codex packaging and runtime conventions.

The canonical product content remains in [`ContextualIO/solution-ai-connect`](https://github.com/ContextualIO/solution-ai-connect). The adapter is synchronized from a tagged upstream release, then receives only the changes required for Codex manifests, skill paths, permissions, namespacing, and installation.

## Shape

- `.agents/plugins/marketplace.json` exposes a repo-local Codex marketplace.
- `plugins/solution-ai-connect/.codex-plugin/plugin.json` is the Codex plugin manifest.
- `plugins/solution-ai-connect/skills/` contains the portable skill/reference content.
- `plugins/solution-ai-connect/.mcp.json` bundles the Solution AI Knowledge and local Flow Editor MCP servers.
- `plugins/solution-ai-connect/hooks/hooks.json` provides an optional daily update notice at session startup/resume.
- `.codex/agents/` contains optional project-scoped custom-agent drafts. Codex does not install these files as part of the plugin.
- `UPSTREAM.json` records the exact public release used for the current synchronization.

## Current Status

The plugin is intended for Git-backed Codex marketplace installation. The current adapter content is synchronized from upstream `v0.7.6`.

Codex custom subagents are TOML files under `~/.codex/agents/` or `.codex/agents/`. They are separate from the plugin package.

## Repo-backed distribution

Add this repository as a marketplace in Codex. The marketplace entry then resolves the plugin from the repo-relative local path in `.agents/plugins/marketplace.json`: `./plugins/solution-ai-connect`.

```bash
codex plugin marketplace add ContextualIO/solution-ai-connect-codex
codex plugin add solution-ai-connect@contextual-io
```

The repository is public; installation and update checks do not require a GitHub account or the GitHub CLI. Git is required for the Git-backed marketplace. ChatGPT desktop uses the Codex plugin runtime for this local installation. Contextual platform operations still require the applicable Contextual login and permissions.

### Move an existing installation to the public source

Inspect `codex plugin marketplace list --json`. If `contextual-io` is registered from an earlier distribution source, switch that registration once before using the normal update commands. Preserve any deliberately customized source or pinned ref unless you intend to change it. Record the original source and ref so they can be restored if registration fails.

```bash
codex plugin marketplace remove contextual-io
codex plugin marketplace add ContextualIO/solution-ai-connect-codex
codex plugin add solution-ai-connect@contextual-io
```

Run each command only after the preceding command succeeds. Removing the marketplace registration is separate from uninstalling the plugin; do not remove the installed plugin or edit its cache. If adding the public source fails, restore the recorded registration with `codex plugin marketplace add` and report the failure. Confirm the public source and installed version with `codex plugin list --marketplace contextual-io --json`. An update notice does not by itself change the registered source.

### Refresh the public installation

Refresh an existing Git-backed installation with:

```bash
codex plugin marketplace upgrade contextual-io
codex plugin add solution-ai-connect@contextual-io
```

Restart desktop and start a new chat after reinstalling so the updated skills and MCP definitions are loaded. If the standalone `codex` command is unavailable, use the working CLI bundled with the desktop app. On macOS this may be `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`.

### Update notices and manual checks

After installing, review and trust the plugin's startup hook through the host's hook review controls (`/hooks` in the Codex CLI). Installation alone does not trust a hook, and administrator policy can disable hooks. Command hooks run in local Work/Codex sessions; Work Cloud orchestration does not run plugin command hooks, even with local computer access. Use the maintenance skill for manual checks on those surfaces. See [OpenAI's hook documentation](https://learn.chatgpt.com/docs/hooks).

The checker requires Python 3 on the desktop process's PATH. It fetches the public manifest over HTTPS without credentials or a GitHub CLI dependency. It reads only the adapter manifest on `main`; it never installs updates or changes authentication. It runs in the background on session startup/resume, attempts at most one check per 24 hours, and displays a notice once per newer version. Network and runtime failures are silent during startup. This is a session-triggered check, not a background scheduler when the app is closed. Hook notices appear at the next safe conversation point.

Python needs a working CA certificate setup for HTTPS verification. A manual check reports certificate verification failures separately with repair guidance; use the Python distributor's certificate setup instructions and keep TLS verification enabled. Hook mode remains quiet on those failures.

Ask **“check for Solution AI Connect updates”** for an immediate check, or **“update Solution AI Connect”** to use the `solai-plugin-maintenance` skill. Explicit checks report failures and bypass the daily limit. Automatic checks can be disabled with `SOLAI_PLUGIN_UPDATE_CHECK=0` in the desktop process environment. The hook stores only check timestamps and notified versions in its `PLUGIN_DATA` directory; the manual fallback is `~/.codex/plugins/data/contextual-io/solution-ai-connect/` (or under `CODEX_HOME` when set).

Existing installations must be updated once using the commands above to receive this checker.

### Adapter release notes

- **0.7.6+codex.20260930190143:** Publish the Codex adapter under ContextualIO with anonymous update checks, contributor and release guidance, automated validation, and secret scanning. Upstream content remains at `v0.7.6`.

- **0.7.6+codex.20260929191327:** Document PR review and end-to-end update verification. This build-version increment provides a real update for installations of the initial checker release to detect; runtime behavior is unchanged.
- **0.7.6+codex.20260929000000:** Add daily, once-per-version startup update notices and the plugin maintenance skill. Upstream content remains at `v0.7.6`.

For adapter-only releases, increment the `+codex.YYYYMMDDHHMMSS` build timestamp in the plugin manifest (UTC). The checker compares normal semantic-version precedence and, for otherwise equal versions, this adapter timestamp. Stable installs ignore prereleases; unrelated build metadata does not imply a newer version. Publish installable changes on `main`, which is the update channel checked by the hook; checks against custom pinned sources should be performed manually.

Run the update-checker tests with `python3 -m unittest discover -s tests -v`.

### Verify a published update

Keep the previous plugin version installed while a version-bump PR is reviewed and merged. Run that installed version's maintenance checker without `--hook`; it should report `update_available` with the installed and newly published versions. Then refresh the marketplace, install the update, and confirm the installed version with `codex plugin list --marketplace contextual-io --json`. The newly installed checker should report `no_update`.

To exercise the automatic notification separately, run the previous installed script with `--hook` and `PLUGIN_DATA` pointing to an empty temporary directory. Its first run should emit a `systemMessage`; a second run should emit nothing. Using temporary state avoids consuming or changing the user's normal notification history. This tests the hook command; native delivery still requires a trusted hook and a supported local session.

## Synchronization policy

- Treat the canonical public repository as read-only during adapter work.
- Synchronize only tracked content from an upstream tag.
- Keep host-specific changes limited to the Codex adapter.
- Do not copy local working files, private notes, personal paths, tenant identifiers, or internal references into this repository.
- Validate the plugin and every skill before publishing an adapter update.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for public-content standards, [the release guide](docs/RELEASING.md) for review and verification, and [SECURITY.md](SECURITY.md) for private vulnerability reporting. The repository and bundled upstream content are [MIT licensed](LICENSE).
