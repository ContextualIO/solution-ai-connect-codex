# Codex adapter releases

## Prepare and review

1. Work on a branch. Keep exploratory installs, personal test versions, raw validation output, and private evidence outside the release branch.
2. For adapter-only changes, retain the upstream semantic version and `UPSTREAM.json`. As the closing content change, set the plugin manifest to `<upstream-version>+codex.YYYYMMDDHHMMSS` using UTC, and describe the release in the README's adapter notes. Update `UPSTREAM.json` only when synchronizing a different public upstream tag.
3. Run repository validation, unit tests, and secret scanning. Review the full diff and all publication metadata against [CONTRIBUTING.md](../CONTRIBUTING.md). Check licenses, repository links, local path exclusions, and install instructions.
4. Open a PR. Wait for CI and the required reviewer approvals. Read Qodo's review and all PR/inline comments when configured, address findings, and check for new findings after revisions. Explain with evidence when a finding needs no change. Do not treat missing automation output as approval or bypass organization review requirements.
5. Merge through the repository's allowed method. Installable releases are published on `main`; the update checker follows that branch. Create an annotated `v<full-adapter-version>` tag on the released commit, and push that exact tag. Never push all local tags.

## Verify the update

Keep the previous release installed until the new version is available on its configured source. Run that installed checker and confirm `update_available` with the two expected versions. Do not modify installed code, cache contents, or hook trust records to manufacture detection.

For a distribution-source migration, first publish the reviewed release on the previous channel so its installed checker can detect the version. Then register the public marketplace through the CLI and install the same reviewed release. Preserve intentional custom refs; do not silently move users from a pinned source.

Refresh the marketplace and install through the supported commands:

```bash
codex plugin marketplace upgrade contextual-io
codex plugin add solution-ai-connect@contextual-io
codex plugin list --marketplace contextual-io --json
```

Confirm the installed version and enabled state, and that its checker reports `no_update`. Restart desktop and start a new chat to load changed definitions. Hook trust is controlled by the host and must be reviewed through its supported UI; installation is not proof that hooks are trusted.

To test the hook command without consuming normal notification history, run the previous installed checker with `--hook` and `PLUGIN_DATA` set to an empty temporary directory. Expect one `systemMessage`, then no second notice. This verifies the command only; native delivery requires a supported local session and a trusted hook.

## Repository protections

Retain organization default-branch rules, use pull requests, and restrict workflow token permissions. Enable available secret scanning, push protection, dependency alerts, and private vulnerability reporting. Pin third-party Actions to reviewed commit SHAs and verify downloaded tool checksums. Review dependency update PRs before merging.

Fresh public snapshots contain only reviewed tracked content and public provenance. Do not import private Git history, review conversations, local notes, or test exports. Keep private audit evidence outside the public repository.
