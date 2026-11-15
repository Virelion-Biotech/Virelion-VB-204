"""Layer 2 orchestration helpers for real, externally sourced model assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


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


def _stop_process_tree(process: subprocess.Popen[Any]) -> str:
    """Terminate the solver and its descendants without buffering their output."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
        return "SIGTERM"
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            process.kill()
        process.wait()
        return "SIGKILL"


def run_simulation(manifest_path: str | Path, output_dir: str | Path, timeout_seconds: int = 86400) -> dict[str, Any]:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")
    source = Path(manifest_path).expanduser().resolve()
    manifest = json.loads(source.read_text(encoding="utf-8"))
    validated = validate_run_manifest(manifest)
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    command = _command_for_run(validated, out)
    if shutil.which(command[0]) is None and not Path(command[0]).is_file():
        raise FileNotFoundError(f"Solver executable cannot be resolved: {command[0]}")
    stdout_path, stderr_path = out / "stdout.log", out / "stderr.log"
    record: dict[str, Any] = {
        "schema_version": "vb204-solver-run-v1", "manifest_source": str(source),
        "manifest_sha256": sha256_file(source), "validated_manifest": validated,
        "command": command, "working_directory": str(out),
        "started_utc_epoch": time.time(), "status": "RUNNING",
        "timeout_seconds": timeout_seconds,
        "log_policy": "stdout and stderr stream directly to files; output is not buffered in memory",
        "note": "A successful process exit is not scientific validation."
    }
    resolved_path = out / "run_manifest_resolved.json"
    _write_json_atomic(resolved_path, record)
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in manifest.get("environment", {}).items()})
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                command, cwd=out, stdout=stdout_handle, stderr=stderr_handle, env=env,
                start_new_session=(os.name == "posix"), creationflags=creationflags,
            )
            try:
                returncode = process.wait(timeout=timeout_seconds)
                status = "PROCESS_SUCCEEDED" if returncode == 0 else "PROCESS_FAILED"
                termination = None
            except subprocess.TimeoutExpired:
                termination = _stop_process_tree(process)
                returncode = process.returncode
                status = "TIMED_OUT"
            for handle in (stdout_handle, stderr_handle):
                handle.flush()
                os.fsync(handle.fileno())
        record.update({
            "status": status, "returncode": returncode, "termination_signal": termination,
            "finished_utc_epoch": time.time(),
            "stdout_sha256": sha256_file(stdout_path), "stderr_sha256": sha256_file(stderr_path),
            "stdout_bytes": stdout_path.stat().st_size, "stderr_bytes": stderr_path.stat().st_size,
            "decision_grade_eligible": False
        })
    except OSError as exc:
        stdout_path.touch(exist_ok=True)
        stderr_path.touch(exist_ok=True)
        record.update({
            "status": "LAUNCH_FAILED", "error": f"{type(exc).__name__}: {exc}",
            "finished_utc_epoch": time.time(),
            "stdout_sha256": sha256_file(stdout_path), "stderr_sha256": sha256_file(stderr_path),
            "decision_grade_eligible": False
        })
        _write_json_atomic(resolved_path, record)
        raise
    _write_json_atomic(resolved_path, record)
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
