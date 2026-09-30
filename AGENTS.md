# Repository workflow

- Follow [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/RELEASING.md](docs/RELEASING.md). Public-content rules apply to code, documentation, commit messages, tags, pull requests, and comments.
- Keep private notes, tenant data, credentials, personal paths, and internal discussion links outside the repository. Use verified product behavior and neutral synthetic examples. Review tracked content before pushing; ignore rules and secret scans do not replace review.

- Make changes on a branch and open a pull request.
- Qodo AI review is enabled for this repository. Wait for its review, read its findings (including review comments and PR comments), and address them before treating the PR as ready to merge. Explain with evidence when a finding does not warrant a code change. Check for new findings after revisions; do not equate an absent review with approval.
- Run `python3 -m unittest discover -s tests -v` for update-checker changes. Validate changed skills and plugin manifests before publishing.
- Bump the Codex adapter build timestamp when publishing changed plugin files. Keep the upstream version and `UPSTREAM.json` unchanged unless actually synchronizing a new upstream release.
- For update verification, test the previously installed checker against the newly published version before upgrading. Do not modify the installed cache or hook trust records to force a successful result.
- Put operational guidance in the skill used at the decision point, not only in repository instructions. Write AI-consumed guidance in present tense and keep upstream synchronization separate from adapter changes.
