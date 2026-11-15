import hashlib
import json
import pandas as pd
import pytest
from vb204 import acquisition
from vb204.phenotype import load_expression
from vb204.scoring import ScoreSettings, score_architectures, validate_candidates


def test_download_verifies_size_and_checksum_and_writes_atomically(tmp_path, monkeypatch):
    payload = b"small trusted model fixture"
    metadata = {"id": 123, "doi": "10.0000/example",
        "metadata": {"title": "fixture", "license": {"id": "CC0-1.0"}},
        "files": [{"key": "fixture.bin", "size": len(payload),
            "checksum": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "links": {"self": "https://zenodo.org/api/records/123/files/fixture.bin/content"}}]}
    class FakeResponse:
        def __init__(self, data): self.data, self.offset = data, 0
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size=-1):
            if size < 0: size = len(self.data)
            chunk = self.data[self.offset:self.offset + size]; self.offset += len(chunk); return chunk
    calls = {"n": 0}
    def fake_urlopen(request, timeout=0):
        calls["n"] += 1
        return FakeResponse(json.dumps(metadata).encode() if calls["n"] == 1 else payload)
    monkeypatch.setattr(acquisition, "urlopen", fake_urlopen)
    result = acquisition.download_record_file("123", "fixture.bin", tmp_path, accept_license=True)
    assert result["checksum_verified"] and result["record_size_verified"]
    assert result["sha256"] == hashlib.sha256(payload).hexdigest()
    assert (tmp_path / "fixture.bin").read_bytes() == payload
    assert not list(tmp_path.glob("*.part"))


def test_download_rejects_checksum_mismatch_and_leaves_no_partial_file(tmp_path, monkeypatch):
    metadata = {"id": 1, "metadata": {}, "files": [{"key": "bad.bin", "size": 3,
        "checksum": "sha256:" + "0" * 64,
        "links": {"self": "https://zenodo.org/api/records/1/files/bad.bin/content"}}]}
    class FakeResponse:
        def __init__(self, data): self.data, self.offset = data, 0
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, size=-1):
            if size < 0:
                size = len(self.data) - self.offset
            chunk = self.data[self.offset:self.offset + size]
            self.offset += len(chunk)
            return chunk
    calls = {"n": 0}
    def fake_urlopen(request, timeout=0):
        calls["n"] += 1
        return FakeResponse(json.dumps(metadata).encode() if calls["n"] == 1 else b"abc")
    monkeypatch.setattr(acquisition, "urlopen", fake_urlopen)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        acquisition.download_record_file("1", "bad.bin", tmp_path, accept_license=True)
    assert not (tmp_path / "bad.bin").exists()
    assert not list(tmp_path.iterdir())


def test_download_rejects_non_zenodo_urls(tmp_path, monkeypatch):
    metadata = {"id": 1, "metadata": {}, "files": [{"key": "x", "size": 1, "checksum": None,
        "links": {"self": "https://example.com/x"}}]}
    monkeypatch.setattr(acquisition, "fetch_record_metadata", lambda _id: metadata)
    with pytest.raises(ValueError, match="HTTPS Zenodo"):
        acquisition.download_record_file("1", "x", tmp_path, accept_license=True)


def test_expression_gene_ids_are_unique_after_case_normalization(tmp_path):
    path = tmp_path / "expression.csv"
    path.write_text(",sample1,sample2\ntnni3,1,2\nTNNI3,2,3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="after normalization"):
        load_expression(path)


def test_candidate_ids_normalize_whitespace_before_duplicate_check():
    frame = pd.DataFrame([
        {"architecture":"A","arrhythmia_risk_mean":.2,"arrhythmia_risk_sd":.1,"mechanical_contribution_mean":.3,"mechanical_contribution_sd":.1,"synchrony_mean":.4,"synchrony_sd":.1},
        {"architecture":" A ","arrhythmia_risk_mean":.3,"arrhythmia_risk_sd":.1,"mechanical_contribution_mean":.4,"mechanical_contribution_sd":.1,"synchrony_mean":.5,"synchrony_sd":.1}])
    with pytest.raises(ValueError, match="after whitespace normalization"):
        validate_candidates(frame)


def test_score_settings_reject_boolean_draw_count():
    with pytest.raises(ValueError, match="integer"):
        ScoreSettings(weights={"arrhythmia_risk":.5,"mechanical_contribution":.25,"synchrony":.25}, draws=True)


def test_tied_architectures_do_not_receive_arbitrary_rank_one_probability():
    frame = pd.DataFrame([
        {"architecture":"A","arrhythmia_risk_mean":.5,"arrhythmia_risk_sd":0,"mechanical_contribution_mean":.5,"mechanical_contribution_sd":0,"synchrony_mean":.5,"synchrony_sd":0},
        {"architecture":"B","arrhythmia_risk_mean":.5,"arrhythmia_risk_sd":0,"mechanical_contribution_mean":.5,"mechanical_contribution_sd":0,"synchrony_mean":.5,"synchrony_sd":0}])
    result = score_architectures(frame, settings=ScoreSettings(weights={"arrhythmia_risk":.5,"mechanical_contribution":.25,"synchrony":.25},draws=100,seed=1))
    assert (result["probability_rank_1"] == 0).all()
    assert (result["median_rank"] == 1.5).all()


def _solver_manifest(tmp_path, command):
    import sys

    parameter_file = tmp_path / "parameters.json"
    mesh_file = tmp_path / "mesh.dat"
    parameter_file.write_text("{}", encoding="utf-8")
    mesh_file.write_text("mesh-fixture", encoding="utf-8")
    manifest = {
        "solver": "openCARP",
        "parameter_file": str(parameter_file),
        "input_meshes": [str(mesh_file)],
        "architecture": "A",
        "species": "synthetic-test-only",
        "asset_provenance": {
            "source_url": "https://example.org/mesh",
            "license_status": "verified",
            "model_id": "synthetic-fixture",
        },
        "parameter_provenance": {
            "conduction_velocity": {
                "source_url": "https://example.org/parameter",
                "species": "synthetic-test-only",
                "units": "cm/ms",
                "uncertainty": 0.01,
            }
        },
        "command": [sys.executable, "-c", command],
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_solver_streams_logs_and_atomically_finalizes_manifest(tmp_path):
    from vb204.simulation import run_simulation

    manifest = _solver_manifest(tmp_path, "import sys; print('stdout-marker'); print('stderr-marker', file=sys.stderr)")
    output = tmp_path / "run-output"
    result = run_simulation(manifest, output, timeout_seconds=10)
    assert result["status"] == "PROCESS_SUCCEEDED"
    assert "stdout-marker" in (output / "stdout.log").read_text(encoding="utf-8")
    assert "stderr-marker" in (output / "stderr.log").read_text(encoding="utf-8")
    assert result["stdout_bytes"] > 0 and result["stderr_bytes"] > 0
    saved = json.loads((output / "run_manifest_resolved.json").read_text(encoding="utf-8"))
    assert saved["status"] == "PROCESS_SUCCEEDED"
    assert saved["stdout_sha256"] == result["stdout_sha256"]
    assert not list(output.glob("*.tmp"))


def test_solver_timeout_kills_process_and_preserves_partial_logs(tmp_path):
    from vb204.simulation import run_simulation

    manifest = _solver_manifest(tmp_path, "import time; print('before-timeout', flush=True); time.sleep(30)")
    output = tmp_path / "timeout-output"
    result = run_simulation(manifest, output, timeout_seconds=1)
    assert result["status"] == "TIMED_OUT"
    assert result["returncode"] is not None
    assert "before-timeout" in (output / "stdout.log").read_text(encoding="utf-8")
    saved = json.loads((output / "run_manifest_resolved.json").read_text(encoding="utf-8"))
    assert saved["status"] == "TIMED_OUT"


def test_solver_rejects_boolean_timeout(tmp_path):
    from vb204.simulation import run_simulation

    with pytest.raises(ValueError, match="positive integer"):
        run_simulation(tmp_path / "unused.json", tmp_path / "out", timeout_seconds=True)
