import pandas as pd
import pytest

from vb204.convergence import evaluate_convergence
from vb204.gates import REQUIRED_GATES, evaluate_gates
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

def test_convergence_requires_multiple_resolutions_and_steps():
    frame = pd.DataFrame([
      {"case_id":"x","spatial_level":1,"dt_ms":1.0,"metric":"activation_ms","value":10.0,"unit":"ms"},
      {"case_id":"x","spatial_level":2,"dt_ms":1.0,"metric":"activation_ms","value":9.8,"unit":"ms"},
    ])
    result = evaluate_convergence(frame)
    assert not result["passed"]
    assert not result["cases"][0]["passed"]

def test_convergence_passes_synthetic_numerical_fixture_only():
    rows=[]
    vals={(1,1.0):10.2,(1,.5):10.1,(2,1.0):10.1,(2,.5):10.02,(3,1.0):10.03,(3,.5):10.0}
    for (level,dt),value in vals.items():
        rows.append({"case_id":"synthetic-test","spatial_level":level,"dt_ms":dt,"metric":"activation_ms","value":value,"unit":"ms"})
    result=evaluate_convergence(pd.DataFrame(rows))
    assert result["passed"]
    assert result["decision_grade_eligible"] is False

def test_validation_gates_default_pending():
    result=evaluate_gates({"gates": {}})
    assert not result["decision_grade_eligible"]
    assert len(result["pending_gates"]) == len(REQUIRED_GATES)

def test_validation_gate_requires_evidence_uri_and_reviewer():
    payload={"gates": {key: {"status":"passed","evidence_uri":"https://example.org/report","reviewer":"Independent reviewer"} for key in REQUIRED_GATES}}
    assert evaluate_gates(payload)["decision_grade_eligible"]
    payload["gates"]["five_case_benchmark"]["evidence_uri"]=""
    assert not evaluate_gates(payload)["decision_grade_eligible"]

def test_maturity_scorecard_relative_not_absolute():
    genes = ["TNNI3","MYH7","TNNI1","MYH6","SCN5A","POU5F1"]
    frame = pd.DataFrame({"immature":[1,1,10,10,1,5],"mature":[10,10,1,1,10,1]},index=genes)
    result = score_maturity(frame)
    assert result["status"] == "RELATIVE_RESEARCH_SCORECARD_NOT_VALIDATED_FOR_RELEASE"
    assert result["composite_relative_index"]["mature"] > result["composite_relative_index"]["immature"]
