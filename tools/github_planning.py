#!/usr/bin/env python3
"""Audit and safely reconcile GitHub planning desired state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, run, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, run, write_json


def validate_contract(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(config.get("repository"), str):
        errors.append("repository must be OWNER/REPOSITORY")
    project = config.get("project")
    if not isinstance(project, dict):
        errors.append("project must be an object")
    else:
        for key in ("owner", "number", "title", "views"):
            if key not in project:
                errors.append(f"project missing {key}")
    for collection, key in (("labels", "name"), ("milestones", "title"), ("fields", "name")):
        items = config.get(collection)
        if not isinstance(items, list):
            errors.append(f"{collection} must be a list")
            continue
        values = [item.get(key) for item in items if isinstance(item, dict)]
        if len(values) != len(items) or any(not value for value in values):
            errors.append(f"every {collection} entry requires {key}")
        if len(values) != len(set(values)):
            errors.append(f"{collection} contains duplicate {key} values")
    return errors


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    if value and isinstance(value[0], list):
        return [item for page in value for item in page if isinstance(item, dict)]
    return [item for item in value if isinstance(item, dict)]


def parse_json_values(output: str, *, command: str) -> Any:
    """Parse one JSON value or the whitespace-separated values emitted by gh pagination."""
    decoder = json.JSONDecoder()
    values: list[Any] = []
    cursor = 0
    while cursor < len(output):
        while cursor < len(output) and output[cursor].isspace():
            cursor += 1
        if cursor == len(output):
            break
        try:
            value, cursor = decoder.raw_decode(output, cursor)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"gh returned invalid JSON for {command}") from exc
        values.append(value)
    if not values:
        raise RuntimeError(f"gh returned no JSON for {command}")
    return values[0] if len(values) == 1 else values


def gh_json(root: Path, *args: str) -> Any:
    result = run(["gh", *args], cwd=root)
    return parse_json_values(result.stdout, command=f"gh {' '.join(args)}")


def read_live(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    repository = config["repository"]
    if repository == "OWNER/REPOSITORY":
        raise ValueError("replace OWNER/REPOSITORY before live GitHub operations")
    identity = run(["gh", "api", "user", "--jq", ".login"], cwd=root).stdout.strip()
    actual_repo = run(
        ["gh", "repo", "view", repository, "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        cwd=root,
    ).stdout.strip()
    if actual_repo.lower() != repository.lower():
        raise RuntimeError(f"resolved repository {actual_repo}, expected {repository}")
    label_pages = gh_json(
        root,
        "api",
        "--paginate",
        f"repos/{repository}/labels?per_page=100",
    )
    milestone_pages = gh_json(
        root,
        "api",
        "--paginate",
        f"repos/{repository}/milestones?state=all&per_page=100",
    )
    fields: list[dict[str, Any]] = []
    project_number = config["project"].get("number")
    if project_number is not None:
        field_data = gh_json(
            root,
            "project",
            "field-list",
            str(project_number),
            "--owner",
            config["project"]["owner"],
            "--format",
            "json",
        )
        fields = field_data.get("fields", []) if isinstance(field_data, dict) else []
    return {
        "authenticated_login": identity,
        "repository": actual_repo,
        "labels": flatten_pages(label_pages),
        "milestones": flatten_pages(milestone_pages),
        "fields": fields,
        "project_audited": project_number is not None,
    }


def diff_state(config: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    live_labels = {item["name"]: item for item in live.get("labels", [])}
    live_milestones = {item["title"]: item for item in live.get("milestones", [])}
    live_fields = {item["name"]: item for item in live.get("fields", [])}

    labels_create: list[dict[str, Any]] = []
    labels_update: list[dict[str, Any]] = []
    for desired in config.get("labels", []):
        current = live_labels.get(desired["name"])
        if current is None:
            labels_create.append(desired)
        elif current.get("color", "").lower() != desired.get("color", "").lower() or (
            current.get("description") or ""
        ) != (desired.get("description") or ""):
            labels_update.append({"desired": desired, "current": current})

    milestones_create: list[dict[str, Any]] = []
    milestones_update: list[dict[str, Any]] = []
    for desired in config.get("milestones", []):
        current = live_milestones.get(desired["title"])
        if current is None:
            milestones_create.append(desired)
        elif (current.get("description") or "") != (desired.get("description") or ""):
            milestones_update.append({"desired": desired, "current": current})

    project_audited = bool(live.get("project_audited"))
    missing_fields = (
        [desired for desired in config.get("fields", []) if desired["name"] not in live_fields]
        if project_audited
        else []
    )
    mismatched_fields = (
        field_mismatches(config.get("fields", []), live.get("fields", []))
        if project_audited
        else []
    )
    warnings: list[str] = []
    if not project_audited:
        warnings.append("project number is null; Project fields and views were not audited")
    else:
        warnings.append(
            "The current tool creates missing fields; existing field mismatches and saved views require manual reconciliation"
        )
    return {
        "labels": {"create": labels_create, "update": labels_update},
        "milestones": {"create": milestones_create, "update": milestones_update},
        "project": {
            "missing_fields": missing_fields,
            "mismatched_fields": mismatched_fields,
            "configured_views": config.get("project", {}).get("views", []),
        },
        "warnings": warnings,
    }


def has_drift(diff: dict[str, Any]) -> bool:
    return any(
        (
            diff["labels"]["create"],
            diff["labels"]["update"],
            diff["milestones"]["create"],
            diff["milestones"]["update"],
            diff["project"]["missing_fields"],
            diff["project"]["mismatched_fields"],
        )
    )


def project_bootstrap_plan(config: dict[str, Any]) -> dict[str, Any]:
    project = config["project"]
    bootstrap = project.get("bootstrap", {"method": "create", "link_repository": True})
    method = bootstrap.get("method", "create")
    errors: list[str] = []
    if method not in {"create", "copy"}:
        errors.append(f"unsupported project bootstrap method: {method}")
    if method == "copy" and (
        not bootstrap.get("source_owner") or bootstrap.get("source_number") is None
    ):
        errors.append("copy method requires source_owner and source_number")
    actions: list[dict[str, Any]] = []
    if project.get("number") is None:
        actions.append(
            {
                "action": method,
                "title": project["title"],
                "owner": project["owner"],
                "source_owner": bootstrap.get("source_owner"),
                "source_number": bootstrap.get("source_number"),
            }
        )
    actions.extend({"action": "ensure-field", **field} for field in config.get("fields", []))
    if bootstrap.get("link_repository", True):
        actions.append({"action": "link-repository", "repository": config["repository"]})
    actions.extend({"action": "manual-view", **view} for view in project.get("views", []))
    return {"ok": not errors, "errors": errors, "dry_run": True, "actions": actions}


def field_mismatches(
    desired_fields: list[dict[str, Any]],
    live_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    live = {item.get("name"): item for item in live_fields}
    expected_types = {
        "SINGLE_SELECT": "ProjectV2SingleSelectField",
        "TEXT": "ProjectV2Field",
        "NUMBER": "ProjectV2Field",
        "DATE": "ProjectV2Field",
        "ITERATION": "ProjectV2IterationField",
    }
    mismatches: list[dict[str, Any]] = []
    for desired in desired_fields:
        current = live.get(desired["name"])
        if current is None:
            continue
        reasons = []
        expected_type = expected_types.get(desired["data_type"])
        if expected_type and current.get("type") != expected_type:
            reasons.append(f"type is {current.get('type')}, expected {expected_type}")
        if desired["data_type"] == "SINGLE_SELECT":
            actual_options = [item.get("name") for item in current.get("options", [])]
            if actual_options != desired.get("options", []):
                reasons.append(
                    f"options are {actual_options}, expected {desired.get('options', [])}"
                )
        if reasons:
            mismatches.append({"name": desired["name"], "reasons": reasons, "current": current})
    return mismatches


def bootstrap_project(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    project = config["project"]
    bootstrap = project.get("bootstrap", {"method": "create", "link_repository": True})
    repository = config["repository"]
    if repository == "OWNER/REPOSITORY":
        raise ValueError("replace OWNER/REPOSITORY before live GitHub operations")
    run(
        ["gh", "repo", "view", repository, "--json", "nameWithOwner"],
        cwd=root,
    )
    number = project.get("number")
    operations: list[str] = []
    if number is None:
        method = bootstrap.get("method", "create")
        if method == "copy":
            created = gh_json(
                root,
                "project",
                "copy",
                str(bootstrap["source_number"]),
                "--source-owner",
                bootstrap["source_owner"],
                "--target-owner",
                project["owner"],
                "--title",
                project["title"],
                "--format",
                "json",
            )
        else:
            created = gh_json(
                root,
                "project",
                "create",
                "--owner",
                project["owner"],
                "--title",
                project["title"],
                "--format",
                "json",
            )
        number = created.get("number")
        if number is None:
            raise RuntimeError("created Project response did not include a number")
        project["number"] = number
        write_json(root / ".github/planning.json", config)
        verb = "copied" if method == "copy" else "created"
        operations.append(f"{verb} Project #{number}")

    fields_data = gh_json(
        root,
        "project",
        "field-list",
        str(number),
        "--owner",
        project["owner"],
        "--format",
        "json",
    )
    existing = {
        item["name"]
        for item in fields_data.get("fields", [])
        if isinstance(item, dict) and item.get("name")
    }
    for field in config.get("fields", []):
        if field["name"] in existing:
            continue
        argv = [
            "gh",
            "project",
            "field-create",
            str(number),
            "--owner",
            project["owner"],
            "--name",
            field["name"],
            "--data-type",
            field["data_type"],
            "--format",
            "json",
        ]
        if field["data_type"] == "SINGLE_SELECT":
            argv.extend(["--single-select-options", ",".join(field.get("options", []))])
        run(argv, cwd=root)
        operations.append(f"created Project field {field['name']}")
    if bootstrap.get("link_repository", True):
        run(
            [
                "gh",
                "project",
                "link",
                str(number),
                "--owner",
                project["owner"],
                "--repo",
                repository,
            ],
            cwd=root,
        )
        operations.append(f"linked Project #{number} to {repository}")
    post_fields = gh_json(
        root,
        "project",
        "field-list",
        str(number),
        "--owner",
        project["owner"],
        "--format",
        "json",
    )
    names = {item.get("name") for item in post_fields.get("fields", [])}
    missing = [field["name"] for field in config.get("fields", []) if field["name"] not in names]
    mismatched = field_mismatches(config.get("fields", []), post_fields.get("fields", []))
    return {
        "ok": not missing and not mismatched,
        "project_number": number,
        "operations": operations,
        "missing_fields": missing,
        "mismatched_fields": mismatched,
        "manual_views": project.get("views", []),
    }


def apply_supported(root: Path, config: dict[str, Any], diff: dict[str, Any]) -> list[str]:
    repository = config["repository"]
    operations: list[str] = []
    for desired in diff["labels"]["create"] + [
        item["desired"] for item in diff["labels"]["update"]
    ]:
        run(
            [
                "gh",
                "label",
                "create",
                desired["name"],
                "--repo",
                repository,
                "--color",
                desired["color"],
                "--description",
                desired.get("description", ""),
                "--force",
            ],
            cwd=root,
        )
        operations.append(f"reconciled label {desired['name']}")

    for desired in diff["milestones"]["create"]:
        run(
            [
                "gh",
                "api",
                "--method",
                "POST",
                f"repos/{repository}/milestones",
                "-f",
                f"title={desired['title']}",
                "-f",
                f"description={desired.get('description', '')}",
            ],
            cwd=root,
        )
        operations.append(f"created milestone {desired['title']}")

    for item in diff["milestones"]["update"]:
        desired = item["desired"]
        number = item["current"]["number"]
        run(
            [
                "gh",
                "api",
                "--method",
                "PATCH",
                f"repos/{repository}/milestones/{number}",
                "-f",
                f"description={desired.get('description', '')}",
            ],
            cwd=root,
        )
        operations.append(f"updated milestone {desired['title']}")
    return operations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--offline", action="store_true")
    apply = subparsers.add_parser("apply")
    apply.add_argument("--yes", action="store_true", help="Perform supported live writes")
    bootstrap = subparsers.add_parser("bootstrap-project")
    bootstrap.add_argument(
        "--yes", action="store_true", help="Create or copy and configure a Project"
    )
    args = parser.parse_args()

    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    try:
        config = load_json(root / ".github/planning.json")
        errors = validate_contract(config)
        if errors:
            print(json.dumps({"ok": False, "errors": errors}, indent=2))
            return 1
        if args.command == "audit" and args.offline:
            warnings = []
            if config["repository"] == "OWNER/REPOSITORY":
                warnings.append("template placeholders remain; live audit is not available")
            print(json.dumps({"ok": True, "mode": "offline", "warnings": warnings}, indent=2))
            return 0

        if args.command == "bootstrap-project":
            plan = project_bootstrap_plan(config)
            if not plan["ok"]:
                print(json.dumps(plan, indent=2))
                return 1
            if not args.yes:
                print(json.dumps(plan, indent=2))
                print("No GitHub writes performed. Re-run with --yes after reviewing the plan.")
                return 0
            result = bootstrap_project(root, config)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1

        live = read_live(root, config)
        diff = diff_state(config, live)
        if args.command == "audit":
            print(
                json.dumps(
                    {
                        "ok": not has_drift(diff),
                        "mode": "live",
                        "identity": live["authenticated_login"],
                        "repository": live["repository"],
                        "diff": diff,
                    },
                    indent=2,
                )
            )
            return 1 if has_drift(diff) else 0

        print(json.dumps({"dry_run": not args.yes, "diff": diff}, indent=2))
        if not args.yes:
            print("No GitHub writes performed. Re-run with --yes after reviewing the plan.")
            return 0
        operations = apply_supported(root, config, diff)
        post = diff_state(config, read_live(root, config))
        print(json.dumps({"operations": operations, "post_apply_diff": post}, indent=2))
        return 1 if has_drift(post) else 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
