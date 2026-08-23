#!/usr/bin/env python3
"""Reconcile downstream lock ownership with a reversible receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.common import load_json, utc_now, write_json  # noqa: E402
from tools.harness_upgrade import (  # noqa: E402
    ownership_for,
    sha256,
    validate_lock,
    validate_ownership_policy,
)


def reconcile(root: Path, *, receipt_root: Path | None = None) -> Path:
    root = root.resolve()
    lock_path = root / "harness.lock"
    lock = load_json(lock_path)
    policy = load_json(root / "harness/ownership.json")
    errors = validate_lock(lock) + validate_ownership_policy(policy)
    if errors:
        raise ValueError("; ".join(errors))

    changes: list[dict[str, str]] = []
    for path, entry in sorted(lock["files"].items()):
        expected = ownership_for(path, policy)
        if entry["ownership"] != expected:
            changes.append(
                {
                    "path": path,
                    "before_ownership": entry["ownership"],
                    "after_ownership": expected,
                }
            )
    if not changes:
        raise ValueError("lock ownership already matches downstream policy")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt_dir = receipt_root or (
        root / ".harness/upgrades" / f"{lock['harness_version']}-ownership-reconciliation" / stamp
    )
    receipt_dir.mkdir(parents=True, exist_ok=False)
    backup = receipt_dir / "backup/harness.lock"
    backup.parent.mkdir(parents=True)
    shutil.copy2(lock_path, backup)
    before = sha256(lock_path)
    try:
        for change in changes:
            lock["files"][change["path"]]["ownership"] = change["after_ownership"]
        write_json(lock_path, lock)
        receipt = {
            "schema_version": "1.0",
            "plan_id": f"{lock['harness_version']}-downstream-ownership-reconciliation",
            "from_version": lock["harness_version"],
            "to_version": lock["harness_version"],
            "applied_at": utc_now(),
            "rolled_back_at": None,
            "pre_state": [
                {
                    "path": "harness.lock",
                    "existed": True,
                    "before_sha256": before,
                    "backup": "harness.lock",
                    "after_sha256": sha256(lock_path),
                }
            ],
            "decisions": changes,
            "rollback_order": [
                "rollback this ownership receipt",
                "then rollback the associated harness release receipt",
            ],
        }
        receipt_path = receipt_dir / "receipt.json"
        write_json(receipt_path, receipt)
        return receipt_path
    except Exception:
        shutil.copy2(backup, lock_path)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile a derived lock's ownership metadata and write a rollback receipt."
    )
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()
    try:
        print(reconcile(args.root))
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
