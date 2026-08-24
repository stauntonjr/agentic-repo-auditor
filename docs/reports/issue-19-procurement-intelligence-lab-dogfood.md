# Issue 19 Procurement Intelligence Lab dogfood report

## 1. Outcome and why it matters

`VERIFIED`: Agentic Repo Auditor `0.1.0` completed the second existing-repository audit against clean, detached Procurement Intelligence Lab commit `0f9d1a45af078ebf969f9ced11fc2e93adb542d0`. A fresh installation of the exact Auditor source candidate accepted configuration schema 1.2, recorded `make check` from `Makefile` without executing target code, produced deterministic JSON and Markdown, and made no observable target change.

This matters because the first S3NTINEL dogfood exposed template-coupled evidence rules. This run proves that the resulting portable primary-check contract works on a different, mature repository without requiring template adoption. The canonical output is available as [JSON](procurement-intelligence-lab-0f9d1a45.audit.json) and [Markdown](procurement-intelligence-lab-0f9d1a45.audit.md).

## 2. Planned versus completed

`VERIFIED`: The accepted Issue #19 slice is complete at the repository-audit boundary:

- audited the exact public target revision from a disposable clone;
- built and installed the Auditor wheel in a fresh virtual environment;
- used schema-1.2 configured evidence for `make check` from `Makefile`;
- repeated both output formats and exercised the default failure threshold;
- compared complete target snapshots before and after execution;
- classified every non-pass finding; and
- created only one bounded product follow-up, [Issue #20](https://github.com/stauntonjr/agentic-repo-auditor/issues/20), for a reproduced false warning.

`VERIFIED`: No Procurement file, wiki file, Issue, Project item, setting, test, or primary command was changed or executed.

## 3. User-visible and business-semantic changes

`VERIFIED`: This loop adds a public, reproducible evidence set for Procurement Intelligence Lab. The report contains 13 fixed-order findings: 9 `pass`, 4 `warn`, and no `fail`, `unknown`, or `not-applicable` findings. Because the default threshold is `fail`, the default execution correctly returned status `0`.

`INFERRED`: The result shows a comparatively strong repository engineering harness at the pinned revision: portable skills, fully immutable workflow dependencies, CI, CodeQL, Dependabot, an authoritative aggregate check, and a conventional test suite are all visible. This is not an assessment of procurement semantics or application quality.

## 4. Architecture, schema, dependency, data, and interface changes

`VERIFIED`: No product code, schema, dependency, runtime, or CLI interface changed. The audit consumed the existing public configuration/report schema `1.2`:

```json
{
  "schema_version": "1.2",
  "evidence": {
    "primary_check": {
      "command": "make check",
      "source": "Makefile"
    }
  }
}
```

The declaration is provenance data. Per ADR-0008, the Auditor did not execute or semantically interpret `make check`.

## 5. Verification evidence and boundary proven

`VERIFIED`:

- Public target: `stauntonjr/procurement-intelligence-lab`.
- Target commit: `0f9d1a45af078ebf969f9ced11fc2e93adb542d0`.
- Target tree: `1ee10ecb5cc2a37e0545c95c4ce1b5d7fa15f1c3`.
- Auditor source: `09e02e9de498d5d0578b35865e929a67d64bb4c6` (tree `8605024b53ce9198b1963b3ecddbdffae14ecfb8`).
- Installed artifacts: `agentic-repo-auditor==0.1.0` and `PyYAML==6.0.2` in a fresh virtual environment.
- Report state identity: `sha256:0943870d181b201f67b3d4c1c136ba2781aae202ea56446cfc91ec96dc82870a`.
- JSON runs were byte-identical: `sha256:2d0de2cc679fef04e5ed1a49237c3e642aaff3f7a345b1624ed40c3891deefb1`.
- Markdown runs were byte-identical: `sha256:f9cc74dc4db863773a32b34ca998c513adad0a8a2aacf896e2b33b4057542e9c`.
- Advisory executions returned `0`; the separate default-threshold execution returned `0` with the same JSON hash because there were no `fail` findings.
- Complete structured target snapshots before and after all probe executions were byte-identical: `sha256:498c339117ba7fe7caa724d3c1234cdec00e94ef22b7956d58aa09df1b5c9e9e`.
- Recursive path/type/mode/content fingerprint across 384 entries and 291 regular files, including Git metadata, remained `sha256:c1efef07300fc56bb501b18d4e8b18229d6cd73208d2f18faa49691026732c4a`.
- `HEAD`, tree, full staged index entries, index flags, and forced porcelain-v2 status were unchanged and clean.
- The target contained no symlinks or gitlinks; both exact sets remained empty.

The packaged commands were:

```text
agentic-repo-auditor audit TARGET --config CONFIG --format json --fail-on none
agentic-repo-auditor audit TARGET --config CONFIG --format markdown --fail-on none
agentic-repo-auditor audit TARGET --config CONFIG --format json
```

## 6. Acceptance-criterion coverage, waivers, and verifier verdict

`VERIFIED`: AC1-AC4 have direct evidence above. AC5's canonical artifacts are present; the complete Auditor gate and independent exact-candidate verdict are recorded in the engineering-loop run before integration. AC6 is completed only after the PR and shared Project are reconciled.

No criterion waiver is requested or recorded. Independent review must bind to the exact candidate rather than this narrative alone.

## 7. Baseline-relative write scope and violations

`VERIFIED`: The intended durable write scope is limited to the two canonical audit artifacts, this report, and the Auditor handoff. `harness.lock` was declared defensively but remains unchanged because the handoff is project-owned. The authoritative Procurement checkout at `/home/jrs/procurement-intelligence-lab` and its separate wiki checkout at `/home/jrs/procurement-intelligence-lab.wiki` were not used as audit targets and were not changed.

The loop completion gate records baseline-relative changed paths and any scope violations. No scope widening is authorized.

## 8. GitHub Issue, Project, PR, and release state

`VERIFIED`: [Issue #19](https://github.com/stauntonjr/agentic-repo-auditor/issues/19) is the canonical work item and is `In Progress` in the shared Agentic Engineering Harness Roadmap during implementation. [Issue #20](https://github.com/stauntonjr/agentic-repo-auditor/issues/20) is a bounded `Todo` product defect discovered by this run.

`VERIFIED`: No Procurement GitHub object was mutated. No Auditor tag, GitHub Release, package-registry publication, or version change is authorized or performed. Product release impact is `none` because this loop publishes dogfood evidence without changing the public CLI, configuration, or report contract.

## 9. Risks, limitations, failures, and unverified claims

The four warnings are triaged as follows:

| Finding | Disposition | Evidence and next boundary |
|---|---|---|
| `agent-readiness.instructions` | Auditor false warning | The pinned root `AGENTS.md` contains concrete confidentiality, authority-separation, authorization, token, and non-deletion guardrails but not the literal `safe`, `safely`, or `safety` tokens. Issue #20 captures the bounded counterexample with negative-test requirements. |
| `governance.community-files` | Confirmed repository-visible gap | `README.md` and MIT `LICENSE` are present; `CONTRIBUTING.md` is absent. Whether to add one is a Procurement maintainer decision. |
| `governance.project-contract` | Confirmed evidence gap or disposition decision | The repository has extensive ADR, handoff, planning, and instruction artifacts, but no configured single machine-readable project intent/authority object. `.github/planning.json` was not misrepresented as that broader contract. |
| `security.policy` | Confirmed repository-visible gap | `docs/security.md` defines threats and controls but does not provide a discoverable vulnerability-reporting policy with supported versions and a private reporting channel. |

`VERIFIED`: An initial packaging command was accidentally invoked from the disposable target directory. It failed during isolated build-requirement resolution before producing a wheel or audit output. The command was corrected to the Auditor worktree, and subsequent complete target snapshots prove no content, index, status, symlink, gitlink, or Git metadata change.

`UNVERIFIED`: This offline audit does not verify GitHub rulesets, branch protection, repository-side security settings, private vulnerability reporting, workflow runs, or live Project state in Procurement. It does not run `make check`, inspect application behavior, validate procurement semantics, assess data/model quality, or establish deployment/production readiness. The empty symlink and gitlink sets prove absence in this target, not general behavioral coverage of those cases.

## 10. Decisions or authorization needed

No decision is needed to integrate this evidence-only loop after exact-candidate approval. Separate human decisions remain for:

- whether Procurement should add `CONTRIBUTING.md`;
- whether it should adopt or explicitly disposition a machine-readable project authority contract;
- whether it should add a public vulnerability-reporting policy; and
- which Auditor roadmap capability follows the two existing-repository audits.

None of those decisions is implied or authorized by this report.

## 11. Recommended next loop

First repair the demonstrated instruction false warning in Issue #20. Then use the two dogfood datasets to make the already-scheduled human choice among authenticated GitHub evidence (#10), SARIF (#5), baselining (#7), and the separate full-application assessment companion (#11). The companion remains the right boundary for the comprehensive application report; it should not expand this offline repository auditor.

## 12. Exact revision and change scope

The audited product source is Auditor commit `09e02e9de498d5d0578b35865e929a67d64bb4c6`. The target is Procurement commit `0f9d1a45af078ebf969f9ced11fc2e93adb542d0`. This branch adds evidence and handoff state only; it does not change Auditor behavior or Procurement state.
