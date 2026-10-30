"""Numerical mesh/time-step convergence checks for externally generated solver metrics."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"case_id", "spatial_level", "dt_ms", "metric", "value", "unit"}

def evaluate_convergence(frame: pd.DataFrame, tolerance_percent: float = 5.0) -> dict[str, Any]:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Missing convergence columns: {', '.join(sorted(missing))}")
    if not 0 < tolerance_percent <= 100:
        raise ValueError("tolerance_percent must be in (0, 100]")
    df = frame.copy()
    for col in ("spatial_level", "dt_ms", "value"):
        df[col] = pd.to_numeric(df[col], errors="raise")
    if df.empty or not np.isfinite(df[["spatial_level", "dt_ms", "value"]].to_numpy(dtype=float)).all():
        raise ValueError("Convergence metrics must be non-empty and finite")
    if (df["dt_ms"] <= 0).any():
        raise ValueError("dt_ms must be positive")
    if df.duplicated(["case_id", "spatial_level", "dt_ms", "metric"]).any():
        raise ValueError("Duplicate case/spatial_level/dt_ms/metric records")
    case_reports = []
    for case_id, case in df.groupby("case_id"):
        levels = sorted(case["spatial_level"].unique())
        timesteps = sorted(case["dt_ms"].unique(), reverse=True)  # coarse to fine
        metrics = sorted(case["metric"].unique())
        if len(levels) < 3 or len(timesteps) < 2:
            case_reports.append({"case_id": str(case_id), "passed": False, "errors": ["Require >=3 spatial levels and >=2 time steps"]})
            continue
        finest_level = max(levels)
        finest_dt = min(timesteps)
        errors = []
        deviations = []
        for metric in metrics:
            ref = case[(case["spatial_level"] == finest_level) & (case["dt_ms"] == finest_dt) & (case["metric"] == metric)]
            if len(ref) != 1:
                errors.append(f"Missing unique finest-mesh/finest-time reference for metric {metric}")
                continue
            ref_value = float(ref["value"].iloc[0])
            for _, row in case[(case["metric"] == metric)].iterrows():
                if row["spatial_level"] == finest_level and row["dt_ms"] == finest_dt:
                    continue
                value = float(row["value"])
                if abs(ref_value) < 1e-12:
                    deviation = 0.0 if abs(value) < 1e-12 else float("inf")
                else:
                    deviation = abs(value - ref_value) / abs(ref_value) * 100
                deviations.append({"metric": metric, "spatial_level": float(row["spatial_level"]), "dt_ms": float(row["dt_ms"]), "reference": ref_value, "value": value, "deviation_percent": deviation})
        within = [d for d in deviations if d["spatial_level"] < finest_level]
        eligible_levels = []
        for level in levels:
            if level == finest_level:
                continue
            rows_at_level = [d for d in within if d["spatial_level"] == level]
            # A spatial level is accepted only if all time-step/metric comparisons
            # at that level are within tolerance.
            if rows_at_level and all(d["deviation_percent"] <= tolerance_percent for d in rows_at_level):
                eligible_levels.append(level)
        selected = min(eligible_levels) if eligible_levels else None
        passed = not errors and selected is not None and all(d["deviation_percent"] <= tolerance_percent for d in deviations)
        case_reports.append({
            "case_id": str(case_id), "passed": bool(passed), "spatial_levels": [float(x) for x in levels],
            "time_steps_ms_coarse_to_fine": [float(x) for x in timesteps], "finest_reference": {"spatial_level": float(finest_level), "dt_ms": float(finest_dt)},
            "selected_coarsest_level": float(selected) if selected is not None else None,
            "tolerance_percent": tolerance_percent, "max_deviation_percent": max((d["deviation_percent"] for d in deviations), default=0.0),
            "deviations": deviations, "errors": errors
        })
    passed = bool(case_reports) and all(c["passed"] for c in case_reports)
    return {
        "passed": passed, "decision_grade_eligible": False, "case_count": len(case_reports),
        "criteria": {"minimum_spatial_levels": 3, "minimum_time_steps": 2, "tolerance_percent": tolerance_percent},
        "cases": case_reports,
        "interpretation": "This evaluates supplied scalar metrics only. It does not prove mesh validity, solver correctness, or biological validity."
    }

def evaluate_file(path: str | Path, tolerance_percent: float = 5.0) -> dict[str, Any]:
    return evaluate_convergence(pd.read_csv(path), tolerance_percent=tolerance_percent)
