#!/usr/bin/env python3
"""Strictly validate a derived repository's pinned upstream harness base."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.common import load_json  # noqa: E402
from tools.harness_upgrade import (  # noqa: E402
    inspect_lock_state,
    ownership_for,
    validate_lock,
    validate_ownership_policy,
)


def check(root: Path) -> dict[str, object]:
    lock = load_json(root / "harness.lock")
    project = load_json(root / "harness/project.yaml")
    policy = load_json(root / "harness/ownership.json")
    state = inspect_lock_state(root, lock)
    errors = validate_lock(lock) + validate_ownership_policy(policy)
    if project.get("harness_version") != lock.get("harness_version"):
        errors.append("project and lock harness versions differ")

    for path, entry in lock.get("files", {}).items():
        expected = ownership_for(path, policy)
        if entry.get("ownership") != expected:
            errors.append(f"lock ownership differs from project policy: {path}")

    protected = {
        path
        for path, entry in lock.get("files", {}).items()
        if entry.get("ownership") == "upstream-owned"
    }
    for disposition in ("modified", "missing"):
        for path in state[disposition]:
            if path in protected:
                errors.append(f"upstream-owned harness file is {disposition}: {path}")

    return {
        "ok": not errors,
        "harness_version": lock.get("harness_version"),
        "upstream": lock.get("upstream"),
        "upstream_owned": {
            "modified": sorted(protected.intersection(state["modified"])),
            "missing": sorted(protected.intersection(state["missing"])),
        },
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail when a pinned upstream-owned harness file has drifted."
    )
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()
    payload = check(args.root.resolve())
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
