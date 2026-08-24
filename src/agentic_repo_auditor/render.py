"""Deterministic report renderers."""

from __future__ import annotations

import json

from .model import Report


def render_json(report: Report) -> str:
    return json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n"


def render_markdown(report: Report) -> str:
    payload = report.as_dict()
    target = payload["target"]
    summary = payload["summary"]
    lines = [
        "# Repository audit report",
        "",
        f"- Tool: `{payload['tool']['name']} {payload['tool']['version']}`",
        f"- Report schema: `{payload['schema_version']}`",
        f"- Target: `{target['name']}`",
        f"- Revision: `{target['revision']}`",
        f"- Branch: `{target['branch']}`",
        f"- Dirty worktree: `{'yes' if target['dirty'] else 'no'}`",
        f"- State identity: `{target['state_id']}`",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {status} | {count} |" for status, count in summary["by_status"].items())
    lines.extend(["", "## Findings", ""])
    for finding in payload["findings"]:
        lines.extend(
            [
                f"### {finding['id']}: {finding['title']}",
                "",
                f"- Category: `{finding['category']}`",
                f"- Status: `{finding['status']}`",
                f"- Severity: `{finding['severity']}`",
                f"- Description: {finding['description']}",
                "- Evidence:",
            ]
        )
        lines.extend(
            f"  - `{item['kind']}` at `{item['path']}`: {item['value']}"
            for item in finding["evidence"]
        )
        lines.extend([f"- Remediation: {finding['remediation']}", ""])
    disabled = payload["configuration"]["disabled_checks"]
    project_contract = payload["configuration"]["evidence"]["project_contract"]
    if project_contract is None:
        project_contract_text = "automatic detection"
    elif "path" in project_contract:
        project_contract_text = f"configured path `{project_contract['path']}`"
    else:
        project_contract_text = "not applicable: " + project_contract["not_applicable_reason"]
    primary_check = payload["configuration"]["evidence"]["primary_check"]
    if primary_check is None:
        primary_check_text = "automatic detection"
    elif "command" in primary_check:
        primary_check_text = f"`{primary_check['command']}` from `{primary_check['source']}`"
    else:
        primary_check_text = "not applicable: " + primary_check["not_applicable_reason"]
    lines.extend(
        [
            "## Configuration",
            "",
            f"Disabled checks: {', '.join(f'`{item}`' for item in disabled) or 'none'}.",
            f"Project-contract evidence: {project_contract_text}.",
            f"Primary-check evidence: {primary_check_text}.",
            "",
        ]
    )
    return "\n".join(lines)
