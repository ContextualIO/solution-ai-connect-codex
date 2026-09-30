# Security

Report suspected vulnerabilities through [GitHub private vulnerability reporting](https://github.com/ContextualIO/solution-ai-connect-codex/security/advisories/new). Do not open a public issue containing an exploit, credentials, customer data, or private diagnostic output.

Include affected versions, a minimal synthetic reproduction, and the expected versus observed behavior. Share only the information needed to investigate. Never paste live access tokens or tenant records.

Security fixes target the latest adapter on `main`. Older adapter builds do not have a separate maintenance channel. The pinned public upstream release and adapter build are recorded in `UPSTREAM.json` and the plugin manifest.

The update hook reads a public manifest over HTTPS and stores timestamps and notified versions locally. It does not install code or send tenant data or credentials. Installation, hook trust, and platform access remain separate host and user controls.
