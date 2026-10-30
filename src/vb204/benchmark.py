"""Ordinal five-case benchmark gate; does not establish quantitative validation."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .plan import load_program

REQUIRED_COLUMNS = {"study", "architecture", "observed_class", "predicted_risk", "source", "observed_endpoint", "notes"}

def evaluate_benchmark(frame: pd.DataFrame) -> dict:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        return {"passed": False, "decision_grade_eligible": False, "errors": ["Missing columns: " + ", ".join(sorted(missing))], "checks": {}, "case_count": len(frame)}
    data = frame.copy()
    for col in ("study", "architecture", "observed_class", "source", "observed_endpoint", "notes"):
        data[col] = data[col].astype(str).str.strip()
    data["architecture"] = data["architecture"].str.upper()
    errors: list[str] = []
    checks: dict[str, bool] = {}
    expected = {row["study"]: row for row in load_program()["benchmark_cases"]}
    checks["exactly_five_unique_named_cases"] = len(data) == 5 and data["study"].nunique() == 5 and set(data["study"]) == set(expected)
    if not checks["exactly_five_unique_named_cases"]:
        errors.append("Expected exactly one row for each of the five named VB-204 benchmark cases.")
    if not checks["exactly_five_unique_named_cases"]:
        return {"passed": False, "decision_grade_eligible": False, "errors": errors, "checks": checks, "case_count": len(data)}
    class_ok = True
    architecture_ok = True
    source_ok = True
    for _, row in data.iterrows():
        spec = expected[row["study"]]
        class_ok &= row["observed_class"].lower() == spec["observed_class"]
        architecture_ok &= row["architecture"] == spec["architecture"]
        source_ok &= row["source"].startswith("https://") and bool(row["observed_endpoint"]) and row["observed_endpoint"].lower() != "nan"
    checks["preregistered_class_matches_protocol"] = bool(class_ok)
    checks["architecture_mapping_matches_protocol"] = bool(architecture_ok)
    checks["endpoint_and_source_present"] = bool(source_ok)
    if not class_ok:
        errors.append("Observed classes must match the proposal's preregistered labels; record deviations instead of silently relabeling.")
    if not architecture_ok:
        errors.append("Architecture mapping differs from the preregistered case set.")
    if not source_ok:
        errors.append("Each study requires a source URL and an extracted endpoint description.")
    try:
        data["predicted_risk"] = pd.to_numeric(data["predicted_risk"], errors="raise")
        risk_ok = bool(np.isfinite(data["predicted_risk"].to_numpy(float)).all() and data["predicted_risk"].between(0, 1).all())
    except (ValueError, TypeError):
        risk_ok = False
    checks["predictions_finite_and_scaled"] = risk_ok
    if not risk_ok:
        errors.append("predicted_risk must be finite and scaled to [0, 1].")
    order_ok = False
    if risk_ok and class_ok:
        high = data.loc[data["observed_class"].str.lower() == "high", "predicted_risk"].to_numpy(float)
        moderate = data.loc[data["observed_class"].str.lower() == "moderate", "predicted_risk"].to_numpy(float)
        low = data.loc[data["observed_class"].str.lower() == "low", "predicted_risk"].to_numpy(float)
        order_ok = bool(len(high) == 3 and len(moderate) == 1 and len(low) == 1 and np.min(high) > np.max(moderate) > np.max(low))
    checks["predicted_ordinal_risk_order_matches_labels"] = order_ok
    if not order_ok:
        errors.append("The model's relative scores must order all high-risk cases above the moderate case and the moderate case above the low-risk EHM-patch case.")
    passed = bool(all(checks.values()))
    return {
        "passed": passed, "decision_grade_eligible": False, "checks": checks, "errors": errors,
        "case_count": len(data),
        "interpretation": "A pass is ordinal concordance with proposal labels only. Study endpoints differ; quantitative reproduction requires study-specific endpoint extraction, harmonization, uncertainty and independent reproduction. This gate alone never unlocks decision-grade ranking."
    }
