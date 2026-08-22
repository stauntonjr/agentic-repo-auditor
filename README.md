# Agentic Project Template

A provider-neutral engineering harness for projects developed substantially or entirely by coding agents. It turns project intent, authority, engineering loops, GitHub planning, verification, and reporting into durable repository artifacts.

This is a working v0.4, not a claim of autonomous software delivery. Humans still own product intent, risk acceptance, external side effects, and release authorization.

## Start a project

From GitHub after this repository is published as a template:

```bash
gh repo create OWNER/NEW-REPOSITORY \
  --template stauntonjr/agentic-project-template \
  --private \
  --clone
cd NEW-REPOSITORY
python3 tools/project_intake.py --interactive --mode new --apply
make check
```

For a local trial:

```bash
python3 tools/project_intake.py \
  --answers harness/fixtures/intake.answers.json \
  --target /tmp/example-agent-project \
  --apply
python3 /tmp/example-agent-project/tools/harness_check.py
```

The initializer is idempotent: it inspects existing state, preserves confirmed answers, and only replaces generated project documents when `--apply` is used. Use `--mode adopt` for an existing repository; it copies only missing harness files, preserves collisions, and writes `docs/project/adoption-gaps.md` for deliberate reconciliation. Use `--mode gap-only` to ask only unresolved questions.

## What is included

| Surface | Purpose |
|---|---|
| `AGENTS.md` | Short instruction map, authority rules, source precedence, and skill routing |
| `harness/project.yaml` | Machine-readable project intent, autonomy, product version, quality, security, evidence, and lifecycle contract |
| `harness/roles/` | Provider-neutral role contracts with distinct authority and handoffs |
| `harness/loops/` | State machines with inputs, outputs, gates, retries, and stop conditions |
| `.agents/skills/` | Intake, research, execution, reporting, planning, ADR, and release workflows |
| `.codex/agents/` | Thin Codex adapters for the canonical role contracts |
| `.pi/` | Experimental Pi settings, workflow prompts, and structured context-readiness questions |
| `harness/adapters/` | Machine-readable provider capabilities, mappings, limitations, and security boundaries |
| `tools/` | Dependency-free intake, validation, loop evidence, report, and GitHub audit tools |
| `.github/planning.json` | Expected GitHub labels, milestones, Project fields, and views |
| `harness/challenges/` | Executable historical failure-case contract |
| `harness/version.json` | Version and dry-run migration boundary for derived repositories |
| `harness.lock` | Pinned upstream release, commit, per-file checksums, and ownership classes |
| `harness/ownership.json` | Upgrade policy separating upstream-owned, project-owned, and merge-required paths |
| `harness/evals/` | Forward-test scenarios for skill routing and safety behavior |
| `docs/project/handoff.md` | Concise orientation index for fresh humans and agents |
| `docs/project/engineering-baseline.md` | Portable capability contract and profile-selected tooling boundary |

## Default engineering loop

```text
Intake -> Understand -> Plan -> Authorize -> Implement
       -> Verify -> Adversarial review -> Integrate -> Report -> Learn
```

The loop is evidence-producing and revision-aware. Parallel work is reserved for independent, bounded lanes. Shared Git operations, planning state, and integration remain serialized through the orchestrator.

Before each loop, the main agent performs a context-readiness gate: inspect discoverable facts, identify gaps in intent/evidence/authority/acceptance, ask focused questions only when needed, and record any low-risk assumptions. The separate `research-existing-solutions` skill handles prior art, standards, licensing, and buy-versus-build research.

Start and close a loop with:

```bash
python3 tools/loop.py start --issue 123 \
  --objective "Deliver the smallest accepted slice" \
  --criterion "AC1=The accepted behavior is demonstrated" \
  --write-path src/example.py --write-path tests/test_example.py \
  --implementer codex/implementer-session
python3 tools/loop.py record-check --run RUN_ID --name unit \
  --command "python3 -m unittest discover -s tests -v" --status passed \
  --evidence "All targeted tests passed" --criterion AC1
python3 tools/loop.py record-release-impact --run RUN_ID \
  --level patch --reason "Backward-compatible correction to documented behavior"
python3 tools/loop.py record-verdict --run RUN_ID \
  --reviewer codex/separate-verifier-session --verdict approve \
  --criterion AC1 --evidence "Diff and raw test output independently reviewed"
python3 tools/loop.py finish --run RUN_ID
```

`start` fingerprints pre-existing dirty and untracked paths; staged index blobs and modes; `assume-unchanged` and `skip-worktree` paths; and recursively inspected submodules or embedded Git repositories. Submodule visibility is forced even when `.gitmodules` requests `ignore = all`; unsafe directory entries fail closed. Completion compares the current tree, index, nested repositories, and committed paths with that baseline; rejects undeclared writes; requires passed evidence for every unwaived criterion; requires a current product release-impact assessment; and rejects approvals made against an older requirement revision, attempt, commit, or candidate digest. Contract revisions invalidate prior waivers. A new waiver requires recorded `human:IDENTITY` provenance and a reason. The generated executive report distinguishes verified repository evidence, reported facts, and inference.

## Product versioning and engineering baseline

`harness_version` tracks the reusable control plane. `engineering.versioning.current` tracks the derived product. An upgrade of the harness never implies an application release.

Intake identifies the product's public compatibility contract and selects SemVer, CalVer, independently versioned components, or no formal product version. SemVer is not selected until an API, CLI, configuration, schema, artifact, or user-visible behavior contract is declared. Agents record a `none`, `patch`, `minor`, or `major` recommendation for each completed loop; humans retain version and release authority.

Profiles select concrete tools behind a portable capability contract: one authoritative local/CI command, runtime and dependency reproducibility, formatting, linting, type checking, tests, coverage policy, and clean package or build smoke. The Python data profile uses pinned `uv` commands with Ruff, Pyright, pytest, pytest-cov, and Hypothesis. It requires a branch-coverage baseline before release; projects ratchet that measured baseline rather than inheriting an unearned threshold. See `docs/project/engineering-baseline.md` and [ADR-0005](docs/adr/0005-product-version-and-engineering-baseline.md).

## Core commands

```bash
make check                 # Harness structure and contract validation
make test                  # Deterministic unit tests
make actions-supply-chain  # Immutable Actions and least-privilege workflow check
make smoke                 # Contracts, Actions, compilation, tests, and selected-profile checks
python3 tools/github_planning.py audit --offline
python3 tools/github_planning.py bootstrap-project       # Dry run
python3 tools/github_planning.py bootstrap-project --yes # Explicit create/copy
python3 tools/github_planning.py audit
python3 tools/github_planning.py apply       # Dry run
python3 tools/github_planning.py apply --yes # Explicit live mutation
python3 tools/harness_upgrade.py status
python3 tools/product_version.py           # Product source/contract drift
python3 tools/product_version.py --tag v1.2.3
python3 tools/evaluate_harness.py
make pi-runtime-check       # Optional: offline Pi resource-load test, no model call
```

No GitHub mutation occurs without both the mutating subcommand and `--yes`. Project bootstrap can create or copy a Project, link it to the repository, and create missing fields. Saved views remain a reported manual step. Destructive cleanup is deliberately out of scope.

## Pi adapter

Pi 0.84.1 is the exercised reference runtime for the experimental adapter. From the repository root, review the project-local resources and then start Pi:

```bash
pi --offline --approve
```

Pi discovers `AGENTS.md` and `.agents/skills/` natively. The adapter adds these prompt templates:

- `/harness-intake [new|adopt|refresh|gap-only]`
- `/harness-research <decision or problem>`
- `/harness-loop <accepted objective>`
- `/harness-report [run-id]`

Run `/harness-adapter` to confirm that the repository-local extension loaded.

`make pi-runtime-check` starts an isolated, offline, sessionless Pi RPC process and verifies project prompts, skills, and the extension command without invoking a model or installing packages.

The `harness_questionnaire` tool collects one to three material follow-up answers after repository inspection. It does not replace the canonical `project-intake` skill or write project state by itself.

`.pi/settings.json` deliberately does not select a model, provider, or thinking level and installs no packages. Project-local Pi extensions execute with the launching user's permissions, so trust the repository only after review and use an external sandbox for untrusted code. The adapter also does not claim Pi core supplies subagents: an authoring session cannot independently verify its own work. See `harness/adapters/pi.json` and [ADR-0003](docs/adr/0003-pi-reference-adapter.md).

## One-repository lifecycle and upgrades

The generated application repository is the operating root. The template is an upstream factory, not a submodule. Application code, `AGENTS.md`, repository-local skills, GitHub configuration, evidence, and project policy evolve together through normal pull requests. [ADR-0002](docs/adr/0002-one-repository-harness-lifecycle.md) records this boundary.

`harness.lock` provides the common base for a three-way comparison:

```text
locked upstream release + current project + newer upstream release
                         -> ownership-aware upgrade plan
```

The ownership classes are:

- `upstream-owned`: replace automatically only when the local file still matches the locked base;
- `project-owned`: never replace silently;
- `merge-required`: require an explicit reviewed resolution even when locally unchanged.

Prepare an upgrade from a local release checkout:

```bash
python3 tools/harness_upgrade.py status
python3 tools/harness_upgrade.py plan \
  --source-root /path/to/agentic-project-template-release \
  --output /tmp/harness-upgrade-plan.json
python3 tools/harness_upgrade.py apply \
  --plan /tmp/harness-upgrade-plan.json \
  --source-root /path/to/agentic-project-template-release \
  --resolve 'AGENTS.md=merged' \
  --yes
```

Every manual operation requires `PATH=keep-local`, `PATH=use-upstream`, or `PATH=merged`. Apply rechecks local and upstream hashes, updates the project version and lock, and writes a backup receipt under `.harness/upgrades/`. Rollback refuses to overwrite files changed after the upgrade:

```bash
python3 tools/harness_upgrade.py rollback \
  --receipt .harness/upgrades/VERSION/TIMESTAMP/receipt.json \
  --yes
```

For an explicitly authorized network path, `latest` reads the newest GitHub release and `fetch --ref TAG --yes` creates an isolated checkout under `.harness/upgrades/sources/`. Fetch also requires the release's `harness.release.lock` asset, verifies its repository and tag, and uses its post-commit provenance instead of trusting an embedded mutable-branch lock. The manually dispatched `Prepare harness upgrade` workflow can produce an upgrade pull request after all required resolutions are supplied. It is intentionally not scheduled.

The manually dispatched `Publish harness release` workflow is the release boundary. It requires a typed confirmation, requires the tag to match `harness/version.json`, runs the full smoke suite, generates `harness.release.lock` against the already-known source commit, and then creates the GitHub Release. No release is published merely by merging template changes.

## v0.4 boundaries

Implemented now:

- Idempotent, status-aware intake rendering.
- Context-readiness and prior-art research gates.
- Provider-neutral roles, one executable engineering loop, thin Codex adapters, and an experimental Pi adapter.
- Machine-readable provider mappings that expose native capabilities and unsupported boundaries.
- Pi-native workflow prompts and a dependency-free structured-question extension.
- Git-boundary collection and evidence-labeled executive reports.
- Local and live GitHub drift audit, Project create/copy, repository linking, missing-field creation, and non-destructive label/milestone reconciliation.
- Historical defect challenge manifests and harness validation scenarios.
- Provenance locks, ownership-aware three-way upgrade plans, explicit apply, receipts, rollback, and an optional manually dispatched upgrade-PR workflow.
- Independent product-version contracts and current-revision release-impact evidence.
- Profile-driven engineering capability contracts with concrete Python defaults.
- Dependabot, dependency review, CodeQL, secret-control expectations, least-privilege permissions, and immutable Action enforcement.

Deliberately deferred:

- Automatic saved Project-view mutation.
- Repository rulesets, environments, secrets, permissions, and branch-protection reconciliation.
- Additional provider adapters beyond Codex and Pi.
- Automated Pi subagent/worktree orchestration; independent verification still requires a separate trusted session or reviewed extension.
- Live model scoring of the harness scenarios.
- Automatic token/cost ingestion and organization-wide analytics.
- Packaging the skill bundle as an installable plugin.
- Automatic semantic merging of project-owned or merge-required files.

These are explicit next-version candidates, not implied capabilities.

## Durable state and preferences

Repository policy belongs in `AGENTS.md`, `harness/project.yaml`, ADRs, code, tests, Issues, and pull requests. Conversation history is exploratory and non-authoritative.

Project-wide working agreements may be committed in `docs/project/working-agreements.md`. Personal preferences belong in `.harness/preferences.local.json`, which is ignored by Git, unless the user deliberately promotes one into public project policy.

## Profiles and adoption

The template ships with `generic`, `python-data`, `web-service`, and `agent-system` profiles. Profiles supply capability and tool defaults; the intake record captures every override and its status as `confirmed`, `provisional`, `assumed`, `TBD`, or `not-applicable`. A successful no-op is not a valid substitute for an unresolved check.

Dogfood a new profile on one repository before making it a template default. A useful progression is:

1. Start a greenfield project with `new` mode.
2. Adopt a mature repository with `adopt` mode.
3. Convert escaped defects into challenge manifests.
4. Measure human corrections, retries, escaped defects, cycle time, and accepted-change cost.

## Design influences

The research snapshot in `docs/research/landscape.md` records the current ecosystem, sources, licenses, and what this template borrows conceptually. It intentionally reimplements a small coherent control plane rather than copying another framework.

## License

MIT. See `LICENSE`.
