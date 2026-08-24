# ADR-0008: Portable primary-check declarations

- Status: accepted
- Date: 2026-08-24
- Deciders: human owner (accepted 2026-08-24); independent verifier reviews implementation evidence
- Governing issue: #14

## Context

The first S3NTINEL dogfood audit showed that `testing.primary-check` recognized only the template's
`harness/project.yaml` structure. S3NTINEL documents and runs several checks but has no single
aggregate local/CI command. Inferring authority from README prose or the presence of a workflow
would overstate the evidence, while requiring a template-specific path contradicts the auditor's
general-repository scope.

The human owner approved a config-based declaration with provenance on ADR-0007's closed evidence
object. The auditor remains read-only and must not execute the declared command.

## Decision

Configuration schema 1.2 adds `evidence.primary_check`. It accepts exactly one of:

- `command` plus `source`: a trimmed, bounded, single-line command and a normalized
  repository-relative provenance path; or
- `not_applicable_reason`: a trimmed, bounded, single-line explanation.

The source must be a non-empty, bounded UTF-8 regular file reached without symlink components and
must not traverse `.git`. The source is recorded provenance asserted by configuration; the auditor
does not claim that it semantically defines or contains the exact command. Missing, empty,
non-regular, escaping, `.git`, or symlinked sources make configured input invalid.

Commands are data only and are never executed. Empty, multiline, unbalanced, disposition-shaped,
and obvious successful no-op commands such as `true`, `exit 0`, echo-only, shell-wrapped `true`, and
Python `pass` declarations are invalid. This is bounded structural validation, not proof that an
arbitrary command performs useful verification.

Without configuration, the auditor continues to parse
`engineering.command_contract.primary_check` from `harness/project.yaml`. A valid command passes;
absence, malformed structure, or an obvious no-op warns. README prose, workflow presence, and
unregistered filenames are never inferred as authoritative declarations.

The canonical report schema advances to 1.2. JSON and Markdown record the exact command and source,
the exact disposition reason, or `null` for automatic detection. Configuration schemas 1.0 and 1.1
remain accepted only within their original capabilities.

## Consequences

### Positive

- General repositories can declare an authoritative aggregate command without adopting the harness.
- Evidence reports the exact command and its maintainer-selected provenance source.
- Dispositions remain visible findings rather than hidden suppressions.
- The audit does not expand into shell execution or unreliable prose inference.

### Negative

- Configuration truthfulness and command usefulness remain maintainer assertions.
- A source path does not prove that the source semantically defines the command.
- Obvious no-op rejection cannot decide whether every possible shell command performs meaningful
  verification.
- Report consumers must support schema 1.2.

### Risks and mitigations

- Risk: a source path escapes the audited worktree. Mitigation: normalized relative paths, `.git`
  exclusion, component-wise `lstat`, and non-symlink regular-file enforcement.
- Risk: the auditor executes repository commands. Mitigation: store and render command text only;
  tests use sentinels and complete target snapshots.
- Risk: a declared command is cosmetic. Mitigation: reject common successful no-ops and report exact
  evidence; execution quality remains a separate application or CI assessment.
- Risk: schema generations blur capabilities. Mitigation: primary-check declarations require config
  1.2, and generated reports identify schema 1.2.

## Alternatives considered

| Alternative | Evidence | Reason not selected |
|---|---|---|
| Infer a command from README prose | S3NTINEL documents several distinct commands | Authority and aggregation cannot be determined reliably |
| Infer success from CI workflow presence | Workflows may run only a subset or differ from local checks | Presence does not establish one portable command |
| Recognize Makefile, package scripts, and language-specific filenames automatically | Common but ecosystem-specific conventions exist | An expanding heuristic set would produce false authority claims |
| Keep only the harness path | Existing behavior is deterministic | General repositories remain unable to provide portable evidence |
| Execute the declared command | Would demonstrate actual exit behavior | Violates the accepted read-only audit boundary and executes repository code |

## Verification and revisit trigger

Verify configured general-repository, automatic harness, explicit-disposition, absent, malformed,
empty/no-op/multiline/unbalanced command, missing/empty/directory/symlink/ancestor-symlink/escaping
source, `.git`, schema-generation, deterministic rendering, and complete before/after target snapshot
fixtures. Verify installed-package behavior independently.

Revisit if a portable primary-check standard gains broad adoption, consumers need signed provenance,
or a separately authorized execution product is created.
