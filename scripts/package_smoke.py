#!/usr/bin/env python3
"""Build, clean-install, and execute the product CLI without target writes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.1.0"


def git_status() -> str:
    return subprocess.run(
        ["git", "--no-optional-locks", "status", "--porcelain=v1", "--untracked-files=normal"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    ).stdout


def main() -> int:
    before = git_status()
    with tempfile.TemporaryDirectory() as directory:
        boundary = Path(directory)
        dist = boundary / "dist"
        subprocess.run(["uv", "build", "--out-dir", str(dist)], cwd=ROOT, check=True)
        wheels = sorted(dist.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        environment = boundary / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(environment)
        executable_root = environment / ("Scripts" if sys.platform == "win32" else "bin")
        python = executable_root / ("python.exe" if sys.platform == "win32" else "python")
        cli = executable_root / (
            "agentic-repo-auditor.exe" if sys.platform == "win32" else "agentic-repo-auditor"
        )
        subprocess.run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])],
            check=True,
            stdout=subprocess.PIPE,
        )
        version = subprocess.run(
            [str(cli), "--version"], check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
        report_text = subprocess.run(
            [str(cli), "audit", str(ROOT), "--format", "json", "--fail-on", "none"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout
        report = json.loads(report_text)
    after = git_status()
    if before != after:
        raise RuntimeError("package smoke changed the audited repository status")
    if version != f"agentic-repo-auditor {EXPECTED_VERSION}":
        raise RuntimeError(f"unexpected CLI version: {version}")
    if report["tool"]["version"] != EXPECTED_VERSION:
        raise RuntimeError("installed CLI report version does not match package version")
    print(f"Agentic Repo Auditor package smoke: ok ({EXPECTED_VERSION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
