#!/usr/bin/env python3
"""Validate and explicitly replay executable historical failure cases."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from .common import load_json, repository_root, run, utc_now, write_json
except ImportError:  # Direct script execution.
    from common import load_json, repository_root, run, utc_now, write_json


CHALLENGE_ID = re.compile(r"^C[0-9]{3,}$")


def challenge_paths(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "harness/challenges").glob("C*.json")
        if path.name != "CHALLENGE_TEMPLATE.json"
    )


def validate_challenge(data: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    required = (
        "id",
        "title",
        "escaped_defect",
        "affected_surfaces",
        "oracle",
        "known_bad",
        "expected_failure",
    )
    for key in required:
        if key not in data:
            errors.append(f"{path.name}: missing {key}")
    identifier = data.get("id", "")
    if not CHALLENGE_ID.fullmatch(identifier):
        errors.append(f"{path.name}: invalid challenge id {identifier}")
    if path.stem != identifier:
        errors.append(f"{path.name}: filename must match challenge id")
    for command_key in ("oracle", "known_bad"):
        argv = data.get(command_key, {}).get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(item, str) for item in argv)
        ):
            errors.append(f"{path.name}: {command_key}.argv must be a non-empty string list")
    return errors


def validate_all(root: Path) -> tuple[list[tuple[Path, dict[str, Any]]], list[str]]:
    challenges: list[tuple[Path, dict[str, Any]]] = []
    errors: list[str] = []
    for path in challenge_paths(root):
        try:
            data = load_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        errors.extend(validate_challenge(data, path))
        challenges.append((path, data))
    return challenges, errors


def replay(root: Path, challenge: dict[str, Any]) -> dict[str, Any]:
    oracle = run(challenge["oracle"]["argv"], cwd=root, check=False)
    known_bad = run(challenge["known_bad"]["argv"], cwd=root, check=False)
    expected = challenge["expected_failure"]
    signature = expected.get("signature", "")
    oracle_ok = oracle.returncode == challenge["oracle"].get("success_exit_code", 0)
    known_bad_output = known_bad.stdout + known_bad.stderr
    known_bad_ok = known_bad.returncode == expected.get("exit_code", 1) and (
        not signature or signature in known_bad_output
    )
    return {
        "id": challenge["id"],
        "oracle": {
            "ok": oracle_ok,
            "exit_code": oracle.returncode,
            "stdout": oracle.stdout[-4000:],
            "stderr": oracle.stderr[-4000:],
        },
        "known_bad": {
            "ok": known_bad_ok,
            "exit_code": known_bad.returncode,
            "stdout": known_bad.stdout[-4000:],
            "stderr": known_bad.stderr[-4000:],
        },
        "ok": oracle_ok and known_bad_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--run", action="store_true", help="Execute validated challenge commands")
    args = parser.parse_args()
    root = args.root.resolve() if args.root else repository_root(Path(__file__).parent)
    challenges, errors = validate_all(root)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    if not args.run:
        print(
            json.dumps({"ok": True, "validated": [data["id"] for _, data in challenges]}, indent=2)
        )
        return 0
    results = [replay(root, data) for _, data in challenges]
    payload = {
        "recorded_at": utc_now(),
        "results": results,
        "ok": all(item["ok"] for item in results),
    }
    output = root / ".harness/challenge-results" / f"{payload['recorded_at'].replace(':', '')}.json"
    write_json(output, payload)
    print(
        json.dumps({"ok": payload["ok"], "artifact": str(output), "count": len(results)}, indent=2)
    )
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
