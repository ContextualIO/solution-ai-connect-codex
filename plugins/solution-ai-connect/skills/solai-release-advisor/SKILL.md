---
name: solai-release-advisor
description: Advise on the next release of a Contextual service you own — inspect which component bumps are available since the last release, preview the per-component change set, and compose the Build (pinning selected component versions via `services patch`) before snapping the release in the workspace UI. Also answers read-only "what's owned / what changed?" inventory questions. Produces decision support only; the actual release snap / install / update is performed in the workspace UI. Requires local shell access and an authenticated `ctxl` config.
---

# SolAI Release Advisor

This skill wraps the `services` and `servicereleases` CLI surface (documented in `solai-cli/cli-reference.md`) to help plan the next release of a service **you own** from the CLI / an agent context — composing the **Build** (the working manifest for the next Release Version) by pinning selected component versions, and assessing what each bump changes (behavioral vs cosmetic) before you snap. The workspace Build tab offers the same composition plus a side-by-side version diff in the browser; this skill is the scriptable, headless counterpart for terminal- and agent-driven workflows.

It produces structured decision support; it does not enact installs, updates, or release snaps. Those steps remain in the workspace web app.

## When to use

- Before **cutting a new release** of an owned service — to inspect which direct dependencies have bumps available since the last release, preview the per-component change set, and compose the Build (pinning selected component versions via `services patch`) before snapping the release in the UI.
- For lightweight inventory work ("what services exist / what changed?"), classify `ctxl services list` output without the full advisor flow.

For raw CLI command shapes, defer to `solai-cli/cli-reference.md` (read it via the `solai-cli` skill rather than from the plugin path). This skill assumes the reference is available.

## Runtime Checks

1. Confirm the environment can run shell commands.
2. Run `command -v ctxl && ctxl --version`. If missing, tell the user the CLI must be installed before this skill can run.
3. Confirm `ctxl services` and `ctxl servicereleases` are available — run `ctxl services --help`. If the topics are not listed, tell the user their CLI build does not expose the services surface and stop.
4. Confirm an active config: `ctxl config current --json`. If none is set or the config is not logged in, follow `solai-cli`'s Automatic Auth Recovery flow first.
5. Read the **entire** `solai-cli/cli-reference.md` file in one pass — do not grep for specific sections like "Services" or "Service Releases", and do not skim. The file is the authoritative command reference for the rest of the session; reading it whole guarantees you see cross-cutting content like Output Formatting, large-payload warnings, write-discipline rules, and the source-tenant routing table that you'll need but might not think to grep for. Do not construct `ctxl` commands from memory.
6. Use Codex's active sandbox and approval policy. Do not modify global or project permissions as part of this skill.

## Permissions

Read-only inventory commands and the bundled summary helper may run under the active Codex sandbox. Request approval only when the runtime requires it. Keep any reusable approval rule narrowly scoped to the exact read-only command family; never propose a rule that also covers `services patch`, record or type writes, or record-version rollback.

## Hard Rules

- This skill **never** runs `services patch` or any other write without explicit user confirmation that follows a diff/preview step.
- This skill **never** claims to install, update, or publish a service. Those actions happen in the workspace UI; the skill produces the patch plan the user takes into that UI.
- Always pass `--config-id <config-id>` on every `ctxl` command — never rely on `ctxl config use` alone.
- Helper script in `scripts/` is the canonical implementation of the Build-composition projection logic. Use it rather than hand-rolling per-command shell loops, especially when a service has many direct deps or any dep has many record versions — the script pre-summarizes output to bound context size.
- **Prefer `jq` over `python3 -c` for inline JSON parsing.** When you need to extract or transform a field from a `ctxl ...` response inline (e.g. `ctxl services list | jq '.items[].id'`), reach for `jq`. Reserve `python3 -c` for transformations that `jq` cannot express because it permits arbitrary code execution and may require additional approval.
- Apply `solai-cli`'s [Disallowed In This Skill](../solai-cli/cli-reference.md#disallowed-in-this-skill) list — this skill inherits those restrictions.

## Workflow

This skill covers the **owned-service** release path. Detect ownership via `sourceTenantId`. Note that `services get` without `--with-data` returns only `id`/`name`/`version`/`_metaData` (no ownership or dependency detail), so pass `--with-data` — or classify from `services list`, which carries `sourceTenantId` per service:

```bash
ctxl services get <service-id> --with-data --config-id <config-id>
```

- `sourceTenantId` **absent** → **owned** → use the [Compose the Build](#compose-the-build-owned-services) advisor below.
- `sourceTenantId` **present** → **installed** (the service was installed from another tenant — operating on it means acting against a *target* tenant, often production). **This skill has no target-tenant workflow, and you must not improvise one.** Do **not** hand-roll update or pruning analysis: no interpreting `servicereleases --updates` / `updatediff`, no `recordversions` version-history checks, and no "what would be pruned" / hotfix-drift assessment. That analysis requires a dedicated installed-service workflow; done ad-hoc here it is unreliable and dangerous — a correct pruning check must compare the incoming pinned version against each record's **actual version history in the target tenant** (not the manifest's pin), and getting it wrong yields a false "nothing will be pruned." The workspace does warn about pruning and dropped-dep removal at apply time, but a wrong pre-assessment still misleads the go/no-go decision before the user ever reaches that prompt. State that target-tenant assessment is out of scope for this skill, that the install/update and its review happen in the workspace UI (least-privilege credentials, per your organization's policy for production or otherwise sensitive tenants), and **stop** — do not offer update inspection as a consolation. (Listing services and owned-service reads remain fine.)

If the user asks for a service-wide inventory across the tenant without specifying an ID, start with `ctxl services list --include-total --config-id <config-id>`, classify each by `sourceTenantId`, and dig into an **owned** service.

## Compose the Build (owned services)

For an owned service, the next release is composed in two steps:

1. **Compose the Build** — pin component versions into the working manifest via `ctxl services patch --set-direct <uri>#N` (or `--add-direct` / `--add-peer` / `--remove-direct`). The CLI is the authoring surface; the core motion is selecting a version (not always the latest) for each component, occasionally adding or dropping a dep.
2. **Snap the release** in the workspace UI to freeze the Build into an immutable release record.

This skill helps with step 1.

### Inspect candidate bumps

```bash
python3 "<skill-dir>/scripts/service_manifest_summarize.py" \
  --service <service-id> \
  --config-id <config-id> \
  --compare-against-release <latest-released-version>
```

`<skill-dir>` is the directory containing this `SKILL.md`; use the path Codex provides when loading the skill.

The script:

1. Fetches the current working manifest (`services get <service-id> --with-data` — required to return the dependency manifest — projecting away inline `.data`).
2. Fetches the last released manifest (`servicereleases get <service-id> -v <latest>`).
3. Diffs the two — surfaces direct deps where the working version differs from the released version, and per-dep, the actual current max version of that record in the tenant.
4. Emits a compact table: `typeId | instanceId | released_version | working_version | tenant_max_version | suggested_action`.

For each row where `working_version != released_version` or `tenant_max > working_version`, decide with the user whether to bump the working manifest's pin (pin that version into the Build) or hold off (defer to a later release).

### Assess what a bump changes (net diff)

Show the **net** pinned→target diff before deciding a bump — not the intermediary churn (versions introduced-then-reverted net out). Drop `_metaData` noise (`hash`, `updatedAt`, `version`, `recordCount` — the last is live row count, not schema) and report whether the change is **behavioral or cosmetic**.

- **Records with an instance id** — flows, agents, connections, typed instances — diff directly: `ctxl recordversions diff native-object:<type-id>/<instance-id> <pinned>..<target> --format jsonpatch`.
- **Type definitions** (`native-object:<type-id>`, no instance id) are a **CLI blind spot**: the CLI exposes no type-def version retrieval (the registry API supports it — and the workspace Build tab diffs type-def versions side-by-side in the browser — but no `ctxl` command routes there). For the pinned→current case, reconstruct the diff from the CLI — the **pinned** content is the dep's hydrated `.data` in the working manifest (`services get <svc> --with-data` hydrates each dep at its pinned version), and the **current** content is `ctxl types get native-object:<type-id>`; diff the two with `solai-cli`'s `scripts/json_diff.py`. **Never** use `types get native-object:<type-id>#<version>` for the pinned side — the `#version` is silently ignored and returns current (a false "no changes"). For any comparison the CLI workaround can't express — arbitrary version-to-version where neither side is current (e.g. two historical releases) — point the user to the **Build tab's side-by-side version diff** in the browser.

### Project the patch

Before invoking `ctxl services patch`, project the patch and surface the resulting manifest. For each `--set-direct` / `--add-direct` flag the user agrees to, compute the resulting `dependencies.direct` list and show the diff against current.

Two ways to project — pick whichever is simpler for the change set:

- **Per-flag preview**: spell out each flag plus the URI it would set, and the version delta vs current.
- **Full projected manifest**: build the projected dependency list as JSON, run it through `scripts/json_diff.py` from the `solai-cli` skill against the current manifest, show the diff.

Show the projection. Ask for explicit confirmation. Only then invoke:

```bash
ctxl services patch <service-id> \
  --set-direct native-object:<type-id>/<instance-id>#<version> \
  --config-id <config-id>
```

Re-read the manifest (`--with-data` — the dependency entries appear only with it):

```bash
ctxl services get <service-id> --with-data --config-id <config-id>
```

Confirm the resulting `version` incremented and the dependency entries match expectations.

**One change per call.** Apply a single `--set-direct` / `--add-direct` / `--add-peer` per `services patch`, and re-verify with `services get` before the next — don't batch multiple add/set flags in one call, since they may not all take effect. When composing a multi-dependency Build, walk the user through the bumps one at a time, patching and confirming each before moving on.

### Snap the release

Tell the user: "The working manifest is updated. Snap the release in the workspace UI at `https://<tenant-id>.my.contextual.io/services/my-services/<service-id>` — pick the appropriate release track (`development`, `release-candidate`, `general-availability`, or `removed-from-distribution`) and add release notes. The CLI does not expose a release-snap command."

Resolve `<tenant-id>` via `ctxl config current --json` — never leave it as a literal placeholder.

## Helper Script

One script lives under `scripts/` and bounds output size + guarantees consistent logic for the workflow above:

- **`service_manifest_summarize.py`** — Compact manifest table for a service (current working manifest or a specific release), optionally diffed against another release. Strips inline `data` to keep output bounded. Used by the Build-composition advisor for the candidate-bumps view and by routine inventory work.

It takes `--config-id` and delegates auth to whatever the active `ctxl` config has set up; it performs no writes.

## Output Expectations

- State the bottom line first — "K direct dep(s) have bumps available since the last release."
- For any `services patch` operation, show the projected manifest diff before asking for confirmation.
- After any confirmed write, re-read with `services get --with-data` and report the resulting `version` and dependency list (`dependencies` appears only with `--with-data`).
- If the user asks for an installed-service / target-tenant operation, surface that this skill covers owned services only (see [Workflow](#workflow)) rather than improvising.
