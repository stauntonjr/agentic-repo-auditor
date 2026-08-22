"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .audit import AuditError, audit_repository, load_config
from .render import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentic-repo-auditor",
        description="Audit repository engineering and agent-readiness evidence without modifying it.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="Audit one local Git repository root")
    audit.add_argument("target", nargs="?", type=Path, default=Path("."))
    audit.add_argument("--format", choices=("json", "markdown"), default="markdown")
    audit.add_argument("--config", type=Path)
    audit.add_argument(
        "--fail-on",
        choices=("none", "warn", "fail"),
        default="fail",
        help="Return exit status 1 when a finding reaches this status (default: fail)",
    )
    return parser


def _result_status(statuses: set[str], fail_on: str) -> int:
    if fail_on == "none":
        return 0
    if fail_on == "warn" and statuses.intersection({"warn", "fail"}):
        return 1
    if fail_on == "fail" and "fail" in statuses:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        report = audit_repository(args.target, config)
    except AuditError as exc:
        print(f"agentic-repo-auditor: {exc}", file=sys.stderr)
        return 2
    rendered = render_json(report) if args.format == "json" else render_markdown(report)
    sys.stdout.write(rendered)
    return _result_status({finding.status for finding in report.findings}, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
