#!/usr/bin/env python3
"""Collect, merge, and render durable project intake records."""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from .common import get_nested, load_json, repository_root, set_nested, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import get_nested, load_json, repository_root, set_nested, utc_now, write_json


MODES = ("new", "adopt", "refresh", "gap-only")
ALLOWED_PREFIXES = ("project.", "intent.", "constraints.", "engineering.", "autonomy.")
PROFILE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GENERATED_PARTS = {
    ".git",
    ".harness",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}
GENERATED_NAMES = {".coverage"}
QUESTION_FIELDS: tuple[tuple[str, str, bool], ...] = (
    ("project.name", "Project name", False),
    ("project.summary", "What does it do, for whom, and why", False),
    ("project.repository", "GitHub repository as OWNER/REPOSITORY", False),
    ("project.profile", "Profile: generic, python-data, web-service, or agent-system", False),
    ("intent.users", "Primary users (comma-separated)", True),
    ("intent.outcomes", "Desired outcomes (comma-separated)", True),
    ("intent.success_metrics", "Measurable success criteria (comma-separated)", True),
    ("intent.in_scope", "In-scope capabilities (comma-separated)", True),
    ("intent.out_of_scope", "Explicit exclusions (comma-separated)", True),
    ("constraints.data_classification", "Data classification", False),
    ("constraints.deployment", "Deployment target or none", False),
    ("constraints.licenses", "Accepted project license or licenses (comma-separated)", True),
    ("engineering.languages", "Languages (comma-separated)", True),
    ("engineering.build_commands", "Build commands (comma-separated)", True),
    ("engineering.test_commands", "Test commands (comma-separated)", True),
    (
        "engineering.command_contract.primary_check",
        "One command that runs the authoritative local/CI check",
        False,
    ),
    (
        "engineering.command_contract.bootstrap",
        "Reproducible dependency/bootstrap command or not-applicable with reason",
        False,
    ),
    (
        "engineering.command_contract.format_check",
        "Format-check command or not-applicable with reason",
        False,
    ),
    ("engineering.command_contract.lint", "Lint command or not-applicable with reason", False),
    (
        "engineering.command_contract.typecheck",
        "Type-check command or not-applicable with reason",
        False,
    ),
    ("engineering.command_contract.unit", "Unit-test command or not-applicable with reason", False),
    (
        "engineering.command_contract.integration",
        "Integration-test command or not-applicable with reason",
        False,
    ),
    (
        "engineering.command_contract.package_smoke",
        "Clean package/build/entrypoint smoke command or not-applicable with reason",
        False,
    ),
    ("engineering.quality.dependency_lock", "Dependency lockfile or conditional policy", False),
    (
        "engineering.quality.coverage_policy",
        "Coverage ratchet, threshold, or explicit exception policy",
        False,
    ),
    ("engineering.versioning.strategy", "Versioning: semver, calver, independent, or none", False),
    ("engineering.versioning.current", "Initial product version", False),
    (
        "engineering.versioning.public_contract",
        "Versioned public contracts: API, CLI, config, schema, artifacts, or user behavior",
        True,
    ),
    (
        "engineering.versioning.source",
        "Canonical product-version source, for example pyproject.toml:project.version",
        False,
    ),
    ("autonomy.level", "Autonomy level: supervised, bounded, or high", False),
)
ESSENTIAL_FIELDS = (
    "project.name",
    "project.summary",
    "project.repository",
    "project.profile",
    "intent.users",
    "intent.outcomes",
    "intent.success_metrics",
    "intent.in_scope",
    "intent.out_of_scope",
    "constraints.data_classification",
    "constraints.deployment",
    "constraints.licenses",
    "engineering.languages",
    "engineering.test_commands",
    "engineering.command_contract.primary_check",
    "engineering.command_contract.bootstrap",
    "engineering.command_contract.format_check",
    "engineering.command_contract.lint",
    "engineering.command_contract.typecheck",
    "engineering.command_contract.unit",
    "engineering.command_contract.integration",
    "engineering.command_contract.package_smoke",
    "engineering.quality.dependency_lock",
    "engineering.quality.coverage_policy",
    "engineering.versioning.strategy",
    "autonomy.level",
)


def normalize_answer(value: Any, *, source: str, recorded_at: str) -> dict[str, Any]:
    if isinstance(value, dict) and "value" in value:
        answer = copy.deepcopy(value)
        answer.setdefault("status", "confirmed")
        answer.setdefault("source", source)
        answer.setdefault("recorded_at", recorded_at)
        return answer
    return {
        "value": value,
        "status": "confirmed",
        "source": source,
        "recorded_at": recorded_at,
    }


def load_answers(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = load_json(path)
    if "answers" in data and isinstance(data["answers"], dict):
        return data["answers"]
    if not isinstance(data, dict):
        raise ValueError("answers file must contain an object")
    return data


def is_resolved(value: Any) -> bool:
    if isinstance(value, str) and value.startswith("not-applicable:"):
        return bool(value.partition(":")[2].strip())
    return value not in (None, "", "TBD", [], {})


def interactive_answers(
    project: dict[str, Any],
    existing: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    print(
        "I will inspect known values and ask only material gaps. "
        "Leave an answer blank to retain the current value or mark it TBD."
    )
    for field, question, is_list in QUESTION_FIELDS:
        prior_record = existing.get(field, {})
        prior = prior_record.get("value") if isinstance(prior_record, dict) else None
        current = prior if is_resolved(prior) else get_nested(project, field)
        if mode == "gap-only" and is_resolved(current):
            continue
        suffix = f" [{current}]" if is_resolved(current) else ""
        response = input(f"{question}{suffix}: ").strip()
        if not response:
            if is_resolved(current):
                continue
            value: Any = []
            status = "TBD"
        else:
            value = (
                [item.strip() for item in response.split(",") if item.strip()]
                if is_list
                else response
            )
            status = "confirmed"
        answers[field] = {
            "value": value,
            "status": status,
            "source": "user-interview",
            "recorded_at": utc_now(),
        }
    return answers


def apply_profile_defaults(
    project: dict[str, Any], profile: dict[str, Any], *, override: bool = False
) -> None:
    for dotted_key, value in profile.get("defaults", {}).items():
        if override or not is_resolved(get_nested(project, dotted_key)):
            set_nested(project, dotted_key, copy.deepcopy(value))


def render(
    base_project: dict[str, Any],
    planning: dict[str, Any],
    answers: dict[str, Any],
    *,
    profile_root: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    project = copy.deepcopy(base_project)
    requested_profile = answers.get("project.profile")
    if isinstance(requested_profile, dict):
        requested_profile = requested_profile.get("value")
    if is_resolved(requested_profile):
        set_nested(project, "project.profile", copy.deepcopy(requested_profile))

    profile_id = get_nested(project, "project.profile", "generic")
    if not isinstance(profile_id, str) or not PROFILE_ID.fullmatch(profile_id):
        raise ValueError(f"invalid project profile ID: {profile_id}")
    profiles = profile_root or Path(__file__).resolve().parents[1] / "harness/profiles"
    profile_path = profiles / f"{profile_id}.json"
    if not profile_path.is_file():
        raise ValueError(f"unknown project profile: {profile_id}")
    apply_profile_defaults(
        project,
        load_json(profile_path),
        override=bool(base_project.get("template_mode", False)),
    )

    for dotted_key, record in answers.items():
        if dotted_key.startswith(ALLOWED_PREFIXES):
            value = record.get("value") if isinstance(record, dict) else record
            set_nested(project, dotted_key, copy.deepcopy(value))

    missing = [field for field in ESSENTIAL_FIELDS if not is_resolved(get_nested(project, field))]
    if get_nested(project, "engineering.quality.dependency_lock") == "required-if-dependencies":
        missing.append("engineering.quality.dependency_lock")
    strategy = get_nested(project, "engineering.versioning.strategy")
    if strategy == "none":
        set_nested(project, "engineering.versioning.current", "not-applicable")
        set_nested(project, "engineering.versioning.public_contract", [])
        set_nested(project, "engineering.versioning.source", "not-applicable")
    else:
        for field in (
            "engineering.versioning.current",
            "engineering.versioning.public_contract",
            "engineering.versioning.source",
        ):
            if not is_resolved(get_nested(project, field)):
                missing.append(field)
    project["template_mode"] = bool(missing)
    project["project"]["status"] = "draft" if missing else "active"
    project["project"]["lifecycle"] = project["project"].get("lifecycle") or "new"
    project["open_questions"] = [f"Resolve {field}" for field in missing]

    rendered_planning = copy.deepcopy(planning)
    repository = get_nested(project, "project.repository")
    if isinstance(repository, str) and "/" in repository and repository != "OWNER/REPOSITORY":
        owner = repository.split("/", 1)[0]
        rendered_planning["repository"] = repository
        rendered_planning["project"]["owner"] = owner
    return project, rendered_planning, missing


def render_charter(project: dict[str, Any], intake_source: str) -> str:
    intent = project["intent"]
    constraints = project["constraints"]
    engineering = project["engineering"]
    versioning = engineering["versioning"]
    if versioning["strategy"] == "none":
        product_version_contract = "- Product versioning: none (no versioned product contract)"
    else:
        product_version_contract = (
            f"- Product versioning: {versioning['strategy']} at {versioning['current']}\n"
            f"- Version source: {versioning['source']}\n"
            f"- Public contract: {', '.join(versioning['public_contract']) or 'TBD'}"
        )

    def bullets(values: Any) -> str:
        if not values:
            return "- TBD"
        if not isinstance(values, list):
            values = [values]
        return "\n".join(f"- {value}" for value in values)

    return f"""# Project charter

Status: {project["project"]["status"]}

## Purpose

{project["project"]["summary"]}

Primary users:

{bullets(intent.get("users"))}

## Outcomes and success measures

Desired outcomes:

{bullets(intent.get("outcomes"))}

Success measures:

{bullets(intent.get("success_metrics"))}

## Scope

### In

{bullets(intent.get("in_scope"))}

### Out

{bullets(intent.get("out_of_scope"))}

## Constraints

- Security: {", ".join(constraints.get("security", [])) or "TBD"}
- Data classification: {constraints.get("data_classification", "TBD")}
- Deployment: {constraints.get("deployment", "TBD")}
- Budget: {constraints.get("budget", "TBD")}
- Licensing: {", ".join(constraints.get("licenses", [])) or "TBD"}

## Engineering and release contract

- Primary check: {engineering["command_contract"]["primary_check"]}
- Dependency lock: {engineering["quality"]["dependency_lock"]}
- Coverage policy: {engineering["quality"]["coverage_policy"]}
{product_version_contract}
- Harness version: {project["harness_version"]}

## Authority

- Autonomy level: {project["autonomy"]["level"]}
- Network writes: {project["autonomy"]["network_writes"]}
- Destructive actions: {project["autonomy"]["destructive_actions"]}
- Release: {project["autonomy"]["release"]}
- Policy changes: {project["autonomy"]["policy_changes"]}

Generated from `harness/project.yaml` and {intake_source}.
"""


def copy_template(source: Path, target: Path) -> None:
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(
            *GENERATED_PARTS,
            *GENERATED_NAMES,
            "*.egg-info",
            "*.pyc",
        ),
    )


def copy_missing_for_adoption(source: Path, target: Path) -> list[str]:
    collisions: list[str] = []
    for source_path in sorted(source.rglob("*")):
        relative = source_path.relative_to(source)
        if (
            any(part in GENERATED_PARTS or part.endswith(".egg-info") for part in relative.parts)
            or source_path.name in GENERATED_NAMES
            or source_path.suffix == ".pyc"
        ):
            continue
        target_path = target / relative
        if source_path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
            continue
        if target_path.exists():
            collisions.append(str(relative))
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
    return collisions


def adoption_gap_report(collisions: list[str]) -> str:
    lines = "\n".join(f"- `{path}`" for path in collisions) or "- None."
    return f"""# Harness adoption gaps

The adopter preserved every pre-existing file. The following paths collided with template paths and require deliberate human reconciliation:

{lines}

## Required review

1. Merge the context-readiness, source-precedence, role, loop, safety, verification, and skill-routing rules into the authoritative `AGENTS.md`.
2. Reconcile existing build and test entrypoints with `Makefile` and the harness workflow.
3. Reconcile product version, public contract, dependency lock, coverage policy, and release notes with the existing package or deployment system.
4. Reconcile existing GitHub templates, security settings, workflows, and planning state; never overwrite live conventions blindly.
5. Confirm ignored local runtime paths include `.harness/runs/`, `.harness/challenge-results/`, and `.harness/preferences.local.json`.
6. Run `python3 tools/harness_check.py` and resolve every error before calling adoption complete.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--mode", choices=MODES, default="new")
    parser.add_argument("--target", type=Path)
    parser.add_argument("--apply", action="store_true", help="Write rendered artifacts")
    args = parser.parse_args()

    source = repository_root(Path(__file__).parent)
    target = args.target.resolve() if args.target else source
    source_project = load_json(source / "harness/project.yaml")
    if target != source and not source_project.get("template_mode", False):
        print(
            "error: cross-repository intake must run from the template-mode repository; "
            "run project_intake.py inside the intended application repository",
            file=sys.stderr,
        )
        return 2
    target_exists = (target / "harness/project.yaml").is_file()
    adopting_existing = (
        target != source and target.exists() and not target_exists and args.mode == "adopt"
    )
    if target.exists() and not target_exists and target != source and not adopting_existing:
        print(f"error: target exists but is not a harness repository: {target}", file=sys.stderr)
        print(
            "hint: use --mode adopt to preserve and overlay an existing repository", file=sys.stderr
        )
        return 2

    base_root = target if target_exists else source
    project = load_json(base_root / "harness/project.yaml")
    planning = load_json(base_root / ".github/planning.json")
    intake_path = base_root / "harness/intake.json"
    existing_record = load_json(intake_path) if intake_path.is_file() else {"answers": {}}
    recorded_at = utc_now()
    merged = copy.deepcopy(existing_record.get("answers", {}))
    provided = load_answers(args.answers)
    for field, value in provided.items():
        merged[field] = normalize_answer(
            value,
            source=str(args.answers) if args.answers else "provided",
            recorded_at=recorded_at,
        )
    if args.interactive:
        merged.update(interactive_answers(project, merged, mode=args.mode))
    if not args.interactive and args.answers is None:
        print("error: provide --answers or --interactive", file=sys.stderr)
        return 2

    rendered_project, rendered_planning, missing = render(
        project,
        planning,
        merged,
        profile_root=base_root / "harness/profiles",
    )
    intake = {
        "schema_version": "1.0",
        "mode": args.mode,
        "captured_at": recorded_at,
        "answers": merged,
        "contradictions": existing_record.get("contradictions", []),
        "missing_essential_fields": missing,
    }

    if not args.apply:
        print("dry run; no files written")
        print(
            json.dumps(
                {"target": str(target), "missing": missing, "project": rendered_project}, indent=2
            )
        )
        return 0

    collisions: list[str] = []
    if adopting_existing:
        collisions = copy_missing_for_adoption(source, target)
    elif not target_exists:
        copy_template(source, target)
    write_json(target / "harness/project.yaml", rendered_project)
    write_json(target / "harness/intake.json", intake)
    planning_target = target / ".github/planning.json"
    if adopting_existing and ".github/planning.json" in collisions:
        planning_target = target / ".github/planning.harness-proposed.json"
    write_json(planning_target, rendered_planning)
    charter_target = target / "docs/project/charter.md"
    if adopting_existing and "docs/project/charter.md" in collisions:
        charter_target = target / "docs/project/charter.harness-proposed.md"
    charter_target.write_text(
        render_charter(rendered_project, "`harness/intake.json`"),
        encoding="utf-8",
    )
    if adopting_existing:
        (target / "docs/project/adoption-gaps.md").write_text(
            adoption_gap_report(collisions),
            encoding="utf-8",
        )
    print(f"rendered project intake at {target}")
    if missing:
        print("context readiness: provisional; unresolved essential fields:")
        for field in missing:
            print(f"  - {field}")
    else:
        print("context readiness: sufficient for bounded planning")
    if collisions:
        print(f"preserved {len(collisions)} colliding files; see docs/project/adoption-gaps.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
