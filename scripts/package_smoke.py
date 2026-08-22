#!/usr/bin/env python3
"""Build, clean-install, and execute the product CLI without target writes."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import venv


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_RUNTIME_DEPENDENCIES = ["PyYAML==6.0.2"]


def expected_version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"].get("dependencies") != EXPECTED_RUNTIME_DEPENDENCIES:
        raise RuntimeError(
            "pyproject.toml runtime dependencies differ from the reviewed pinned set"
        )
    version = project["project"]["version"]
    if not isinstance(version, str) or not version:
        raise RuntimeError("pyproject.toml project.version must be a non-empty string")
    return version


def verify_source_versions(version: str) -> None:
    harness = json.loads((ROOT / "harness/project.yaml").read_text(encoding="utf-8"))
    contract = harness["engineering"]["versioning"]
    if contract["source"] != "pyproject.toml:project.version":
        raise RuntimeError("product version source must be pyproject.toml:project.version")
    if contract["current"] != version:
        raise RuntimeError("harness product version differs from pyproject.toml")
    module: dict[str, str] = {}
    exec((ROOT / "src/agentic_repo_auditor/__init__.py").read_text(encoding="utf-8"), module)
    if module.get("__version__") != version:
        raise RuntimeError("module version differs from pyproject.toml")
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    locked = [
        package.get("version")
        for package in lock.get("package", [])
        if package.get("name") == "agentic-repo-auditor"
    ]
    if locked != [version]:
        raise RuntimeError(f"uv.lock product version differs from pyproject.toml: {locked}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"early `{version}` implementation" not in readme:
        raise RuntimeError("README current version differs from pyproject.toml")
    if f"## [{version}]" not in changelog:
        raise RuntimeError("CHANGELOG current version differs from pyproject.toml")


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
    version_expected = expected_version()
    verify_source_versions(version_expected)
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
            ["uv", "pip", "install", "--python", str(python), str(wheels[0])],
            check=True,
            stdout=subprocess.PIPE,
        )
        version = subprocess.run(
            [str(cli), "--version"], check=True, text=True, stdout=subprocess.PIPE
        ).stdout.strip()
        distribution_version = subprocess.run(
            [
                str(python),
                "-c",
                "from importlib.metadata import version; print(version('agentic-repo-auditor'))",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout.strip()
        yaml_version = subprocess.run(
            [
                str(python),
                "-c",
                "from importlib.metadata import version; print(version('PyYAML'))",
            ],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
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
    if distribution_version != version_expected:
        raise RuntimeError(
            f"installed distribution version {distribution_version} differs from {version_expected}"
        )
    if yaml_version != "6.0.2":
        raise RuntimeError(
            f"installed PyYAML version differs from the reviewed pin: {yaml_version}"
        )
    if version != f"agentic-repo-auditor {version_expected}":
        raise RuntimeError(f"unexpected CLI version: {version}")
    if report["tool"]["version"] != version_expected:
        raise RuntimeError("installed CLI report version does not match package version")
    print(f"Agentic Repo Auditor package smoke: ok ({version_expected})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
