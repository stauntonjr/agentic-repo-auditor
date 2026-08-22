"""Read-only repository evidence collection and checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import __version__
from .model import Evidence, Finding, Report, TargetState


class AuditError(RuntimeError):
    """Raised when the target or configuration cannot be audited safely."""


@dataclass(frozen=True)
class AuditConfig:
    """Validated v0.1 configuration."""

    disabled_checks: frozenset[str] = frozenset()


ACTION_USE = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*[\"']?([^\"'#\s]+)", re.MULTILINE)
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _finding(
    finding_id: str,
    category: str,
    status: str,
    severity: str,
    title: str,
    description: str,
    evidence: list[Evidence],
    remediation: str,
) -> Finding:
    return Finding(
        finding_id,
        category,
        status,
        severity,
        title,
        description,
        tuple(evidence),
        remediation,
    )


def _git(root: Path, *args: str, check: bool = True) -> str:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
        timeout=15,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise AuditError(detail)
    return result.stdout.strip()


def _target_state(root: Path) -> tuple[TargetState, str]:
    top = _git(root, "rev-parse", "--show-toplevel")
    resolved_top = Path(top).resolve()
    if resolved_top != root:
        raise AuditError(f"target must be a repository root: {resolved_top}")
    revision = _git(root, "rev-parse", "HEAD", check=False) or "UNBORN"
    branch = _git(root, "branch", "--show-current", check=False) or "DETACHED"
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
        "--ignore-submodules=none",
    )
    identity = hashlib.sha256(
        f"{root.name}\n{revision}\n{branch}\n{status}\n".encode("utf-8")
    ).hexdigest()
    return TargetState(root.name, revision, branch, bool(status), f"sha256:{identity}"), status


def _presence_check(
    root: Path,
    finding_id: str,
    category: str,
    title: str,
    paths: tuple[str, ...],
    description: str,
    remediation: str,
) -> Finding:
    present = tuple(path for path in paths if (root / path).exists())
    status = "pass" if present else "warn"
    severity = "info" if present else "medium"
    value = ", ".join(present) if present else "none found"
    return _finding(
        finding_id,
        category,
        status,
        severity,
        title,
        description,
        [Evidence("path-presence", ".", value)],
        remediation,
    )


def _governance_instructions(root: Path, _: str) -> Finding:
    return _presence_check(
        root,
        "governance.instructions",
        "governance",
        "Repository instructions",
        ("AGENTS.md",),
        "Repository-level agent and contributor instructions are discoverable.",
        "Add a root AGENTS.md with commands, boundaries, sources of truth, and safety rules.",
    )


def _governance_contract(root: Path, _: str) -> Finding:
    return _presence_check(
        root,
        "governance.project-contract",
        "governance",
        "Machine-readable project contract",
        ("harness/project.yaml",),
        "A durable project intent and authority contract is present.",
        "Add a machine-readable project contract or document why one is not used.",
    )


def _governance_community_files(root: Path, _: str) -> Finding:
    expected = ("README.md", "CONTRIBUTING.md", "LICENSE")
    present = tuple(path for path in expected if (root / path).is_file())
    missing = tuple(path for path in expected if path not in present)
    return _finding(
        "governance.community-files",
        "governance",
        "pass" if not missing else "warn",
        "info" if not missing else "low",
        "Community health files",
        "Basic purpose, contribution, and licensing files are present.",
        [Evidence("path-set", ".", f"present={list(present)}; missing={list(missing)}")],
        "Add the missing community health files and keep them aligned with actual behavior.",
    )


def _git_clean(root: Path, status_text: str) -> Finding:
    entries = tuple(line for line in status_text.splitlines() if line)
    return _finding(
        "git.clean-worktree",
        "git",
        "pass" if not entries else "warn",
        "info" if not entries else "low",
        "Worktree state",
        "The audit records whether the target has uncommitted or untracked state.",
        [Evidence("git-status", ".", f"changed_entries={len(entries)}")],
        "Review and intentionally preserve, commit, or ignore outstanding worktree entries.",
    )


def _workflow_paths(root: Path) -> tuple[Path, ...]:
    workflow_root = root / ".github/workflows"
    if not workflow_root.is_dir():
        return ()
    return tuple(sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml"))))


def _ci_workflows(root: Path, _: str) -> Finding:
    paths = _workflow_paths(root)
    return _finding(
        "ci.workflows",
        "ci",
        "pass" if paths else "warn",
        "info" if paths else "medium",
        "Continuous integration workflows",
        "At least one repository CI workflow is present.",
        [Evidence("path-count", ".github/workflows", str(len(paths)))],
        "Add CI that runs the same authoritative check used locally.",
    )


def _ci_immutable_actions(root: Path, _: str) -> Finding:
    paths = _workflow_paths(root)
    references: list[tuple[str, str]] = []
    mutable: list[tuple[str, str]] = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for reference in ACTION_USE.findall(content):
            relative = path.relative_to(root).as_posix()
            references.append((relative, reference))
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if "@sha256:" not in reference:
                    mutable.append((relative, reference))
                continue
            _, separator, revision = reference.rpartition("@")
            if not separator or re.fullmatch(r"[0-9a-fA-F]{40}", revision) is None:
                mutable.append((relative, reference))
    if not paths:
        status, severity = "not-applicable", "info"
    elif mutable:
        status, severity = "fail", "high"
    else:
        status, severity = "pass", "info"
    evidence = [Evidence("action-summary", ".github/workflows", f"references={len(references)}")]
    evidence.extend(Evidence("mutable-action", path, reference) for path, reference in mutable)
    return _finding(
        "ci.immutable-actions",
        "ci",
        status,
        severity,
        "Immutable workflow dependencies",
        "External Actions and container actions use immutable references.",
        evidence,
        "Pin third-party Actions to full commit SHAs and containers to image digests.",
    )


def _security_policy(root: Path, _: str) -> Finding:
    return _presence_check(
        root,
        "security.policy",
        "security",
        "Security policy",
        ("SECURITY.md", ".github/SECURITY.md"),
        "A vulnerability-reporting policy is discoverable.",
        "Add SECURITY.md with supported versions and a private reporting channel.",
    )


def _security_updates(root: Path, _: str) -> Finding:
    return _presence_check(
        root,
        "security.dependency-updates",
        "security",
        "Automated dependency updates",
        (".github/dependabot.yml", ".github/renovate.json", "renovate.json"),
        "A recognized dependency-update configuration is present.",
        "Configure a reviewed dependency-update tool for every supported ecosystem.",
    )


def _security_code_scanning(root: Path, _: str) -> Finding:
    paths = _workflow_paths(root)
    matched = tuple(
        path.relative_to(root).as_posix()
        for path in paths
        if "github/codeql-action" in path.read_text(encoding="utf-8")
    )
    return _finding(
        "security.code-scanning",
        "security",
        "pass" if matched else "warn",
        "info" if matched else "medium",
        "Code scanning",
        "The repository declares a CodeQL workflow as a visible code-scanning signal.",
        [Evidence("workflow-set", ".github/workflows", ", ".join(matched) or "none found")],
        "Configure code scanning appropriate to the repository languages and threat model.",
    )


def _testing_primary_check(root: Path, _: str) -> Finding:
    contract_path = root / "harness/project.yaml"
    command = ""
    if contract_path.is_file():
        try:
            payload = json.loads(contract_path.read_text(encoding="utf-8"))
            command = payload["engineering"]["command_contract"]["primary_check"]
        except (KeyError, TypeError, json.JSONDecodeError):
            command = ""
    return _finding(
        "testing.primary-check",
        "testing",
        "pass" if command else "warn",
        "info" if command else "medium",
        "Authoritative local and CI check",
        "A machine-readable primary verification command is declared.",
        [Evidence("project-contract", "harness/project.yaml", command or "not declared")],
        "Declare one authoritative command and run it unchanged in local and CI boundaries.",
    )


def _testing_suite(root: Path, _: str) -> Finding:
    patterns = ("test_*.py", "*_test.py", "*.test.ts", "*.test.js", "*.spec.ts", "*.spec.js")
    tests = tuple(
        sorted(
            path.relative_to(root).as_posix()
            for pattern in patterns
            for path in root.glob(f"tests/**/{pattern}")
            if path.is_file()
        )
    )
    return _finding(
        "testing.suite",
        "testing",
        "pass" if tests else "warn",
        "info" if tests else "medium",
        "Automated tests",
        "A conventional automated test suite is present.",
        [Evidence("path-count", "tests", str(len(tests)))],
        "Add deterministic tests for the project's public and failure-path behavior.",
    )


def _agent_instruction_quality(root: Path, _: str) -> Finding:
    path = root / "AGENTS.md"
    required_signals = ("source", "test", "safety", "verification")
    content = path.read_text(encoding="utf-8").lower() if path.is_file() else ""
    present = tuple(signal for signal in required_signals if signal in content)
    return _finding(
        "agent-readiness.instructions",
        "agent-readiness",
        "pass" if len(present) == len(required_signals) else "warn",
        "info" if len(present) == len(required_signals) else "medium",
        "Agent instruction coverage",
        "Repository instructions expose core evidence, verification, and safety signals.",
        [Evidence("signal-set", "AGENTS.md", f"present={list(present)}")],
        "Document source precedence, tests, verification boundaries, and safety constraints.",
    )


def _parse_skill_frontmatter(path: Path) -> tuple[str, str] | None:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n") or "\n---\n" not in content[4:]:
        return None
    header = content[4:].split("\n---\n", 1)[0]
    values: dict[str, str] = {}
    for line in header.splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"name", "description"}:
            values[key.strip()] = value.strip()
    name = values.get("name", "")
    description = values.get("description", "")
    if not SKILL_NAME.fullmatch(name) or not description:
        return None
    return name, description


def _agent_skills(root: Path, _: str) -> Finding:
    paths = tuple(sorted(root.glob(".agents/skills/*/SKILL.md")))
    invalid = tuple(
        path.relative_to(root).as_posix()
        for path in paths
        if _parse_skill_frontmatter(path) is None
    )
    if not paths:
        status, severity = "warn", "low"
    elif invalid:
        status, severity = "fail", "medium"
    else:
        status, severity = "pass", "info"
    evidence = [Evidence("path-count", ".agents/skills", str(len(paths)))]
    evidence.extend(Evidence("invalid-skill", path, "invalid frontmatter") for path in invalid)
    return _finding(
        "agent-readiness.skills",
        "agent-readiness",
        status,
        severity,
        "Portable agent skills",
        "Repository skills use discoverable SKILL.md files with basic portable metadata.",
        evidence,
        "Use one skill directory per capability with valid name and description frontmatter.",
    )


CHECKS: tuple[tuple[str, Callable[[Path, str], Finding]], ...] = (
    ("governance.instructions", _governance_instructions),
    ("governance.project-contract", _governance_contract),
    ("governance.community-files", _governance_community_files),
    ("git.clean-worktree", _git_clean),
    ("ci.workflows", _ci_workflows),
    ("ci.immutable-actions", _ci_immutable_actions),
    ("security.policy", _security_policy),
    ("security.dependency-updates", _security_updates),
    ("security.code-scanning", _security_code_scanning),
    ("testing.primary-check", _testing_primary_check),
    ("testing.suite", _testing_suite),
    ("agent-readiness.instructions", _agent_instruction_quality),
    ("agent-readiness.skills", _agent_skills),
)
CHECK_IDS = frozenset(item[0] for item in CHECKS)


def load_config(path: Path | None) -> AuditConfig:
    if path is None:
        return AuditConfig()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read configuration: {exc}") from exc
    if not isinstance(payload, dict):
        raise AuditError("configuration must be a JSON object")
    unknown_keys = sorted(set(payload) - {"schema_version", "disabled_checks"})
    if unknown_keys:
        raise AuditError(f"unknown configuration keys: {', '.join(unknown_keys)}")
    if payload.get("schema_version") != "1.0":
        raise AuditError("configuration schema_version must be 1.0")
    disabled = payload.get("disabled_checks", [])
    if not isinstance(disabled, list) or any(not isinstance(item, str) for item in disabled):
        raise AuditError("disabled_checks must be an array of strings")
    unknown_checks = sorted(set(disabled) - CHECK_IDS)
    if unknown_checks:
        raise AuditError(f"unknown disabled checks: {', '.join(unknown_checks)}")
    return AuditConfig(frozenset(disabled))


def audit_repository(target: Path, config: AuditConfig | None = None) -> Report:
    """Audit one repository root without intentionally writing to it."""

    root = target.expanduser().resolve()
    if not root.is_dir():
        raise AuditError(f"target is not a directory: {root}")
    active_config = config or AuditConfig()
    target_state, status_text = _target_state(root)
    findings = tuple(
        check(root, status_text)
        for finding_id, check in CHECKS
        if finding_id not in active_config.disabled_checks
    )
    return Report(
        tool_name="agentic-repo-auditor",
        tool_version=__version__,
        target=target_state,
        findings=findings,
        disabled_checks=tuple(active_config.disabled_checks),
    )
