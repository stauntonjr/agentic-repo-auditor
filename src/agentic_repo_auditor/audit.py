"""Read-only repository evidence collection and checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml  # pyright: ignore[reportMissingModuleSource]
from yaml.nodes import (  # pyright: ignore[reportMissingModuleSource]
    MappingNode,
    Node,
    ScalarNode,
    SequenceNode,
)

from . import __version__
from .model import Evidence, Finding, Report, TargetState


class AuditError(RuntimeError):
    """Raised when the target or configuration cannot be audited safely."""


@dataclass(frozen=True)
class AuditConfig:
    """Validated v0.1 configuration."""

    disabled_checks: frozenset[str] = frozenset()


SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FULL_COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
DOCKER_DIGEST = re.compile(r"^docker://[^\s@]+@sha256:[0-9a-fA-F]{64}$")
MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
MAX_NESTED_REPOSITORIES = 128
MAX_YAML_NODES = 20_000
MAX_YAML_DEPTH = 100
FILTER_KEY = re.compile(r"^filter\.(.+)\.(?:clean|smudge|process|required)$", re.IGNORECASE)
INSTRUCTION_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
INSTRUCTION_SIGNAL_TERMS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("source", ("source", "sources", "authority", "authoritative", "precedence")),
    ("test", ("test", "tests", "testing")),
    ("safety", ("safe", "safely", "safety")),
    ("verification", ("verify", "verified", "verification", "validate", "validation")),
)


@dataclass(frozen=True)
class WorkflowInspection:
    """References and parse errors extracted from one workflow."""

    references: tuple[str, ...]
    errors: tuple[str, ...]


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


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_NO_LAZY_FETCH"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    return environment


def _base_git_command(root: Path) -> list[str]:
    return [
        "git",
        "--no-optional-locks",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-C",
        str(root),
    ]


def _run_git(
    root: Path,
    args: tuple[str, ...],
    *,
    filter_names: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    command = _base_git_command(root)
    for name in filter_names:
        command.extend(
            (
                "-c",
                f"filter.{name}.clean=",
                "-c",
                f"filter.{name}.smudge=",
                "-c",
                f"filter.{name}.process=",
                "-c",
                f"filter.{name}.required=false",
            )
        )
    command.extend(args)
    try:
        return subprocess.run(
            command,
            check=False,
            text=True,
            encoding="utf-8",
            errors="strict",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(),
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise AuditError(f"cannot inspect Git repository safely: {exc}") from exc


def _configured_filter_names(root: Path) -> tuple[str, ...]:
    """Find local filter drivers without invoking worktree conversion."""

    visited: set[Path] = set()
    names: set[str] = set()

    def is_repository_root(path: Path) -> bool:
        probe = _run_git(path, ("rev-parse", "--show-toplevel"))
        if probe.returncode:
            return False
        try:
            return Path(probe.stdout.rstrip("\r\n")).resolve() == path.resolve()
        except OSError as exc:
            raise AuditError(f"cannot resolve nested repository root {path}: {exc}") from exc

    def inspect(repository: Path) -> None:
        try:
            identity = repository.resolve(strict=True)
        except OSError as exc:
            raise AuditError(f"cannot inspect nested repository path {repository}: {exc}") from exc
        if identity in visited:
            return
        if len(visited) >= MAX_NESTED_REPOSITORIES:
            raise AuditError("repository contains too many nested Git repositories to audit safely")
        visited.add(identity)
        configured = _run_git(
            repository,
            (
                "config",
                "--null",
                "--name-only",
                "--get-regexp",
                r"^filter\..*\.(clean|smudge|process|required)$",
            ),
        )
        if configured.returncode not in {0, 1}:
            detail = configured.stderr.strip() or "cannot inspect repository filter configuration"
            raise AuditError(detail)
        for key in configured.stdout.split("\0"):
            if not key:
                continue
            match = FILTER_KEY.fullmatch(key)
            if match is None:
                raise AuditError(f"unexpected Git filter configuration key: {key!r}")
            names.add(match.group(1))
        index = _run_git(repository, ("ls-files", "--stage", "-z"))
        if index.returncode:
            detail = index.stderr.strip() or "cannot inspect repository index"
            raise AuditError(detail)
        for token in index.stdout.split("\0"):
            if not token:
                continue
            metadata, separator, relative = token.partition("\t")
            if not separator or not metadata.startswith("160000 "):
                continue
            child = repository / _repository_relative(relative)
            if _safe_kind(repository, relative) == "directory" and is_repository_root(child):
                inspect(child)

    inspect(root)
    if len(names) > MAX_NESTED_REPOSITORIES:
        raise AuditError("repository defines too many Git filter drivers to audit safely")
    return tuple(sorted(names))


def _git(root: Path, *args: str, check: bool = True) -> str:
    result = _run_git(root, tuple(args), filter_names=_configured_filter_names(root))
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise AuditError(detail)
    return result.stdout.rstrip("\r\n")


def _repository_relative(relative: str) -> Path:
    path = Path(relative)
    if not relative or path.is_absolute() or ".." in path.parts:
        raise AuditError(f"unsafe repository path: {relative!r}")
    return path


def _safe_kind(root: Path, relative: str) -> str:
    """Classify a repository path without following any symlink component."""

    cursor = root
    parts = _repository_relative(relative).parts
    metadata: os.stat_result | None = None
    for index, part in enumerate(parts):
        cursor /= part
        try:
            metadata = cursor.lstat()
        except FileNotFoundError:
            return "absent"
        except OSError as exc:
            raise AuditError(f"cannot inspect repository path {relative}: {exc}") from exc
        if stat.S_ISLNK(metadata.st_mode):
            return "symlink"
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            return "blocked"
    if metadata is None:  # Guarded by _repository_relative; keeps the invariant explicit.
        raise AuditError(f"unsafe repository path: {relative!r}")
    if stat.S_ISREG(metadata.st_mode):
        return "file"
    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    return "other"


def _safe_regular_file(root: Path, relative: str) -> Path | None:
    return root / _repository_relative(relative) if _safe_kind(root, relative) == "file" else None


def _safe_directory(root: Path, relative: str) -> Path | None:
    return (
        root / _repository_relative(relative) if _safe_kind(root, relative) == "directory" else None
    )


def _read_repository_text(root: Path, relative: str) -> str | None:
    path = _safe_regular_file(root, relative)
    if path is None:
        return None
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read repository file {relative}: {exc}") from exc
    if len(payload) > MAX_EVIDENCE_BYTES:
        raise AuditError(
            f"repository file exceeds {MAX_EVIDENCE_BYTES} byte evidence limit: {relative}"
        )
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise AuditError(f"repository file is not valid UTF-8: {relative}") from exc


def _nested_repository_metadata(root: Path) -> dict[str, Any] | None:
    """Capture nested HEAD/index state recursively without reading Git object contents."""

    def is_repository_root(path: Path) -> bool:
        probe = _run_git(path, ("rev-parse", "--show-toplevel"))
        if probe.returncode:
            return False
        try:
            return Path(probe.stdout.rstrip("\r\n")).resolve() == path.resolve()
        except OSError as exc:
            raise AuditError(f"cannot resolve nested repository root {path}: {exc}") from exc

    if not is_repository_root(root):
        return None
    visited: set[Path] = set()

    def inspect(repository: Path) -> dict[str, Any]:
        identity = repository.resolve()
        if identity in visited:
            return {"cycle": identity.name}
        if len(visited) >= MAX_NESTED_REPOSITORIES:
            raise AuditError("repository contains too many nested Git repositories to fingerprint")
        visited.add(identity)
        head = _git(repository, "rev-parse", "HEAD", check=False) or "UNBORN"
        index = _git(repository, "ls-files", "--stage", "-z")
        children: list[dict[str, Any]] = []
        for token in index.split("\0"):
            if not token:
                continue
            metadata, separator, relative = token.partition("\t")
            if not separator or not metadata.startswith("160000 "):
                continue
            if _safe_kind(repository, relative) != "directory":
                continue
            child_path = repository / _repository_relative(relative)
            if is_repository_root(child_path):
                children.append({"path": relative, "repository": inspect(child_path)})
        return {
            "head": head,
            "index": hashlib.sha256(index.encode("utf-8")).hexdigest(),
            "index_flags": _hidden_index_paths(repository),
            "gitlinks": sorted(children, key=lambda item: item["path"]),
        }

    return inspect(root)


def _fingerprint_worktree_path(root: Path, relative: str) -> str:
    """Hash a worktree entry without following links or reading Git metadata."""

    target = root / _repository_relative(relative)
    digest = hashlib.sha256()
    try:
        target_metadata = target.lstat()
    except FileNotFoundError:
        target_metadata = None
    except OSError as exc:
        raise AuditError(f"cannot fingerprint repository path {relative}: {exc}") from exc
    if target_metadata is not None and stat.S_ISDIR(target_metadata.st_mode):
        nested = _nested_repository_metadata(target)
        if nested is not None:
            payload = json.dumps(nested, sort_keys=True, separators=(",", ":")).encode("utf-8")
            digest.update(b"nested-git\0" + payload + b"\0")

    def visit(path: Path, display: str) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            digest.update(f"absent\0{display}\0".encode("utf-8", "surrogateescape"))
            return
        except OSError as exc:
            raise AuditError(f"cannot fingerprint repository path {relative}: {exc}") from exc
        mode = metadata.st_mode
        encoded = display.encode("utf-8", "surrogateescape")
        if stat.S_ISLNK(mode):
            target_text = os.readlink(path).encode("utf-8", "surrogateescape")
            digest.update(b"symlink\0" + encoded + b"\0" + target_text + b"\0")
        elif stat.S_ISREG(mode):
            digest.update(f"file\0{mode & 0o7777:o}\0".encode("ascii") + encoded + b"\0")
            try:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
            except OSError as exc:
                raise AuditError(f"cannot fingerprint repository file {relative}: {exc}") from exc
            digest.update(b"\0")
        elif stat.S_ISDIR(mode):
            digest.update(b"directory\0" + encoded + b"\0")
            try:
                children = sorted(path.iterdir(), key=lambda item: item.name)
            except OSError as exc:
                raise AuditError(f"cannot inspect repository directory {relative}: {exc}") from exc
            for child in children:
                if child.name == ".git":
                    continue
                child_display = f"{display}/{child.name}" if display else child.name
                visit(child, child_display)
        else:
            digest.update(f"other\0{mode}\0{metadata.st_size}\0".encode("ascii") + encoded + b"\0")

    visit(target, relative)
    return digest.hexdigest()


def _hidden_index_paths(root: Path) -> dict[str, tuple[str, ...]]:
    flags: dict[str, set[str]] = {}
    for option, label, predicate in (
        ("-v", "assume-unchanged", lambda tag: tag.islower()),
        ("-t", "skip-worktree", lambda tag: tag == "S"),
    ):
        output = _git(root, "ls-files", option, "-z")
        for token in output.split("\0"):
            if not token:
                continue
            tag, separator, path = token.partition(" ")
            if not separator or len(tag) != 1:
                raise AuditError(f"unexpected Git index flag entry: {token!r}")
            if predicate(tag):
                flags.setdefault(path, set()).add(label)
    return {path: tuple(sorted(values)) for path, values in flags.items()}


def _status_paths(status_text: str) -> list[tuple[str, str]]:
    tokens = status_text.split("\0")
    entries: list[tuple[str, str]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if len(token) < 4 or token[2] != " ":
            raise AuditError(f"unexpected Git porcelain entry: {token!r}")
        status_code = token[:2]
        entries.append((token[3:].rstrip("/"), status_code))
        if "R" in status_code or "C" in status_code:
            if index >= len(tokens) or not tokens[index]:
                raise AuditError("incomplete Git rename/copy status entry")
            entries.append((tokens[index].rstrip("/"), f"{status_code}:source"))
            index += 1
    return entries


def _state_entries(root: Path, status_text: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    flags_by_path = _hidden_index_paths(root)
    for relative, status_code in _status_paths(status_text):
        index_state = _git(root, "ls-files", "--stage", "-z", "--", relative, check=False)
        entries.append(
            {
                "path": relative,
                "status": status_code,
                "worktree": _fingerprint_worktree_path(root, relative),
                "index": hashlib.sha256(index_state.encode("utf-8")).hexdigest(),
                "index_flags": list(flags_by_path.get(relative, ())),
            }
        )
        seen.add(relative)
    for relative, flags in flags_by_path.items():
        if relative in seen:
            continue
        index_state = _git(root, "ls-files", "--stage", "-z", "--", relative)
        entries.append(
            {
                "path": relative,
                "status": "index-hidden",
                "worktree": _fingerprint_worktree_path(root, relative),
                "index": hashlib.sha256(index_state.encode("utf-8")).hexdigest(),
                "index_flags": list(flags),
            }
        )
        seen.add(relative)
    full_index = _git(root, "ls-files", "--stage", "-z")
    for token in full_index.split("\0"):
        if not token:
            continue
        metadata, separator, relative = token.partition("\t")
        if not separator or not metadata.startswith("160000 ") or relative in seen:
            continue
        entries.append(
            {
                "path": relative,
                "status": "gitlink-monitored",
                "worktree": _fingerprint_worktree_path(root, relative),
                "index": hashlib.sha256(token.encode("utf-8")).hexdigest(),
                "index_flags": list(flags_by_path.get(relative, ())),
            }
        )
    return sorted(entries, key=lambda item: (item["path"], item["status"]))


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
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    )
    status_entries = _status_paths(status)
    payload = {
        "name": root.name,
        "revision": revision,
        "branch": branch,
        "entries": _state_entries(root, status),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    identity = hashlib.sha256(serialized).hexdigest()
    return TargetState(
        root.name, revision, branch, bool(status_entries), f"sha256:{identity}"
    ), status


def _presence_check(
    root: Path,
    finding_id: str,
    category: str,
    title: str,
    paths: tuple[str, ...],
    description: str,
    remediation: str,
) -> Finding:
    present = tuple(path for path in paths if _safe_regular_file(root, path) is not None)
    rejected = tuple(
        f"{path}:{_safe_kind(root, path)}"
        for path in paths
        if _safe_kind(root, path) not in {"absent", "file"}
    )
    status = "pass" if present else "warn"
    severity = "info" if present else "medium"
    value = ", ".join(present) if present else "none found"
    evidence = [Evidence("path-presence", ".", value)]
    evidence.extend(Evidence("rejected-path", path.split(":", 1)[0], path) for path in rejected)
    return _finding(
        finding_id,
        category,
        status,
        severity,
        title,
        description,
        evidence,
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
    present = tuple(path for path in expected if _safe_regular_file(root, path) is not None)
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
    entries = tuple(_status_paths(status_text))
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
    workflow_root = _safe_directory(root, ".github/workflows")
    if workflow_root is None:
        return ()
    try:
        paths = tuple(
            sorted(
                path
                for path in workflow_root.iterdir()
                if path.suffix in {".yml", ".yaml"}
                and _safe_kind(root, path.relative_to(root).as_posix()) == "file"
            )
        )
    except OSError as exc:
        raise AuditError(f"cannot list repository workflows: {exc}") from exc
    return paths


def _validate_yaml_graph(document: Node, *, context: str) -> None:
    visited: set[int] = set()

    def visit(node: Node, depth: int = 0) -> None:
        if depth > MAX_YAML_DEPTH:
            raise AuditError(f"{context} exceeds the safe nesting limit")
        identity = id(node)
        if identity in visited:
            return
        visited.add(identity)
        if len(visited) > MAX_YAML_NODES:
            raise AuditError(f"{context} exceeds the safe node limit")
        if isinstance(node, MappingNode):
            for key, value in node.value:
                visit(key, depth + 1)
                visit(value, depth + 1)
        elif isinstance(node, SequenceNode):
            for value in node.value:
                visit(value, depth + 1)

    visit(document)


def _inspect_workflow(text: str) -> WorkflowInspection:
    references: list[str] = []
    errors: list[str] = []
    try:
        document = yaml.compose(text, Loader=yaml.SafeLoader)
    except (yaml.YAMLError, RecursionError) as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f"line {mark.line + 1}: " if mark is not None else ""
        return WorkflowInspection((), (f"{location}invalid YAML: {exc}",))
    if document is None:
        return WorkflowInspection((), ())

    def effective_mapping(
        node: MappingNode,
        depth: int = 0,
        active: frozenset[int] = frozenset(),
    ) -> dict[str, Node]:
        if depth > MAX_YAML_DEPTH or id(node) in active:
            return {}
        next_active = active | {id(node)}
        merged_nodes: list[MappingNode] = []
        direct: list[tuple[str, Node]] = []
        for key, value in node.value:
            if not isinstance(key, ScalarNode):
                continue
            if key.value == "<<":
                if isinstance(value, MappingNode):
                    merged_nodes.append(value)
                elif isinstance(value, SequenceNode):
                    merged_nodes.extend(
                        item for item in reversed(value.value) if isinstance(item, MappingNode)
                    )
                continue
            direct.append((key.value, value))
        result: dict[str, Node] = {}
        for merged in merged_nodes:
            result.update(effective_mapping(merged, depth + 1, next_active))
        for key, value in direct:
            result[key] = value
        return result

    def add_reference(value: Node, context: str) -> None:
        if isinstance(value, ScalarNode) and value.tag.endswith(":str"):
            references.append(value.value)
        else:
            errors.append(
                f"line {value.start_mark.line + 1}: {context} uses value must be a string"
            )

    _validate_yaml_graph(document, context="workflow YAML")
    if not isinstance(document, MappingNode):
        return WorkflowInspection((), ("workflow document must be a mapping",))
    jobs = effective_mapping(document).get("jobs")
    if jobs is None:
        return WorkflowInspection((), ())
    if not isinstance(jobs, MappingNode):
        return WorkflowInspection((), ("workflow jobs value must be a mapping",))
    for job_id, job in effective_mapping(jobs).items():
        if not isinstance(job, MappingNode):
            errors.append(f"line {job.start_mark.line + 1}: job {job_id} must be a mapping")
            continue
        fields = effective_mapping(job)
        if "uses" in fields:
            add_reference(fields["uses"], f"job {job_id}")
        steps = fields.get("steps")
        if steps is None:
            continue
        if not isinstance(steps, SequenceNode):
            errors.append(
                f"line {steps.start_mark.line + 1}: job {job_id} steps must be a sequence"
            )
            continue
        for step_index, step in enumerate(steps.value):
            if not isinstance(step, MappingNode):
                continue
            step_uses = effective_mapping(step).get("uses")
            if step_uses is not None:
                add_reference(step_uses, f"job {job_id} step {step_index}")

    return WorkflowInspection(tuple(references), tuple(errors))


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
    parse_errors: list[tuple[str, str]] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        content = _read_repository_text(root, relative)
        if content is None:
            continue
        inspection = _inspect_workflow(content)
        parse_errors.extend((relative, error) for error in inspection.errors)
        for reference in inspection.references:
            references.append((relative, reference))
            if reference.startswith("./"):
                continue
            if reference.startswith("docker://"):
                if DOCKER_DIGEST.fullmatch(reference) is None:
                    mutable.append((relative, reference))
                continue
            action, separator, revision = reference.rpartition("@")
            if not separator or not action or FULL_COMMIT_SHA.fullmatch(revision) is None:
                mutable.append((relative, reference))
    if not paths:
        status, severity = "not-applicable", "info"
    elif mutable or parse_errors:
        status, severity = "fail", "high"
    else:
        status, severity = "pass", "info"
    evidence = [Evidence("action-summary", ".github/workflows", f"references={len(references)}")]
    evidence.extend(Evidence("mutable-action", path, reference) for path, reference in mutable)
    evidence.extend(Evidence("workflow-parse-error", path, error) for path, error in parse_errors)
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
    matched: list[str] = []
    parse_errors: list[tuple[str, str]] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        content = _read_repository_text(root, relative)
        if content is None:
            continue
        inspection = _inspect_workflow(content)
        parse_errors.extend((relative, error) for error in inspection.errors)
        if any(
            reference.partition("@")[0].startswith("github/codeql-action/")
            for reference in inspection.references
        ):
            matched.append(relative)
    evidence = [Evidence("workflow-set", ".github/workflows", ", ".join(matched) or "none found")]
    evidence.extend(Evidence("workflow-parse-error", path, error) for path, error in parse_errors)
    return _finding(
        "security.code-scanning",
        "security",
        "pass" if matched and not parse_errors else "warn",
        "info" if matched and not parse_errors else "medium",
        "Code scanning",
        "The repository declares a CodeQL workflow as a visible code-scanning signal.",
        evidence,
        "Configure code scanning appropriate to the repository languages and threat model.",
    )


def _testing_primary_check(root: Path, _: str) -> Finding:
    command = ""
    content = _read_repository_text(root, "harness/project.yaml")
    if content is not None:
        try:
            payload = json.loads(content)
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
    tests: list[str] = []
    tests_root = _safe_directory(root, "tests")
    if tests_root is not None:
        try:
            for directory, names, filenames in os.walk(tests_root, followlinks=False):
                names[:] = sorted(name for name in names if not Path(directory, name).is_symlink())
                for filename in sorted(filenames):
                    path = Path(directory, filename)
                    relative = path.relative_to(root).as_posix()
                    if _safe_kind(root, relative) != "file":
                        continue
                    if any(path.match(pattern) for pattern in patterns):
                        tests.append(relative)
        except OSError as exc:
            raise AuditError(f"cannot inspect repository tests: {exc}") from exc
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
    content = (_read_repository_text(root, "AGENTS.md") or "").lower()
    words = frozenset(INSTRUCTION_WORD.findall(content))
    matches = tuple(
        (signal, next((term for term in terms if term in words), None))
        for signal, terms in INSTRUCTION_SIGNAL_TERMS
    )
    present = tuple(signal for signal, match in matches if match is not None)
    missing = tuple(signal for signal, match in matches if match is None)
    matched_terms = tuple(f"{signal}:{match}" for signal, match in matches if match is not None)
    return _finding(
        "agent-readiness.instructions",
        "agent-readiness",
        "pass" if not missing else "warn",
        "info" if not missing else "medium",
        "Agent instruction coverage",
        "Repository instructions expose core evidence, verification, and safety signals.",
        [
            Evidence(
                "signal-set",
                "AGENTS.md",
                f"present={list(present)}; missing={list(missing)}; matches={list(matched_terms)}",
            )
        ],
        "Document source precedence, tests, verification boundaries, and safety constraints.",
    )


def _parse_skill_frontmatter(root: Path, relative: str) -> tuple[str, str] | None:
    content = _read_repository_text(root, relative)
    if content is None:
        return None
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        closing = lines.index("---", 1)
    except ValueError:
        return None
    header = "\n".join(lines[1:closing])
    try:
        document = yaml.compose(header, Loader=yaml.SafeLoader)
        if document is None:
            return None
        _validate_yaml_graph(document, context="Skill frontmatter YAML")
        values = yaml.safe_load(header)
    except (yaml.YAMLError, RecursionError):
        return None
    if not isinstance(values, dict):
        return None
    name = values.get("name")
    description = values.get("description")
    if (
        not isinstance(name, str)
        or not isinstance(description, str)
        or not SKILL_NAME.fullmatch(name)
        or len(name) > 64
        or not description.strip()
        or len(description) > 1024
        or Path(relative).parent.name != name
    ):
        return None
    return name, description


def _agent_skills(root: Path, _: str) -> Finding:
    paths: list[str] = []
    skills_root = _safe_directory(root, ".agents/skills")
    if skills_root is not None:
        try:
            for skill_directory in sorted(skills_root.iterdir(), key=lambda item: item.name):
                relative_directory = skill_directory.relative_to(root).as_posix()
                if _safe_kind(root, relative_directory) != "directory":
                    continue
                relative = f"{relative_directory}/SKILL.md"
                if _safe_regular_file(root, relative) is not None:
                    paths.append(relative)
        except OSError as exc:
            raise AuditError(f"cannot inspect repository skills: {exc}") from exc
    invalid = tuple(path for path in paths if _parse_skill_frontmatter(root, path) is None)
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
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
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
    if len(disabled) != len(set(disabled)):
        raise AuditError("disabled_checks must contain unique check IDs")
    unknown_checks = sorted(set(disabled) - CHECK_IDS)
    if unknown_checks:
        raise AuditError(f"unknown disabled checks: {', '.join(unknown_checks)}")
    return AuditConfig(frozenset(disabled))


def audit_repository(target: Path, config: AuditConfig | None = None) -> Report:
    """Audit one repository root without intentionally writing to it."""

    try:
        expanded = target.expanduser()
        try:
            root = expanded.resolve(strict=True)
        except FileNotFoundError as exc:
            raise AuditError(f"target is not a directory: {expanded.resolve()}") from exc
        if not root.is_dir():
            raise AuditError(f"target is not a directory: {root}")
        active_config = config or AuditConfig()
        target_state, status_text = _target_state(root)
        findings = tuple(
            check(root, status_text)
            for finding_id, check in CHECKS
            if finding_id not in active_config.disabled_checks
        )
    except AuditError:
        raise
    except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
        raise AuditError(f"cannot audit repository safely: {exc}") from exc
    return Report(
        tool_name="agentic-repo-auditor",
        tool_version=__version__,
        target=target_state,
        findings=findings,
        disabled_checks=tuple(active_config.disabled_checks),
    )
