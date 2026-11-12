"""Integrity tests for the VB-204 discovery-stage configuration and manifests.

VB-204 is a research scaffold: these tests guard the declared contracts that
later pipeline layers will consume, so drift is caught before code depends on it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

import vb204

ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    payload = yaml.safe_load((ROOT / relative).read_text(encoding="utf-8"))
    assert isinstance(payload, dict), f"{relative} must be a YAML mapping"
    return payload


@pytest.fixture(scope="module")
def architectures() -> dict:
    return _load("configs/architectures.yaml")


@pytest.fixture(scope="module")
def registry() -> dict:
    return _load("data/manifests/benchmark_registry.yaml")


@pytest.fixture(scope="module")
def axes() -> dict:
    return _load("configs/phenotype_axes.yaml")


def test_package_version_matches_pyproject() -> None:
    from packaging.version import Version

    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE).group(1)
    assert Version(vb204.__version__) == Version(declared)


def test_architectures_are_fully_described(architectures: dict) -> None:
    entries = architectures["architectures"]
    assert set(entries) == {"A", "B", "C", "D"}
    for key, entry in entries.items():
        for field in ("name", "description", "vb204_position"):
            assert isinstance(entry[field], str) and entry[field].strip(), (key, field)
        for field in ("strengths", "liabilities"):
            assert entry[field] and all(isinstance(x, str) and x.strip() for x in entry[field]), (key, field)
    names = [entry["name"] for entry in entries.values()]
    assert len(names) == len(set(names))


def test_shared_design_variables_are_unique_identifiers(architectures: dict) -> None:
    shared = architectures["shared_variables"]
    assert shared and len(shared) == len(set(shared))
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in shared)


def test_benchmark_registry_has_exactly_five_unique_cases(registry: dict) -> None:
    cases = registry["benchmarks"]
    ids = [case["id"] for case in cases]
    assert len(ids) == 5
    assert len(ids) == len(set(ids))
    required = {"id", "citation", "model", "architecture", "outcome", "role", "notes"}
    for case in cases:
        assert required <= set(case), case["id"]
        assert all(str(case[field]).strip() for field in required), case["id"]
        assert re.fullmatch(r"[a-z]+_(19|20)\d\d", case["id"]), case["id"]
        assert case["id"].rsplit("_", 1)[1] in case["citation"], case["id"]


def test_benchmark_architectures_reference_declared_architectures(
    registry: dict, architectures: dict
) -> None:
    declared = set(architectures["architectures"])
    for case in registry["benchmarks"]:
        letter = case["architecture"].split()[0]
        assert letter in declared, case["id"]


def test_gate_composition_matches_the_documented_rule(registry: dict) -> None:
    """Four positive cell-suspension cases and one architecture-matched negative."""
    cases = registry["benchmarks"]
    positives = [c for c in cases if c["role"].startswith("positive_")]
    negatives = [c for c in cases if c["role"].startswith("negative_")]
    assert len(positives) == 4 and len(negatives) == 1
    assert all(c["architecture"].startswith("A") for c in positives)
    negative = negatives[0]
    assert negative["architecture"].startswith("C")
    assert negative["id"].split("_")[0].capitalize() in registry["gate_rule"]
    assert "five" in registry["gate_rule"]


def test_independent_mechanism_checks_are_distinct_from_gate_cases(registry: dict) -> None:
    gate_ids = {c["id"] for c in registry["benchmarks"]}
    checks = registry["independent_mechanism_check"]
    assert checks
    for check in checks:
        assert check["id"] not in gate_ids
        assert check["citation"].strip() and check["role"].strip()


def test_phenotype_axes_carry_provenance(axes: dict) -> None:
    entries = axes["axes"]
    assert len(entries) >= 6
    allowed_status = {"to_be_parameterized", "parameterized", "validated"}
    for name, entry in entries.items():
        assert re.fullmatch(r"[a-z][a-z0-9_]*", name)
        assert entry["description"].strip()
        assert entry["primary_sources"] and all(s.strip() for s in entry["primary_sources"])
        assert entry["status"] in allowed_status, name
    assert any("provenance" in note for note in axes["notes"])


@pytest.mark.parametrize(
    "document",
    ["docs/boundaries.md", "docs/layers/layer25_benchmark_gate.md", "docs/layers/README.md", "docs/proposal/README.md"],
)
def test_documented_entry_points_exist(document: str) -> None:
    assert (ROOT / document).is_file()


def test_markdown_relative_links_resolve() -> None:
    link = re.compile(r"\]\((?!https?://|#|mailto:)([^)#\s]+)")
    missing = []
    for doc in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
        for target in link.findall(doc.read_text(encoding="utf-8")):
            if not (doc.parent / target).exists():
                missing.append(f"{doc.relative_to(ROOT)} -> {target}")
    assert not missing, missing


def test_setup_script_is_valid_bash() -> None:
    script = ROOT / "scripts" / "setup_environment.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    assert "set -euo pipefail" in script.read_text()
