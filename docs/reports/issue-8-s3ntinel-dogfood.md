# Issue 8 S3NTINEL dogfood report

## Outcome

`VERIFIED`: Agentic Repo Auditor `0.1.0` completed its first audit of an existing public repository against clean, detached S3NTINEL commit `14ba0416e06f6a9b57a8f7b02fdef1bb09a2f1cc`. The installed wheel produced deterministic JSON and Markdown, returned the documented default failure status, and made no observable target-repository change.

The canonical output is available as [JSON](s3ntinel-14ba0416.audit.json) and [Markdown](s3ntinel-14ba0416.audit.md). The report assesses repository engineering and agent-readiness evidence only. It does not assess S3NTINEL's application architecture, telemetry semantics, Spark runtime, generated artifacts, or production readiness; that remains the separate companion boundary in [Issue 11](https://github.com/stauntonjr/agentic-repo-auditor/issues/11).

## Reproduction boundary

- Public target: `stauntonjr/S3NTINEL`.
- Revision: `14ba0416e06f6a9b57a8f7b02fdef1bb09a2f1cc`.
- Git tree: `69ca0eebe6459c6089dc63805c77a8e0bb97a3ef`.
- Target checkout: fresh public clone, detached at the exact revision, clean before execution.
- Auditor source: Agentic Repo Auditor commit `9e0f93298b55be5ffe2925c4a0922ff7de8a6d61`.
- Installed artifact: locally built `agentic_repo_auditor-0.1.0-py3-none-any.whl` in a fresh virtual environment.
- Installed runtime: `agentic-repo-auditor==0.1.0`, `PyYAML==6.0.2`.
- Configuration: default checks, with `--fail-on none` only for artifact capture; the default threshold was exercised separately.

The packaged command was run in both formats:

```text
agentic-repo-auditor audit TARGET --format json --fail-on none
agentic-repo-auditor audit TARGET --format markdown --fail-on none
```

## Determinism and read-only evidence

`VERIFIED`:

- JSON run 1 and run 2 were byte-identical: `sha256:6c500685ac9f866cd4c3ba2bdd8f62bc8eb7e811842c0ec5f5f76c14c89555d8`.
- Markdown run 1 and run 2 were byte-identical: `sha256:90d76a09bc645a3cebafdba4e45975b1d7f2ed2a508e42c39b418612ba9e0e9a`.
- The default `--fail-on fail` execution returned status `1`, matching the single `fail` finding.
- Target `HEAD`, tree, and porcelain-v2 status were unchanged.
- A recursive content fingerprint covering every regular file, including Git metadata, was unchanged before and after both formats: `sha256:aaf09b9b2d7c0b87d2528efce333bf7fb4a0c88fc3cc843915fb3589547177ce`.
- The target contained no symlinks; the empty symlink-set fingerprint remained `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The Auditor's full local gate also passed 95 tests with one intentional template-only skip, Ruff formatting and lint, Pyright, 20 product tests with 82% branch-aware coverage, the deterministic/read-only integration test, and clean-install package smoke.

## Result

The report emitted 13 fixed-order findings: 4 `pass`, 8 `warn`, and 1 `fail`. The one high-severity failure is real and actionable: S3NTINEL's workflow uses mutable `actions/checkout@v4` and `actions/setup-python@v5` references rather than full commit SHAs.

## Non-pass triage

| Finding | Disposition | Owner | Triage |
|---|---|---|---|
| `agent-readiness.instructions` | Auditor false warning | Auditor, [Issue 13](https://github.com/stauntonjr/agentic-repo-auditor/issues/13) | S3NTINEL's `AGENTS.md` defines authoritative and non-authoritative evidence, tests, verification, and safety. The check misses that source-precedence meaning because it requires the literal substring `source`. |
| `agent-readiness.skills` | Confirmed repository-visible advisory gap | S3NTINEL maintainer | No portable `.agents/skills/*/SKILL.md` files exist at the pinned revision. Whether S3NTINEL needs them is a product-governance decision, so the low-severity warning is retained. |
| `ci.immutable-actions` | Confirmed repository defect | S3NTINEL maintainer | Both external Actions in `.github/workflows/ci.yml` use mutable major-version tags. This is the only failing finding. |
| `governance.community-files` | Confirmed repository-visible gap | S3NTINEL maintainer | `README.md` exists; `CONTRIBUTING.md` and `LICENSE` do not. In particular, the public repository contains no checked-in license grant at this revision. |
| `governance.project-contract` | Mixed target gap and Auditor contract defect | S3NTINEL maintainer; Auditor, [Issue 12](https://github.com/stauntonjr/agentic-repo-auditor/issues/12) | No machine-readable project/authority contract exists. Separately, the remediation says a documented exception can satisfy the finding, while the implementation recognizes only `harness/project.yaml`; that alternative is currently impossible. |
| `security.code-scanning` | Confirmed repository-visible gap | S3NTINEL maintainer | No checked-in workflow references CodeQL. The offline auditor does not claim to inspect GitHub-side code-scanning settings. |
| `security.dependency-updates` | Confirmed repository-visible gap | S3NTINEL maintainer | No checked-in Dependabot or Renovate configuration exists. GitHub-side settings were not authenticated or inspected. |
| `security.policy` | Confirmed repository-visible gap | S3NTINEL maintainer | Neither `SECURITY.md` nor `.github/SECURITY.md` exists. |
| `testing.primary-check` | Confirmed target gap plus Auditor portability limitation | S3NTINEL maintainer; Auditor, [Issue 14](https://github.com/stauntonjr/agentic-repo-auditor/issues/14) | S3NTINEL documents Markdown, pytest, Ruff, and a structural smoke command, but no single machine-readable aggregate command used unchanged locally and in CI. The warning is reasonable; the detector's exclusive reliance on template-specific `harness/project.yaml` is not portable. |

The four passing findings are supported at the pinned revision: a root `AGENTS.md`, one CI workflow, a clean worktree, and 79 conventional test files.

## Product feedback

`VERIFIED`: The run created three bounded Auditor follow-ups and added them to the shared Project:

- [Issue 13](https://github.com/stauntonjr/agentic-repo-auditor/issues/13) is ready for implementation and addresses the demonstrated false warning.
- [Issue 12](https://github.com/stauntonjr/agentic-repo-auditor/issues/12) needs a human choice about satisfiable project-contract evidence.
- [Issue 14](https://github.com/stauntonjr/agentic-repo-auditor/issues/14) needs a human choice about portable primary-check declarations.

No S3NTINEL file, Issue, Project item, or setting was changed. Target remediation remains separate work requiring explicit authorization in that repository.

## Residual limits

- The audit was deliberately offline and repository-local; branch protection, private vulnerability reporting, Dependabot repository settings, and code-scanning configuration outside tracked files were not verified.
- A clean source audit does not prove the S3NTINEL test suite, Spark pipelines, replay bundles, application behavior, deployment, or production readiness.
- The recursive read-only fingerprint proves no regular-file or symlink-content change across these executions; it does not claim filesystem metadata such as access times was unchanged.
- No Auditor release, tag, registry publication, or S3NTINEL remediation was authorized or performed.
