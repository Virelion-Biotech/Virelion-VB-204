"""Fail-closed acceptance gates separating runnable code from decision-grade science."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

REQUIRED_GATES = {
    "phenotype_data_provenance": "Versioned phenotype input, preprocessing and source provenance reviewed.",
    "geometry_mesh_validation": "Host and graft meshes validated against source anatomy, tissue labels and solver requirements.",
    "mesh_time_convergence": "At least three spatial resolutions and two time steps meet the predefined 5% comparison criterion.",
    "monodomain_bidomain_check": "Sweep-scale approximation checked against bidomain on at least one benchmark case.",
    "five_case_benchmark": "Independent reproduction of all five preregistered published benchmark cases.",
    "mechanics_validation": "Mechanical outputs and force/strain transfer metrics validated and convergence characterized.",
    "cross_species_check": "Porcine primary-substrate result compared with human-substrate model and ranking changes recorded.",
    "uncertainty_and_ood_review": "Uncertainty propagation and out-of-distribution/extrapolation flags reviewed.",
    "expert_threshold_review": "Decision thresholds reviewed by a documented multidisciplinary panel."
}

def evaluate_gates(payload: dict[str, Any]) -> dict[str, Any]:
    supplied = payload.get("gates", {})
    reports = []
    for gate_id, required_evidence in REQUIRED_GATES.items():
        row = supplied.get(gate_id, {})
        status = row.get("status", "pending")
        evidence = str(row.get("evidence_uri", "")).strip()
        reviewer = str(row.get("reviewer", "")).strip()
        valid_status = status in {"pending", "passed", "failed"}
        complete = valid_status and status == "passed" and bool(evidence) and bool(reviewer)
        reports.append({
            "id": gate_id, "requirement": required_evidence, "status": status if valid_status else "invalid",
            "evidence_uri": evidence or None, "reviewer": reviewer or None, "complete": complete
        })
    eligible = all(row["complete"] for row in reports)
    failures = [row["id"] for row in reports if row["status"] == "failed"]
    pending = [row["id"] for row in reports if not row["complete"] and row["status"] != "failed"]
    return {
        "decision_grade_eligible": eligible,
        "overall": "ELIGIBLE_FOR_INDEPENDENT_REVIEW" if eligible else ("BLOCKED_BY_FAILED_GATE" if failures else "BLOCKED_PENDING_EVIDENCE"),
        "gates": reports, "failed_gates": failures, "pending_gates": pending,
        "note": "This registry records sign-offs; it cannot itself establish that scientific evidence is correct."
    }

def evaluate_gate_file(path: str | Path) -> dict[str, Any]:
    return evaluate_gates(json.loads(Path(path).read_text(encoding="utf-8")))
