#!/usr/bin/env python3
"""Validate Pi project resources without invoking a model or installing packages."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root
except ImportError:  # Direct script execution.
    from common import load_json, repository_root


REQUIRED_COMMANDS = {
    "harness-adapter": "extension",
    "harness-intake": "prompt",
    "harness-loop": "prompt",
    "harness-report": "prompt",
    "harness-research": "prompt",
    "skill:execute-engineering-loop": "skill",
    "skill:loop-report": "skill",
    "skill:project-intake": "skill",
    "skill:research-existing-solutions": "skill",
}


def command_errors(payload: dict[str, Any]) -> list[str]:
    commands = payload.get("data", {}).get("commands", [])
    observed = {item.get("name"): item.get("source") for item in commands}
    errors: list[str] = []
    for name, source in sorted(REQUIRED_COMMANDS.items()):
        if observed.get(name) != source:
            errors.append(f"missing {source} command: {name}")
    return errors


def run_check(root: Path, executable: str) -> dict[str, Any]:
    manifest = load_json(root / "harness/adapters/pi.json")
    tested_versions = manifest.get("runtime", {}).get("tested_versions", [])
    version_result = subprocess.run(
        [executable, "--version"],
        cwd=root,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10,
    )
    version = version_result.stdout.strip()
    errors: list[str] = []
    if version_result.returncode != 0:
        errors.append(version_result.stderr.strip() or "pi --version failed")
    elif version not in tested_versions:
        errors.append(f"Pi {version} is not in tested_versions: {tested_versions}")

    response: dict[str, Any] | None = None
    extension_errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="pi-adapter-check-") as config_dir:
        environment = os.environ.copy()
        environment["PI_CODING_AGENT_DIR"] = config_dir
        environment["PI_OFFLINE"] = "1"
        rpc = subprocess.run(
            [executable, "--approve", "--mode", "rpc", "--no-session"],
            cwd=root,
            check=False,
            text=True,
            input=json.dumps({"type": "get_commands"}) + "\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            timeout=15,
        )
    if rpc.returncode != 0:
        errors.append(rpc.stderr.strip() or f"Pi RPC exited {rpc.returncode}")
    for line in rpc.stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if item.get("type") == "extension_error":
            extension_errors.append(item.get("error", json.dumps(item, sort_keys=True)))
        if item.get("type") == "response" and item.get("command") == "get_commands":
            response = item
    errors.extend(f"extension error: {message}" for message in extension_errors)
    if response is None:
        errors.append("Pi RPC did not return get_commands")
        commands: list[dict[str, Any]] = []
    else:
        if not response.get("success"):
            errors.append(f"get_commands failed: {response.get('error', 'unknown error')}")
        errors.extend(command_errors(response))
        commands = response.get("data", {}).get("commands", [])

    return {
        "ok": not errors,
        "pi": executable,
        "version": version,
        "tested_versions": tested_versions,
        "offline": True,
        "model_invoked": False,
        "required_commands": sorted(REQUIRED_COMMANDS),
        "observed_project_commands": sorted(
            item.get("name", "")
            for item in commands
            if item.get("sourceInfo", {}).get("scope") == "project"
        ),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--pi", dest="executable")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    executable = args.executable or shutil.which("pi")
    if not executable:
        print(json.dumps({"ok": False, "errors": ["pi executable not found"]}, indent=2))
        return 1
    try:
        result = run_check(root, executable)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
