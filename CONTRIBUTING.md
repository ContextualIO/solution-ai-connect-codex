# Contributing

This public repository packages Solution AI Connect for Codex. Product content originates in the tagged public release recorded in `UPSTREAM.json`; host-specific behavior lives in the adapter. Keep changes focused and explain which behavior they alter.

## Public-content standards

Review every public surface before pushing: tracked files, examples, commit messages, tags, PR titles and descriptions, review replies, and release notes.

- Use synthetic examples and generic placeholders. Exclude customer or tenant records, session and installation identifiers, personal filesystem paths, personal contact details, and credentials. Normal contributor attribution in Git metadata is appropriate; use your intended public work identity.
- Keep internal discussion links, private repository references, employee or reporter narratives, and incident speculation out of published material. Describe the product behavior, change, and verification. Ticket labels may provide traceability without copying private ticket prose.
- Do not include secret-shaped sample tokens, cookies, authorization headers, or raw diagnostic dumps. Project operational data to the non-secret fields needed for the task before inspection.
- Keep local notes, audit evidence, authentication state, and personal test exports outside tracked content. Ignore rules help prevent mistakes but do not remove already tracked files or protect commit messages.
- Ground technical claims in the implementation, public documentation, or a reproducible check. State the scope of verification; a successful CLI test does not establish desktop or cloud compatibility.

## Changes and review

Create a branch and open a pull request. Describe the concrete problem and resulting behavior, with the verification needed to assess it. Address human and automated review findings. Where Qodo is configured, read its PR comments, inline comments, and reviews for the current revision; an absent review is not approval.

Keep AI-consumed instructions in present tense. Place operational rules in the relevant skill at the point where an agent decides what to do. Preserve narrowly scoped host adaptations when synchronizing upstream; do not import a whole local working directory.

Run locally before review:

```bash
python3 scripts/validate_repository.py
python3 -m unittest discover -s tests -v
gitleaks dir . --redact --no-banner
```

The repository validator requires Python 3.11 or newer. The update checker uses Python 3 and the standard library, with no package installation or GitHub login. CI also scans Git history; a clean scan supplements manual public-content review.

See [the release guide](docs/RELEASING.md) for versioning and publication. Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
