"""Versioned report model for repository audit evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "1.1"
STATUSES = ("pass", "warn", "fail", "not-applicable", "unknown")
SEVERITIES = ("info", "low", "medium", "high")
CATEGORIES = ("governance", "git", "ci", "security", "testing", "agent-readiness")


@dataclass(frozen=True, order=True)
class Evidence:
    """One observable fact supporting a finding."""

    kind: str
    path: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "path": self.path, "value": self.value}


@dataclass(frozen=True)
class Finding:
    """One stable repository assessment result."""

    finding_id: str
    category: str
    status: str
    severity: str
    title: str
    description: str
    evidence: tuple[Evidence, ...]
    remediation: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"unknown finding category: {self.category}")
        if self.status not in STATUSES:
            raise ValueError(f"unknown finding status: {self.status}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"unknown finding severity: {self.severity}")
        if not self.evidence:
            raise ValueError(f"finding {self.finding_id} requires evidence")

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.finding_id,
            "category": self.category,
            "status": self.status,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence": [item.as_dict() for item in sorted(self.evidence)],
            "remediation": self.remediation,
        }


@dataclass(frozen=True)
class TargetState:
    """Deterministic identity of the audited repository state."""

    name: str
    revision: str
    branch: str
    dirty: bool
    state_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "revision": self.revision,
            "branch": self.branch,
            "dirty": self.dirty,
            "state_id": self.state_id,
        }


@dataclass(frozen=True)
class ProjectContractDeclaration:
    """Normalized configured evidence for the project-contract finding."""

    path: str | None = None
    not_applicable_reason: str | None = None

    def __post_init__(self) -> None:
        if (self.path is None) == (self.not_applicable_reason is None):
            raise ValueError("project contract declaration requires exactly one disposition")

    def as_dict(self) -> dict[str, str]:
        if self.path is not None:
            return {"path": self.path}
        assert self.not_applicable_reason is not None
        return {"not_applicable_reason": self.not_applicable_reason}


@dataclass(frozen=True)
class Report:
    """Complete deterministic audit report."""

    tool_name: str
    tool_version: str
    target: TargetState
    findings: tuple[Finding, ...]
    disabled_checks: tuple[str, ...] = ()
    project_contract: ProjectContractDeclaration | None = None

    def as_dict(self) -> dict[str, Any]:
        ordered = tuple(sorted(self.findings, key=lambda item: item.finding_id))
        by_status = {status: sum(item.status == status for item in ordered) for status in STATUSES}
        by_severity = {
            severity: sum(item.severity == severity for item in ordered) for severity in SEVERITIES
        }
        return {
            "schema_version": SCHEMA_VERSION,
            "tool": {"name": self.tool_name, "version": self.tool_version},
            "target": self.target.as_dict(),
            "configuration": {
                "disabled_checks": list(sorted(self.disabled_checks)),
                "evidence": {
                    "project_contract": (
                        self.project_contract.as_dict()
                        if self.project_contract is not None
                        else None
                    )
                },
            },
            "summary": {
                "total": len(ordered),
                "by_status": by_status,
                "by_severity": by_severity,
            },
            "findings": [item.as_dict() for item in ordered],
        }
