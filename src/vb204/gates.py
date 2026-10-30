"""Evidence-gate registry; never automatically declares scientific validity."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_GATES = {
    "phenotype_data_provenance": "Versioned phenotype input, preprocessing and source provenance reviewed.",
    "geometry_mesh_validation": "Host/graft meshes validated against source anatomy, tissue labels and solver requirements.",
    "mesh_time_convergence": "At least three spatial resolutions and two time steps meet the predefined 5% criterion.",
    "monodomain_bidomain_check": "Sweep-scale approximation checked against bidomain on a benchmark case.",
    "five_case_benchmark": "Independent reproduction of all five pre-registered benchmark cases.",
    "mechanics_validation": "Mechanical outputs and force/strain transfer metrics validated.",
    "cross_species_check": "Porcine and human-substrate results compared and ranking changes recorded.",
    "uncertainty_and_ood_review": "Uncertainty propagation and out-of-distribution flags reviewed.",
    "expert_threshold_review": "Threshold rationale reviewed by a documented multidisciplinary panel.",
}


def _evidence_uri_valid(value: str) -> bool:
    return value.startswith(("https://", "file://", "doi:"))


def evaluate_gates(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether explicit reviewer sign-offs are recorded."""
    supplied = payload.get("gates", {})
    if not isinstance(supplied, dict):
        supplied = {}
    reports = []
    for gate_id, requirement in REQUIRED_GATES.items():
        row = supplied.get(gate_id, {})
        if not isinstance(row, dict):
            row = {}
        status = row.get("status", "pending")
        evidence = str(row.get("evidence_uri", "")).strip()
        reviewer = str(row.get("reviewer", "")).strip()
        valid_status = status in {"pending", "passed", "failed"}
        complete = bool(valid_status and status == "passed" and _evidence_uri_valid(evidence) and reviewer)
        reports.append({
            "id": gate_id,
            "requirement": requirement,
            "status": status if valid_status else "invalid",
            "evidence_uri": evidence or None,
            "reviewer": reviewer or None,
            "complete": complete,
        })
    all_recorded = all(row["complete"] for row in reports)
    failures = [row["id"] for row in reports if row["status"] == "failed"]
    pending = [row["id"] for row in reports if not row["complete"] and row["status"] != "failed"]
    return {
        "all_signoff_gates_recorded": all_recorded,
        "eligible_for_independent_review": all_recorded,
        "decision_grade_eligible": False,
        "overall": "ALL_SIGNOFFS_RECORDED_REQUIRES_INDEPENDENT_REVIEW" if all_recorded else ("BLOCKED_BY_FAILED_GATE" if failures else "BLOCKED_PENDING_EVIDENCE"),
        "gates": reports,
        "failed_gates": failures,
        "pending_gates": pending,
        "note": "This registry records sign-offs only. It cannot prove evidence quality or scientific validity; decision-grade status is never assigned automatically.",
    }


def validate_gate_report(report: dict[str, Any]) -> bool:
    """Check completeness of a generated sign-off report, not scientific truth."""
    rows = report.get("gates")
    if not isinstance(rows, list):
        return False
    by_id = {row.get("id"): row for row in rows if isinstance(row, dict)}
    if set(by_id) != set(REQUIRED_GATES) or len(rows) != len(REQUIRED_GATES):
        return False
    for gate_id in REQUIRED_GATES:
        row = by_id[gate_id]
        if row.get("status") != "passed" or row.get("complete") is not True:
            return False
        if not _evidence_uri_valid(str(row.get("evidence_uri") or "").strip()):
            return False
        if not str(row.get("reviewer") or "").strip():
            return False
    return report.get("all_signoff_gates_recorded") is True


def evaluate_gate_file(path: str | Path) -> dict[str, Any]:
    return evaluate_gates(json.loads(Path(path).read_text(encoding="utf-8")))
