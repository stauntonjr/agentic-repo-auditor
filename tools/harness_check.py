#!/usr/bin/env python3
"""Validate the portable harness without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from .check_actions_supply_chain import check_workflows
    from .common import load_json, repository_root
    from .harness_upgrade import safe_path, sha256, validate_lock, validate_ownership_policy
    from .product_version import product_version_status
    from .run_quality import command_argv
except ImportError:  # Direct script execution.
    from check_actions_supply_chain import check_workflows
    from common import load_json, repository_root
    from harness_upgrade import safe_path, sha256, validate_lock, validate_ownership_policy
    from product_version import product_version_status
    from run_quality import command_argv


REQUIRED_PATHS = (
    ".editorconfig",
    ".gitattributes",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "README.md",
    "SECURITY.md",
    "tools/check_actions_supply_chain.py",
    "tools/product_version.py",
    "tools/python_package_smoke.py",
    "tools/run_quality.py",
    "harness/project.yaml",
    "harness/loops/engineering-loop.yaml",
    "harness/schemas/project.schema.json",
    "harness/schemas/intake.schema.json",
    "harness/schemas/loop-run.schema.json",
    "harness/schemas/loop-report.schema.json",
    "harness/schemas/challenge.schema.json",
    "harness/schemas/migration.schema.json",
    "harness/schemas/lock.schema.json",
    "harness/schemas/ownership.schema.json",
    "harness/schemas/preferences.schema.json",
    "harness/schemas/eval-scenarios.schema.json",
    "harness/schemas/provider-adapter.schema.json",
    "harness/adapters/codex.json",
    "harness/adapters/pi.json",
    "harness/evals/scenarios.json",
    "harness/version.json",
    "harness/ownership.json",
    "harness.lock",
    ".github/planning.json",
    ".github/dependabot.yml",
    ".github/actions-allowlist.json",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-review.yml",
    ".pi/settings.json",
    "docs/project/charter.md",
    "docs/project/engineering-baseline.md",
    "docs/project/handoff.md",
)
ROLE_IDS = {"orchestrator", "explorer", "implementer", "verifier", "release-steward"}
ROLE_FILES = ROLE_IDS | {"human-owner"}
TERMINAL_STATES = {"reported", "blocked", "abandoned"}
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
COMMAND_KEYS = {
    "primary_check",
    "bootstrap",
    "format_check",
    "lint",
    "typecheck",
    "unit",
    "integration",
    "package_smoke",
}
QUALITY_CHECKS = COMMAND_KEYS - {"primary_check", "bootstrap"}


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)


def parse_skill_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid frontmatter line: {line}")
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


def validate_project(root: Path, result: Result) -> dict[str, Any]:
    project = load_json(root / "harness/project.yaml")
    result.checked.append("project contract")
    for key in (
        "schema_version",
        "harness_version",
        "project",
        "intent",
        "engineering",
        "autonomy",
        "sources_of_truth",
        "github",
    ):
        result.require(key in project, f"harness/project.yaml missing top-level key: {key}")
    project_data = project.get("project", {})
    for key in ("name", "summary", "lifecycle", "profile", "status", "repository"):
        result.require(key in project_data, f"project contract missing project.{key}")
    ranks = [entry.get("rank") for entry in project.get("sources_of_truth", [])]
    result.require(
        ranks == list(range(1, len(ranks) + 1)),
        "sources_of_truth ranks must be unique and contiguous starting at 1",
    )
    profile = project_data.get("profile")
    result.require(
        isinstance(profile, str)
        and bool(SKILL_NAME.fullmatch(profile))
        and (root / "harness/profiles" / f"{profile}.json").is_file(),
        f"selected profile does not exist: {profile}",
    )
    engineering = project.get("engineering", {})
    commands = engineering.get("command_contract", {})
    result.require(
        set(commands) == COMMAND_KEYS,
        "engineering.command_contract must define the complete portable command set",
    )
    quality = engineering.get("quality", {})
    for key in ("dependency_lock", "coverage_policy", "required_checks", "property_testing"):
        result.require(key in quality, f"engineering.quality missing {key}")
    required_checks = quality.get("required_checks", [])
    result.require(
        isinstance(required_checks, list) and bool(required_checks),
        "engineering.quality.required_checks must be a non-empty list",
    )
    if isinstance(required_checks, list):
        unknown_checks = sorted(set(required_checks) - QUALITY_CHECKS)
        result.require(
            not unknown_checks,
            "engineering.quality.required_checks contains unknown capabilities: "
            + ", ".join(unknown_checks),
        )
    versioning = engineering.get("versioning", {})
    for key in (
        "strategy",
        "current",
        "public_contract",
        "source",
        "tag_prefix",
        "pre_1_0_policy",
        "release_notes",
    ):
        result.require(key in versioning, f"engineering.versioning missing {key}")
    strategy = versioning.get("strategy")
    result.require(
        strategy in {"TBD", "semver", "calver", "independent", "none"},
        f"unsupported product versioning strategy: {strategy}",
    )
    if strategy == "semver":
        result.require(
            bool(SEMVER.fullmatch(str(versioning.get("current", "")))),
            "SemVer product current version is invalid",
        )
        result.require(
            bool(versioning.get("public_contract")),
            "SemVer requires a declared public compatibility contract",
        )
    security = project.get("github", {}).get("security", {})
    result.require(
        security.get("action_pinning") == "full-commit-sha",
        "GitHub Action policy must require full commit SHAs",
    )
    result.require(
        security.get("workflow_permissions") == "least-privilege",
        "GitHub workflow policy must require least privilege",
    )
    if not project.get("template_mode", False):
        unresolved = json.dumps(project_data)
        result.require(
            "OWNER/REPOSITORY" not in unresolved,
            "instantiated project contract still contains OWNER/REPOSITORY",
        )
        for dotted_key, value in (
            ("project.name", project_data.get("name")),
            ("project.summary", project_data.get("summary")),
            ("intent.users", project.get("intent", {}).get("users")),
            ("intent.outcomes", project.get("intent", {}).get("outcomes")),
            ("intent.success_metrics", project.get("intent", {}).get("success_metrics")),
            ("constraints.licenses", project.get("constraints", {}).get("licenses")),
        ):
            result.require(
                value not in (None, "", "TBD", []),
                f"unresolved essential field: {dotted_key}",
            )
        for capability in sorted(COMMAND_KEYS):
            command = commands.get(capability)
            result.require(
                isinstance(command, str) and bool(command.strip()) and command != "TBD",
                f"unresolved command capability: {capability}",
            )
            if isinstance(command, str) and command.startswith("not-applicable:"):
                result.require(
                    bool(command.partition(":")[2].strip()),
                    f"not-applicable command capability requires a reason: {capability}",
                )
            elif isinstance(command, str) and command not in {"", "TBD"}:
                try:
                    command_argv(command, capability)
                except ValueError as exc:
                    result.errors.append(str(exc))
            if capability in required_checks and isinstance(command, str):
                result.require(
                    not command.startswith("not-applicable:"),
                    f"required command capability is not applicable: {capability}",
                )
        dependency_lock = quality.get("dependency_lock")
        result.require(
            isinstance(dependency_lock, str)
            and dependency_lock not in {"", "TBD", "required-if-dependencies"},
            "instantiated projects must resolve a dependency lockfile or explicit exception",
        )
        if isinstance(dependency_lock, str) and dependency_lock.startswith("not-applicable:"):
            result.require(
                bool(dependency_lock.partition(":")[2].strip()),
                "not-applicable dependency lock requires a reason",
            )
        elif isinstance(dependency_lock, str) and dependency_lock not in {
            "",
            "TBD",
            "required-if-dependencies",
        }:
            try:
                lock_path = safe_path(root, dependency_lock)
            except ValueError as exc:
                result.errors.append(f"dependency lockfile: {exc}")
            else:
                result.require(
                    lock_path.is_file(),
                    f"configured dependency lockfile does not exist: {dependency_lock}",
                )
        coverage_policy = quality.get("coverage_policy")
        result.require(
            coverage_policy not in (None, "", "TBD"),
            "instantiated projects must resolve a coverage policy",
        )
        if isinstance(coverage_policy, str) and coverage_policy.startswith("not-applicable:"):
            result.require(
                bool(coverage_policy.partition(":")[2].strip()),
                "not-applicable coverage policy requires a reason",
            )
        for dotted_key, value in (
            ("engineering.command_contract.primary_check", commands.get("primary_check")),
            ("engineering.versioning.strategy", strategy),
        ):
            result.require(
                value not in (None, "", "TBD", []),
                f"unresolved essential field: {dotted_key}",
            )
        if strategy != "none":
            for dotted_key, value in (
                ("engineering.versioning.current", versioning.get("current")),
                ("engineering.versioning.public_contract", versioning.get("public_contract")),
                ("engineering.versioning.source", versioning.get("source")),
            ):
                result.require(
                    value not in (None, "", "TBD", []),
                    f"unresolved essential field: {dotted_key}",
                )
        try:
            version_status = product_version_status(root)
            for error in version_status.get("errors", []):
                result.errors.append(error)
        except (OSError, ValueError) as exc:
            result.errors.append(str(exc))
    return project


def validate_loop(root: Path, result: Result) -> None:
    loop = load_json(root / "harness/loops/engineering-loop.yaml")
    result.checked.append("engineering loop")
    states = loop.get("states", [])
    ids = {state.get("id") for state in states}
    result.require(loop.get("start_state") in ids, "loop start_state is not a defined state")
    result.require(
        set(loop.get("terminal_states", [])) == TERMINAL_STATES,
        "loop terminal_states must be reported, blocked, and abandoned",
    )
    for state in states:
        state_id = state.get("id", "<unknown>")
        result.require(state.get("owner") in ROLE_IDS, f"{state_id}: unknown owner")
        for key in ("requires", "produces", "gate", "next"):
            result.require(key in state, f"{state_id}: missing {key}")
        for next_state in state.get("next", []):
            result.require(
                next_state in ids or next_state in TERMINAL_STATES,
                f"{state_id}: transition references unknown state {next_state}",
            )


def validate_roles(root: Path, result: Result) -> None:
    for role in sorted(ROLE_FILES):
        path = root / "harness/roles" / f"{role}.md"
        result.require(path.is_file(), f"missing role contract: {path.relative_to(root)}")
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            for heading in ("## Objective", "## Authority", "## Prohibited", "## Required handoff"):
                result.require(heading in text, f"{role}: missing heading {heading}")
    result.checked.append("role contracts")


def validate_skills(root: Path, result: Result) -> None:
    skill_root = root / ".agents/skills"
    skills = sorted(path for path in skill_root.iterdir() if path.is_dir())
    result.require(bool(skills), "no repository-local skills found")
    for folder in skills:
        path = folder / "SKILL.md"
        result.require(path.is_file(), f"{folder.name}: missing SKILL.md")
        if not path.is_file():
            continue
        try:
            metadata = parse_skill_frontmatter(path)
        except ValueError as exc:
            result.errors.append(f"{folder.name}: {exc}")
            continue
        name = metadata.get("name", "")
        description = metadata.get("description", "")
        result.require(name == folder.name, f"{folder.name}: frontmatter name mismatch")
        result.require(bool(SKILL_NAME.fullmatch(name)), f"{folder.name}: invalid skill name")
        result.require(
            40 <= len(description) <= 1024,
            f"{folder.name}: description must be 40-1024 characters",
        )
        text = path.read_text(encoding="utf-8")
        result.require("TODO" not in text, f"{folder.name}: generated TODO remains")
        ui_path = folder / "agents/openai.yaml"
        result.require(ui_path.is_file(), f"{folder.name}: missing agents/openai.yaml")
        if ui_path.is_file():
            ui = ui_path.read_text(encoding="utf-8")
            result.require(
                f"${folder.name}" in ui,
                f"{folder.name}: default_prompt must mention ${folder.name}",
            )
    result.checked.append(f"{len(skills)} skills")


def validate_codex_agents(root: Path, result: Result) -> None:
    agent_files = sorted((root / ".codex/agents").glob("*.toml"))
    result.require(bool(agent_files), "no Codex role adapters found")
    for path in agent_files:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as exc:
            result.errors.append(f"{path.relative_to(root)}: invalid TOML: {exc}")
            continue
        for key in ("name", "description", "developer_instructions"):
            result.require(key in data, f"{path.name}: missing {key}")
        instructions = data.get("developer_instructions", "")
        result.require(
            "harness/roles/" in instructions,
            f"{path.name}: adapter must reference a canonical role contract",
        )
    result.checked.append(f"{len(agent_files)} Codex role adapters")


def validate_provider_adapters(root: Path, result: Result) -> None:
    adapter_files = sorted((root / "harness/adapters").glob("*.json"))
    result.require(bool(adapter_files), "no provider adapter manifests found")
    seen: set[str] = set()
    for path in adapter_files:
        adapter = load_json(path)
        adapter_id = adapter.get("id", "")
        result.require(adapter_id == path.stem, f"{path.name}: adapter id must match filename")
        result.require(bool(SKILL_NAME.fullmatch(adapter_id)), f"{path.name}: invalid adapter id")
        result.require(adapter_id not in seen, f"duplicate provider adapter id: {adapter_id}")
        seen.add(adapter_id)
        result.require(
            adapter.get("status") in {"supported", "experimental", "planned"},
            f"{path.name}: invalid status",
        )
        for key in (
            "display_name",
            "entrypoints",
            "mappings",
            "capabilities",
            "limitations",
            "security_notes",
        ):
            result.require(key in adapter, f"{path.name}: missing {key}")
        for entrypoint in adapter.get("entrypoints", []):
            result.require(
                (root / entrypoint).exists(),
                f"{path.name}: missing entrypoint {entrypoint}",
            )
        contracts: set[str] = set()
        for mapping in adapter.get("mappings", []):
            contract = mapping.get("contract", "")
            result.require(contract not in contracts, f"{path.name}: duplicate mapping {contract}")
            contracts.add(contract)
            result.require(
                mapping.get("mode") in {"native", "prompt-mediated", "native-extension"},
                f"{path.name}: invalid mapping mode for {contract}",
            )
            for key in ("canonical", "adapter"):
                relative = mapping.get(key, "")
                result.require(
                    isinstance(relative, str) and (root / relative).exists(),
                    f"{path.name}: missing {key} path {relative}",
                )
        for capability, value in adapter.get("capabilities", {}).items():
            result.require(
                isinstance(capability, str) and isinstance(value, str) and bool(value.strip()),
                f"{path.name}: invalid capability {capability}",
            )
    result.checked.append(f"{len(adapter_files)} provider adapters")


def validate_pi_adapter(root: Path, result: Result) -> None:
    settings = load_json(root / ".pi/settings.json")
    result.require(settings.get("enableSkillCommands") is True, "Pi skill commands must be enabled")
    result.require(
        settings.get("extensions") == ["extensions/context-readiness.ts"],
        "Pi settings must load only the reviewed context-readiness extension",
    )
    result.require(settings.get("prompts") == ["prompts"], "Pi prompt directory is not configured")
    result.require(
        settings.get("sessionDir") == "../.harness/pi/sessions",
        "Pi sessions must stay under ignored .harness state",
    )
    result.require(
        not settings.get("packages"), "Pi adapter must not auto-install third-party packages"
    )
    for personal_key in (
        "defaultProvider",
        "defaultModel",
        "defaultThinkingLevel",
        "enabledModels",
    ):
        result.require(
            personal_key not in settings, f"Pi project settings must not set {personal_key}"
        )
    gitignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    result.require(".harness/pi/" in gitignore, "Pi runtime session state must be ignored")

    extension = root / ".pi/extensions/context-readiness.ts"
    result.require(extension.is_file(), "Pi context-readiness extension is missing")
    if extension.is_file():
        source = extension.read_text(encoding="utf-8")
        for marker in (
            "@earendil-works/pi-coding-agent",
            'pi.registerCommand("harness-adapter"',
            'name: "harness_questionnaire"',
            "maxItems: 3",
            "if (!ctx.hasUI)",
        ):
            result.require(
                marker in source, f"Pi context-readiness extension missing marker: {marker}"
            )

    expected_prompts = {
        "harness-intake.md": "project-intake",
        "harness-loop.md": "execute-engineering-loop",
        "harness-report.md": "loop-report",
        "harness-research.md": "research-existing-solutions",
    }
    for filename, skill in expected_prompts.items():
        path = root / ".pi/prompts" / filename
        result.require(path.is_file(), f"missing Pi prompt template: {filename}")
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            result.require(skill in text, f"{filename}: must route to canonical skill {skill}")
            result.require(text.startswith("---\n"), f"{filename}: missing frontmatter")
    result.checked.append("Pi adapter")


def validate_planning(root: Path, result: Result) -> None:
    planning = load_json(root / ".github/planning.json")
    for collection, key in (("labels", "name"), ("milestones", "title"), ("fields", "name")):
        values = [item.get(key) for item in planning.get(collection, [])]
        result.require(len(values) == len(set(values)), f"duplicate {collection} in planning.json")
    field_types = {"SINGLE_SELECT", "TEXT", "NUMBER", "DATE", "ITERATION"}
    for item in planning.get("fields", []):
        result.require(
            item.get("data_type") in field_types,
            f"invalid field data_type for {item.get('name')}",
        )
    result.checked.append("GitHub desired state")


def validate_json_assets(root: Path, result: Result) -> None:
    for base in ("harness/schemas", "harness/profiles", "harness/fixtures"):
        for path in sorted((root / base).glob("*.json")):
            load_json(path)
    load_json(root / "harness/challenges/CHALLENGE_TEMPLATE.json")
    load_json(root / "harness/migrations/MIGRATION_TEMPLATE.json")
    load_json(root / "harness/preferences.example.json")
    load_json(root / "harness/evals/scenarios.json")
    version = load_json(root / "harness/version.json")
    project = load_json(root / "harness/project.yaml")
    ownership = load_json(root / "harness/ownership.json")
    lock = load_json(root / "harness.lock")
    for error in validate_ownership_policy(ownership):
        result.errors.append(error)
    for error in validate_lock(lock):
        result.errors.append(error)
    result.require(
        version.get("current") == project.get("harness_version"),
        "harness/version.json and project harness_version differ",
    )
    result.require(
        version.get("current") == lock.get("harness_version"),
        "harness/version.json and harness.lock version differ",
    )
    result.require(
        version.get("upstream_repository") == lock.get("upstream", {}).get("repository"),
        "harness/version.json and harness.lock upstream repository differ",
    )
    if project.get("template_mode", False):
        for relative, entry in lock.get("files", {}).items():
            result.require(
                sha256(root / relative) == entry.get("sha256"),
                f"template source differs from harness.lock: {relative}",
            )
    result.checked.append("JSON assets")


def validate_engineering_tooling(root: Path, result: Result) -> None:
    for path in sorted((root / "harness/profiles").glob("*.json")):
        profile = load_json(path)
        result.require(profile.get("id") == path.stem, f"{path.name}: profile id mismatch")
        result.require(
            bool(profile.get("recommended_checks")), f"{path.name}: no recommended checks"
        )
        result.require(
            bool(profile.get("tooling") or profile.get("tooling_capabilities")),
            f"{path.name}: no tooling contract",
        )
    dependabot = (root / ".github/dependabot.yml").read_text(encoding="utf-8")
    result.require(
        'package-ecosystem: "github-actions"' in dependabot,
        "Dependabot must update GitHub Actions",
    )
    for error in check_workflows(root):
        result.errors.append(error)
    result.checked.append("engineering and GitHub tooling")


def check(root: Path) -> Result:
    result = Result()
    for relative in REQUIRED_PATHS:
        result.require((root / relative).is_file(), f"missing required file: {relative}")
    try:
        validate_project(root, result)
        validate_loop(root, result)
        validate_roles(root, result)
        validate_skills(root, result)
        validate_codex_agents(root, result)
        validate_provider_adapters(root, result)
        validate_pi_adapter(root, result)
        validate_planning(root, result)
        validate_json_assets(root, result)
        validate_engineering_tooling(root, result)
    except (ValueError, OSError) as exc:
        result.errors.append(str(exc))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    result = check(root)
    payload = {
        "ok": result.ok,
        "root": str(root),
        "checked": result.checked,
        "warnings": result.warnings,
        "errors": result.errors,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"harness check: {'ok' if result.ok else 'failed'}")
        for item in result.checked:
            print(f"  checked: {item}")
        for warning in result.warnings:
            print(f"  warning: {warning}")
        for error in result.errors:
            print(f"  error: {error}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
