"""Versioned, data-driven planning layer for the VB-204 discovery program."""
from __future__ import annotations
from datetime import date, timedelta
from pathlib import Path
from typing import Any
import yaml

ASSET_DIR = Path(__file__).resolve().parent / "assets"
SCALE = {"low": 1.0, "low_moderate": 1.5, "moderate": 2.0, "high": 3.0, "very_high": 4.0, "unknown": 2.0}

def load_program() -> dict[str, Any]:
    with (ASSET_DIR / "program.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)

def architecture_scores(weights: dict[str, float] | None = None) -> list[dict[str, Any]]:
    program = load_program()
    default = program["architecture_weights"]
    chosen = dict(weights or default)
    if set(chosen) != set(default):
        raise ValueError(f"Weights must specify exactly: {', '.join(default)}")
    if any(not isinstance(v, (int, float)) or v < 0 for v in chosen.values()):
        raise ValueError("Weights must be non-negative numbers")
    if abs(sum(chosen.values()) - 1.0) > 1e-6:
        raise ValueError("Architecture weights must sum to 1.0")
    output = []
    for arch in program["architectures"]:
        scores = arch["illustrative_scores"]
        score = sum(float(scores[k]) * float(chosen[k]) for k in chosen)
        output.append({
            "id": arch["id"], "name": arch["name"], "program_position": arch["program_position"],
            "illustrative_score": round(score, 4), "axis_scores": scores,
            "evidence_status": "ILLUSTRATIVE_NOT_EMPIRICALLY_CALIBRATED"
        })
    return sorted(output, key=lambda row: (-row["illustrative_score"], row["id"]))

def risk_scores() -> list[dict[str, Any]]:
    doc = load_program()["risk_register"]
    output = []
    for risk in doc["items"]:
        severity = float(doc["scale"].get(risk["severity"], 2))
        likelihood = float(doc["scale"].get(risk["likelihood"], 2))
        output.append({**risk, "severity_score": severity, "likelihood_score": likelihood,
                       "rpn": round(severity * likelihood, 2)})
    return sorted(output, key=lambda x: (not x["hard_gate"], -x["rpn"], x["id"]))

def evaluate_go_no_go(overrides: dict[str, str] | None = None) -> dict[str, Any]:
    rows = [dict(row) for row in load_program()["go_no_go"]["criteria"]]
    valid = {"GO": {"unmet", "partially_met", "met"}, "NO-GO": {"not_triggered", "triggered"}}
    for key, status in (overrides or {}).items():
        found = next((row for row in rows if row["id"] == key), None)
        if found is None:
            raise ValueError(f"Unknown GO/NO-GO criterion: {key}")
        if status not in valid[found["type"]]:
            raise ValueError(f"Invalid status {status!r} for criterion {key}")
        found["status"] = status
        found["override_for_this_run_only"] = True
    if any(r["type"] == "NO-GO" and r["status"] == "triggered" for r in rows):
        overall = "NO-GO"
    elif all(r["status"] == "met" for r in rows if r["type"] == "GO"):
        overall = "GO"
    else:
        overall = "HOLD — insufficient evidence to call GO or NO-GO"
    return {"overall": overall, "criteria": rows}

def _month_date(start: date, month: float) -> date:
    return start + timedelta(days=round(month * 365.2425 / 12.0))

def roadmap_status(today: date | None = None) -> list[dict[str, Any]]:
    program = load_program()
    start = date.fromisoformat(program["program"]["program_start_date"])
    current = today or date.today()
    output = []
    for milestone in program["roadmap_12_months"]:
        row = dict(milestone)
        row["window_start"] = _month_date(start, milestone["start_month"]).isoformat()
        row["window_end"] = _month_date(start, milestone["end_month"]).isoformat()
        if current < date.fromisoformat(row["window_start"]):
            row["computed_status"] = "upcoming"
        elif current <= date.fromisoformat(row["window_end"]):
            row["computed_status"] = "in_window"
        else:
            row["computed_status"] = "window_passed"
        output.append(row)
    return output

def report_data() -> dict[str, Any]:
    program = load_program()
    return {
        "program": program["program"],
        "architecture_comparison": architecture_scores(),
        "risk_register": risk_scores(),
        "hypotheses": program["hypotheses"],
        "workstreams": program["workstreams"],
        "roadmap_12_months": roadmap_status(),
        "computational_workstream_18_weeks": program["computational_workstream_18_weeks"],
        "go_no_go": evaluate_go_no_go(),
        "benchmark_cases": program["benchmark_cases"],
        "references": program["references"],
        "scientific_status": {
            "decision_grade_rankings_allowed": False,
            "reason": "Real input provenance, solver validation, convergence evidence and independent five-case reproduction are not bundled or inferred."
        }
    }

def render_report() -> str:
    data = report_data()
    lines = [
        f"# {data['program']['id']} — {data['program']['title']}",
        f"Stage: {data['program']['stage']} | Evidence: {data['program']['evidence_status']}",
        "",
        "## Architecture comparison (illustrative only)",
        "| Rank | ID | Architecture | Score | Status |",
        "|---:|---|---|---:|---|"
    ]
    for idx, row in enumerate(data["architecture_comparison"], 1):
        lines.append(f"| {idx} | {row['id']} | {row['name']} | {row['illustrative_score']:.3f} | {row['evidence_status']} |")
    lines += ["", "## Risk register", "| ID | Risk | Severity | Likelihood | RPN | Hard gate |", "|---|---|---|---|---:|---|"]
    for r in data["risk_register"]:
        lines.append(f"| {r['id']} | {r['name']} | {r['severity']} | {r['likelihood']} | {r['rpn']:.2f} | {'YES' if r['hard_gate'] else 'no'} |")
    lines += ["", "## GO/NO-GO", f"**Overall call: {data['go_no_go']['overall']}**", "", "| Criterion | Type | Status | Dependency |", "|---|---|---|---|"]
    for g in data["go_no_go"]["criteria"]:
        lines.append(f"| {g['id']} — {g['text']} | {g['type']} | {g['status']} | {', '.join(g['depends_on'])} |")
    lines += ["", "## 18-week computational plan", "| Weeks | Layer | Activity | Deliverable |", "|---|---|---|---|"]
    for row in data["computational_workstream_18_weeks"]:
        lines.append(f"| {row['weeks']} | {row['layer']} | {row['activity']} | {row['deliverable']} |")
    lines += ["", "## Evidence boundary", data["scientific_status"]["reason"], "", data["program"]["scope_boundary"]]
    return "\n".join(lines) + "\n"
