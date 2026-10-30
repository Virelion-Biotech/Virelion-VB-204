"""Evidence completeness and relative-order benchmark gate for VB-204."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd

REQUIRED_CASES = {"Chong et al. 2014", "Liu et al. 2018", "Shiba et al. 2016", "Romagnuolo et al. 2019", "Jebran et al. 2025"}
REQUIRED_COLUMNS = {"study", "architecture", "observed_risk", "source", "unit", "notes"}

@dataclass(frozen=True)
class GateReport:
    passed: bool
    checks: dict[str, bool]
    errors: list[str]
    case_count: int
    statement: str = ("This gate checks data completeness and a pre-specified qualitative relative-order condition only; "
                      "it does not validate a solver or establish biological, clinical, or regulatory validity.")
    def to_dict(self) -> dict:
        return asdict(self)

def evaluate_benchmark(frame: pd.DataFrame) -> GateReport:
    """Require five named studies and lower measured risk for patch C than each A case."""
    errors: list[str] = []
    checks: dict[str, bool] = {}
    missing = REQUIRED_COLUMNS - set(frame.columns)
    checks["required_columns_present"] = not missing
    if missing:
        errors.append("Missing columns: " + ", ".join(sorted(missing)))
        return GateReport(False, checks, errors, len(frame))
    data = frame.copy()
    data["study"] = data["study"].astype(str).str.strip()
    data["architecture"] = data["architecture"].astype(str).str.strip().str.upper()
    checks["exactly_five_unique_studies"] = len(data) == 5 and data["study"].nunique() == 5
    if not checks["exactly_five_unique_studies"]:
        errors.append("Expected exactly five rows, one per independent benchmark study.")
    missing_studies = REQUIRED_CASES - set(data["study"])
    checks["all_named_studies_present"] = not missing_studies
    if missing_studies:
        errors.append("Missing studies: " + ", ".join(sorted(missing_studies)))
    try:
        data["observed_risk"] = pd.to_numeric(data["observed_risk"], errors="raise")
        numeric_ok = bool(np.isfinite(data["observed_risk"].to_numpy(float)).all())
    except (ValueError, TypeError):
        numeric_ok = False
    checks["observed_risk_is_finite_numeric"] = numeric_ok
    if not numeric_ok:
        errors.append("observed_risk must be finite numeric data; no imputation is performed.")
    provenance_ok = all(str(v).strip() and str(v).strip().lower() not in {"nan", "none", "unknown"}
                        for col in ("source", "unit") for v in data[col])
    checks["source_and_unit_documented"] = provenance_ok
    if not provenance_ok:
        errors.append("Every row needs a concrete source and a comparable endpoint unit.")
    architecture_ok = (data["architecture"] == "A").sum() == 4 and (data["architecture"] == "C").sum() == 1
    checks["architecture_mapping_matches_protocol"] = bool(architecture_ok)
    if not architecture_ok:
        errors.append("Expected four suspension cases labelled A and one patch case labelled C.")
    if numeric_ok and architecture_ok and len(data) == 5:
        patch_risk = float(data.loc[data["architecture"] == "C", "observed_risk"].iloc[0])
        order_ok = bool(np.all(patch_risk < data.loc[data["architecture"] == "A", "observed_risk"].to_numpy(float)))
    else:
        order_ok = False
    checks["patch_below_all_suspension_cases"] = order_ok
    if not order_ok:
        errors.append("Patch C must have lower comparable observed risk than each suspension A case.")
    return GateReport(all(checks.values()), checks, errors, len(data))
