"""Transparent, uncertainty-aware exploratory architecture scoring.

This is research scaffolding, not a validated arrhythmia model. Inputs must
come from documented evidence or explicitly labeled simulation outputs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {
    "architecture", "arrhythmia_risk_mean", "arrhythmia_risk_sd",
    "mechanical_contribution_mean", "mechanical_contribution_sd",
    "synchrony_mean", "synchrony_sd",
}
DEFAULT_WEIGHTS = {
    "arrhythmia_risk": 0.50,
    "mechanical_contribution": 0.25,
    "synchrony": 0.25,
}


@dataclass(frozen=True)
class ScoreSettings:
    weights: dict[str, float]
    draws: int = 10_000
    seed: int = 204

    def __post_init__(self) -> None:
        if self.draws < 100:
            raise ValueError("draws must be >= 100")
        if set(self.weights) != set(DEFAULT_WEIGHTS):
            raise ValueError(f"weights must contain exactly {sorted(DEFAULT_WEIGHTS)}")
        if any(not np.isfinite(v) or v < 0 for v in self.weights.values()):
            raise ValueError("weights must be finite and non-negative")
        if not np.isclose(sum(self.weights.values()), 1.0):
            raise ValueError("weights must sum to 1.0")


def validate_candidates(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate candidate summaries without imputing missing evidence."""
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")
    data = frame.copy()
    if data.empty:
        raise ValueError("candidate table is empty")
    if data["architecture"].isna().any() or data["architecture"].astype(str).str.strip().eq("").any():
        raise ValueError("architecture identifiers must be non-empty")
    if data["architecture"].duplicated().any():
        raise ValueError("architecture identifiers must be unique")
    numeric = sorted(REQUIRED_COLUMNS - {"architecture"})
    for col in numeric:
        data[col] = pd.to_numeric(data[col], errors="raise")
        if not np.isfinite(data[col].to_numpy(dtype=float)).all():
            raise ValueError(f"{col} contains non-finite values")
    for col in (c for c in numeric if c.endswith("_sd")):
        if (data[col] < 0).any():
            raise ValueError(f"{col} must be non-negative")
    for col in ("arrhythmia_risk_mean", "mechanical_contribution_mean", "synchrony_mean"):
        if ((data[col] < 0) | (data[col] > 1)).any():
            raise ValueError(f"{col} must be scaled to [0, 1]")
    return data


def _minmax(values: np.ndarray) -> np.ndarray:
    low, high = float(np.min(values)), float(np.max(values))
    return np.full(values.shape, 0.5) if np.isclose(low, high) else (values - low) / (high - low)


def score_architectures(
    candidates: pd.DataFrame,
    *,
    settings: ScoreSettings | None = None,
    benchmark_gate_passed: bool = False,
) -> pd.DataFrame:
    """Score relative trade-offs and report Monte Carlo rank uncertainty.

    The score is candidate-set-dependent, not a calibrated probability. Unless
    the benchmark gate passes, outputs remain blocked for design decisions.
    """
    data = validate_candidates(candidates)
    settings = settings or ScoreSettings(weights=DEFAULT_WEIGHTS.copy())
    rng = np.random.default_rng(settings.seed)
    w = settings.weights

    risk = _minmax(data["arrhythmia_risk_mean"].to_numpy(float))
    mechanics = _minmax(data["mechanical_contribution_mean"].to_numpy(float))
    synchrony = _minmax(data["synchrony_mean"].to_numpy(float))
    point_score = w["arrhythmia_risk"] * (1 - risk) + w["mechanical_contribution"] * mechanics + w["synchrony"] * synchrony

    draws_by_metric: dict[str, np.ndarray] = {}
    for metric in ("arrhythmia_risk", "mechanical_contribution", "synchrony"):
        means = data[f"{metric}_mean"].to_numpy(float)
        sds = data[f"{metric}_sd"].to_numpy(float)
        draws = np.clip(rng.normal(means, sds, size=(settings.draws, len(data))), 0, 1)
        draws_by_metric[metric] = np.apply_along_axis(_minmax, 1, draws)

    scores = (
        w["arrhythmia_risk"] * (1 - draws_by_metric["arrhythmia_risk"])
        + w["mechanical_contribution"] * draws_by_metric["mechanical_contribution"]
        + w["synchrony"] * draws_by_metric["synchrony"]
    )
    ranks = np.argsort(np.argsort(-scores, axis=1), axis=1) + 1
    result = pd.DataFrame({
        "architecture": data["architecture"].astype(str),
        "exploratory_score": point_score,
        "score_ci_2_5": np.quantile(scores, 0.025, axis=0),
        "score_ci_97_5": np.quantile(scores, 0.975, axis=0),
        "probability_rank_1": (ranks == 1).mean(axis=0),
        "median_rank": np.median(ranks, axis=0),
        "benchmark_gate_passed": bool(benchmark_gate_passed),
        "decision_status": "eligible_for_review" if benchmark_gate_passed else "EXPLORATORY_GATE_BLOCKED",
    })
    return result.sort_values(["exploratory_score", "architecture"], ascending=[False, True]).reset_index(drop=True)
