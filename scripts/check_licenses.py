#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
import tomllib
from importlib import metadata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

APPROVED_LICENSE_TOKENS = {
    "0BSD",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0-1.0",
    "ISC",
    "MIT",
    "MPL-2.0",
    "PSF-2.0",
    "Python-2.0",
    "Zlib",
}

LICENSE_ALIASES = {
    "Apache License 2.0": "Apache-2.0",
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "MIT License": "MIT",
    "Mozilla Public License 2.0 (MPL 2.0)": "MPL-2.0",
    "Python Software Foundation License": "PSF-2.0",
}


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement_name(requirement: str) -> str:
    match = re.match(r"^\s*([A-Za-z0-9_.-]+)", requirement)
    if not match:
        raise ValueError(f"Unsupported dependency declaration: {requirement}")
    return canonicalize_name(match.group(1))


def load_project_dependency_names(scope: str) -> list[str]:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    project = data["project"]
    names = [parse_requirement_name(item) for item in project.get("dependencies", [])]
    if scope == "runtime+dev":
        for item in project.get("optional-dependencies", {}).get("dev", []):
            names.append(parse_requirement_name(item))
    return sorted(set(names))


def split_license_tokens(raw_value: str) -> list[str]:
    normalized = LICENSE_ALIASES.get(raw_value.strip(), raw_value.strip())
    parts = re.split(r"\s+(?:AND|OR|WITH)\s+|[()]", normalized)
    tokens = []
    for part in parts:
        value = part.strip()
        if value:
            tokens.append(LICENSE_ALIASES.get(value, value))
    return tokens


def extract_license_signals(dist: metadata.Distribution) -> tuple[list[str], list[str]]:
    md = dist.metadata
    classifiers = md.get_all("Classifier") or []
    signals = []
    for key in ("License-Expression", "License"):
        for raw_value in md.get_all(key) or []:
            signals.extend(split_license_tokens(raw_value))
    return signals, classifiers


def is_open_source(dist: metadata.Distribution) -> tuple[bool, list[str], list[str]]:
    signals, classifiers = extract_license_signals(dist)
    if any(item.startswith("License :: OSI Approved ::") for item in classifiers):
        return True, signals, classifiers
    if signals and all(token in APPROVED_LICENSE_TOKENS for token in signals):
        return True, signals, classifiers
    return False, signals, classifiers


def iter_target_distributions(scope: str) -> list[metadata.Distribution]:
    installed = {
        canonicalize_name(dist.metadata["Name"]): dist
        for dist in metadata.distributions()
        if dist.metadata.get("Name")
    }

    if scope == "all-installed":
        return [installed[name] for name in sorted(installed)]

    names = load_project_dependency_names(scope)
    missing = [name for name in names if name not in installed]
    if missing:
        raise RuntimeError(
            "Missing installed distributions for declared dependencies: "
            + ", ".join(sorted(missing))
        )
    return [installed[name] for name in names]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that the project dependencies resolve to open-source packages."
    )
    parser.add_argument(
        "--scope",
        choices=["runtime", "runtime+dev", "all-installed"],
        default="runtime+dev",
        help="Select which dependency set to audit.",
    )
    args = parser.parse_args()

    failures: list[str] = []
    audited = iter_target_distributions(args.scope)

    print(f"Auditing {len(audited)} distributions with scope={args.scope}")
    for dist in audited:
        name = dist.metadata["Name"]
        version = dist.version
        ok, signals, classifiers = is_open_source(dist)
        classifier_labels = [
            item.removeprefix("License :: OSI Approved :: ").strip()
            for item in classifiers
            if item.startswith("License :: OSI Approved ::")
        ]
        rendered = ", ".join(signals or classifier_labels or ["unknown"])
        status = "OK" if ok else "FAIL"
        print(f"[{status}] {name}=={version} :: {rendered}")
        if not ok:
            failures.append(
                f"{name}=={version} could not be verified as open source. "
                f"Signals={signals or ['unknown']} classifiers={classifier_labels or ['none']}"
            )

    if failures:
        print("")
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print("Open-source license audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
