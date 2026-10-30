import pandas as pd
import pytest

from vb204.convergence import evaluate_convergence
from vb204.gates import REQUIRED_GATES, evaluate_gates, validate_gate_report
from vb204.geometry import validate_geometry_spec
from vb204.phenotype import score_maturity
from vb204.plan import architecture_scores, evaluate_go_no_go, report_data


def test_plan_renders_all_architectures_and_fails_closed():
    assert len(architecture_scores()) == 4
    assert evaluate_go_no_go()["overall"].startswith("HOLD")
    data = report_data()
    assert data["scientific_status"]["decision_grade_rankings_allowed"] is False


def test_geometry_requires_actual_sourced_parameters():
    with pytest.raises(ValueError, match="incomplete"):
        validate_geometry_spec("C", {"thickness_mm": 1.0})


def test_geometry_requires_provenance_for_every_numeric_parameter():
    params = {
        "thickness_mm": 1.0, "alignment": "anisotropic", "cell_density_per_mm3": 1e5,
        "matrix_stiffness_kpa": 2.0, "vascular_void_fraction": .1, "interface_contact_area_mm2": 10.0,
    }
    with pytest.raises(ValueError, match="provenance"):
        validate_geometry_spec("C", params, {})


def _convergence_frame(values):
    rows = []
    for (level, dt), value in values.items():
        rows.append({"case_id": "synthetic-test", "spatial_level": level, "dt_ms": dt,
                     "metric": "activation_ms", "value": value, "unit": "ms"})
    return pd.DataFrame(rows)


def test_convergence_requires_multiple_resolutions_and_steps():
    frame = pd.DataFrame([
      {"case_id":"x","spatial_level":1,"dt_ms":1.0,"metric":"activation_ms","value":10.0,"unit":"ms"},
      {"case_id":"x","spatial_level":2,"dt_ms":1.0,"metric":"activation_ms","value":9.8,"unit":"ms"},
    ])
    result = evaluate_convergence(frame)
    assert not result["passed"]
    assert not result["cases"][0]["passed"]


def test_convergence_passes_synthetic_numerical_fixture_only():
    vals = {(1,1.0):10.2,(1,.5):10.1,(2,1.0):10.1,(2,.5):10.02,(3,1.0):10.03,(3,.5):10.0}
    result = evaluate_convergence(_convergence_frame(vals))
    assert result["passed"]
    assert result["decision_grade_eligible"] is False


def test_convergence_can_select_middle_level_when_coarsest_fails():
    vals = {(1,1.0):12.0,(1,.5):11.8,(2,1.0):10.2,(2,.5):10.1,(3,1.0):10.03,(3,.5):10.0}
    result = evaluate_convergence(_convergence_frame(vals))
    assert result["passed"]
    assert result["cases"][0]["selected_coarsest_level"] == 2.0


def test_convergence_fails_on_incomplete_grid():
    vals = {(1,1.0):10.2,(1,.5):10.1,(2,1.0):10.1,(2,.5):10.02,(3,.5):10.0}
    result = evaluate_convergence(_convergence_frame(vals))
    assert not result["passed"]
    assert any("found 0" in error for error in result["cases"][0]["errors"])


def test_validation_gates_default_pending():
    result = evaluate_gates({"gates": {}})
    assert not result["all_signoff_gates_recorded"]
    assert result["decision_grade_eligible"] is False
    assert len(result["pending_gates"]) == len(REQUIRED_GATES)


def test_validation_gate_requires_evidence_uri_and_reviewer():
    payload={"gates": {key: {"status":"passed","evidence_uri":"https://example.org/report","reviewer":"Independent reviewer"} for key in REQUIRED_GATES}}
    report = evaluate_gates(payload)
    assert report["all_signoff_gates_recorded"]
    assert not report["decision_grade_eligible"]
    assert validate_gate_report(report)
    payload["gates"]["five_case_benchmark"]["evidence_uri"]=""
    incomplete = evaluate_gates(payload)
    assert not incomplete["all_signoff_gates_recorded"]
    assert not validate_gate_report(incomplete)


def test_fabricated_boolean_cannot_unlock_scoring():
    assert not validate_gate_report({"decision_grade_eligible": True, "gates": []})


def test_maturity_scorecard_relative_not_absolute():
    genes = ["TNNI3","MYH7","TNNI1","MYH6","SCN5A","POU5F1"]
    frame = pd.DataFrame({"immature":[1,1,10,10,1,5],"mature":[10,10,1,1,10,1]},index=genes)
    result = score_maturity(frame)
    assert result["status"] == "RELATIVE_RESEARCH_SCORECARD_NOT_VALIDATED_FOR_RELEASE"
    assert result["composite_relative_index"]["mature"] > result["composite_relative_index"]["immature"]
