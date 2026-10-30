"""Layer 2 orchestration helpers for real, externally sourced model assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def validate_run_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = {"solver", "parameter_file", "input_meshes", "architecture", "species", "asset_provenance", "parameter_provenance"}
    missing = required - set(manifest)
    if missing:
        raise ValueError("Run manifest missing: " + ", ".join(sorted(missing)))
    if manifest["solver"] not in {"openCARP", "ELECTRA"}:
        raise ValueError("solver must be 'openCARP' or 'ELECTRA'")
    if manifest["architecture"] not in {"A", "B", "C", "D"}:
        raise ValueError("architecture must be one of A, B, C or D")
    param_file = Path(manifest["parameter_file"]).expanduser().resolve()
    if not param_file.is_file():
        raise ValueError(f"Parameter/configuration file does not exist: {param_file}")
    if not isinstance(manifest["input_meshes"], list) or not manifest["input_meshes"]:
        raise ValueError("input_meshes must be a non-empty list of source mesh paths")
    resolved_meshes = []
    for item in manifest["input_meshes"]:
        p = Path(item).expanduser().resolve()
        if not p.is_file():
            raise ValueError(f"Input mesh does not exist: {p}")
        resolved_meshes.append({"path": str(p), "sha256": sha256_file(p)})
    provenance = manifest["asset_provenance"]
    for key in ("source_url", "license_status", "model_id"):
        if not str(provenance.get(key, "")).strip():
            raise ValueError(f"asset_provenance.{key} is required")
    if provenance["license_status"] != "verified":
        raise ValueError("Asset license/redistribution status must be explicitly verified before a solver run")
    parameter_provenance = manifest["parameter_provenance"]
    if not isinstance(parameter_provenance, dict) or not parameter_provenance:
        raise ValueError("parameter_provenance must list the source record for each parameter")
    for key, record in parameter_provenance.items():
        if not (
            str(record.get("source_url", "")).startswith("https://")
            and str(record.get("species", "")).strip()
            and str(record.get("units", "")).strip()
            and record.get("uncertainty") is not None
        ):
            raise ValueError(f"Parameter {key!r} needs source_url, species, units and uncertainty provenance")
    return {
        **manifest,
        "parameter_file": str(param_file),
        "parameter_file_sha256": sha256_file(param_file),
        "input_meshes_resolved": resolved_meshes,
        "solver_configuration_status": "INPUTS_PRESENT_AND_PROVENANCE_DECLARED",
        "decision_grade_eligible": False
    }

def _command_for_run(manifest: dict[str, Any], output_dir: Path) -> list[str]:
    custom = manifest.get("command")
    if custom:
        if not isinstance(custom, list) or not custom or not all(isinstance(x, str) for x in custom):
            raise ValueError("command must be a non-empty list of strings; shell commands are not accepted")
        return [part.format(parameter_file=manifest["parameter_file"], output_dir=str(output_dir)) for part in custom]
    if manifest["solver"] == "openCARP":
        binary = manifest.get("executable") or shutil.which("openCARP") or shutil.which("opencarp")
        if not binary:
            raise FileNotFoundError("openCARP executable not found. Install a compatible openCARP build or set 'executable' in the manifest.")
        return [str(binary), "+F", str(manifest["parameter_file"])]
    raise ValueError("ELECTRA needs a reviewed, version-specific command array in the run manifest; no CLI compatibility is assumed.")

def run_simulation(manifest_path: str | Path, output_dir: str | Path, timeout_seconds: int = 86400) -> dict[str, Any]:
    if timeout_seconds < 1:
        raise ValueError("timeout_seconds must be positive")
    source = Path(manifest_path).expanduser().resolve()
    manifest = json.loads(source.read_text(encoding="utf-8"))
    validated = validate_run_manifest(manifest)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    command = _command_for_run(validated, out)
    if shutil.which(command[0]) is None and not Path(command[0]).is_file():
        raise FileNotFoundError(f"Solver executable cannot be resolved: {command[0]}")
    record: dict[str, Any] = {
        "schema_version": "vb204-solver-run-v1", "manifest_source": str(source),
        "manifest_sha256": sha256_file(source), "validated_manifest": validated,
        "command": command, "working_directory": str(out),
        "started_utc_epoch": time.time(), "status": "RUNNING",
        "note": "A successful process exit is not scientific validation."
    }
    (out / "run_manifest_resolved.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in manifest.get("environment", {}).items()})
    try:
        result = subprocess.run(command, cwd=out, capture_output=True, text=True, timeout=timeout_seconds, env=env, check=False)
        (out / "stdout.log").write_text(result.stdout or "", encoding="utf-8")
        (out / "stderr.log").write_text(result.stderr or "", encoding="utf-8")
        record.update({
            "status": "PROCESS_SUCCEEDED" if result.returncode == 0 else "PROCESS_FAILED",
            "returncode": result.returncode, "finished_utc_epoch": time.time(),
            "stdout_sha256": sha256_file(out / "stdout.log"), "stderr_sha256": sha256_file(out / "stderr.log"),
            "decision_grade_eligible": False
        })
    except subprocess.TimeoutExpired as exc:
        (out / "stdout.log").write_text(str(exc.stdout or ""), encoding="utf-8")
        (out / "stderr.log").write_text(str(exc.stderr or ""), encoding="utf-8")
        record.update({"status": "TIMED_OUT", "finished_utc_epoch": time.time(), "decision_grade_eligible": False})
    (out / "run_manifest_resolved.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record

def prepare_sweep(hosts: list[dict[str, Any]], phenotype_ids: list[str], architectures: list[str] | None = None) -> dict[str, Any]:
    from itertools import product
    if not hosts or not phenotype_ids:
        raise ValueError("Provide at least one host model and phenotype ID")
    architectures = architectures or ["A", "B", "C", "D"]
    if any(a not in {"A", "B", "C", "D"} for a in architectures):
        raise ValueError("Architectures must be selected from A, B, C, D")
    jobs = []
    for host, phenotype, arch in product(hosts, phenotype_ids, architectures):
        mesh = Path(host.get("mesh_path", "")).expanduser()
        ready = mesh.is_file() and host.get("license_status") == "verified" and str(host.get("source_url", "")).startswith("https://") and bool(host.get("species"))
        jobs.append({
            "job_id": f"{host.get('id','host')}-{phenotype}-{arch}",
            "host_id": host.get("id"), "species": host.get("species"),
            "host_mesh": str(mesh.resolve()) if mesh.is_file() else str(mesh),
            "architecture": arch, "phenotype_id": phenotype,
            "asset_ready": bool(ready),
            "status": "READY_FOR_SOLVER_CONFIGURATION" if ready else "BLOCKED_MISSING_ASSET_OR_PROVENANCE",
            "source_url": host.get("source_url"), "license_status": host.get("license_status")
        })
    return {
        "schema_version": "vb204-sweep-manifest-v1", "job_count": len(jobs),
        "jobs": jobs, "decision_grade_eligible": False,
        "note": "This is a matrix of planned cases, not simulated results. Each ready case still needs an architecture-specific geometry/mesh, parameter file, verified solver setup and convergence evidence."
    }
