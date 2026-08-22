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
    lines.extend(
        [
            "## Configuration",
            "",
            f"Disabled checks: {', '.join(f'`{item}`' for item in disabled) or 'none'}.",
            "",
        ]
    )
    return "\n".join(lines)
