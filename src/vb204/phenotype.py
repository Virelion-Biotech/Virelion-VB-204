"""Relative multi-axis hPSC-CM expression scorecard; not a release test."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import yaml
from .plan import ASSET_DIR

def load_expression(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, index_col=0)
    if frame.empty or frame.shape[1] < 2:
        raise ValueError("Expression matrix must contain genes as rows and at least two samples as columns")
    if frame.index.has_duplicates:
        raise ValueError("Gene symbols must be unique; aggregate duplicate genes before scoring")
    frame.index = frame.index.astype(str).str.strip().str.upper()
    if (frame.index == "").any():
        raise ValueError("Gene symbols cannot be empty")
    frame = frame.apply(pd.to_numeric, errors="raise")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("Expression matrix contains missing or non-finite values")
    return frame

def _zscore_rows(frame: pd.DataFrame) -> pd.DataFrame:
    means = frame.mean(axis=1)
    std = frame.std(axis=1, ddof=0).replace(0, np.nan)
    return frame.sub(means, axis=0).div(std, axis=0).fillna(0.0)

def score_maturity(expression: pd.DataFrame) -> dict[str, Any]:
    with (ASSET_DIR / "maturity_markers.yaml").open(encoding="utf-8") as handle:
        panel = yaml.safe_load(handle)
    z = _zscore_rows(expression)
    axes = {}
    used_genes: set[str] = set()
    for axis_id, spec in panel["axes"].items():
        up = [g for g in spec.get("up", []) if g in z.index]
        down = [g for g in spec.get("down", []) if g in z.index]
        genes = up + down
        if not genes:
            axes[axis_id] = {"description": spec["description"], "scores": {}, "genes_used": [], "status": "MISSING_MARKERS"}
            continue
        signed = []
        if up:
            signed.append(z.loc[up].mean(axis=0))
        if down:
            signed.append(-z.loc[down].mean(axis=0))
        scores = pd.concat(signed, axis=1).mean(axis=1)
        axes[axis_id] = {
            "description": spec["description"], "scores": {str(k): round(float(v), 4) for k, v in scores.items()},
            "genes_used": genes, "status": "RELATIVE_SCORE_ONLY", "sources": spec.get("sources", [])
        }
        used_genes.update(genes)
    if not used_genes:
        raise ValueError("None of the maturity-panel genes occur in the expression matrix")
    safety = {}
    for group, genes in panel.get("safety_flags", {}).items():
        present = [g for g in genes if g in expression.index]
        safety[group] = {
            "genes_present": present,
            "expression": {gene: {str(s): float(expression.loc[gene, s]) for s in expression.columns} for gene in present},
            "relative_z_scores": {gene: {str(s): round(float(v), 4) for s, v in z.loc[gene].items()} for gene in present},
            "interpretation": "Flag for review only; no fixed threshold or release decision."
        }
    axis_series = []
    for axis_id, details in axes.items():
        if details["scores"]:
            axis_series.append(pd.Series(details["scores"], name=axis_id))
    composite = pd.concat(axis_series, axis=1).mean(axis=1).sort_values(ascending=False) if axis_series else pd.Series(dtype=float)
    return {
        "status": "RELATIVE_RESEARCH_SCORECARD_NOT_VALIDATED_FOR_RELEASE",
        "normalization_assumption": "Input values should be pre-normalized; normalization is not performed here.",
        "axes": axes,
        "composite_relative_index": {str(k): round(float(v), 4) for k, v in composite.items()},
        "safety_flags": safety,
        "missing_panel_genes": sorted({g for sp in panel["axes"].values() for g in sp.get("up", []) + sp.get("down", [])} - set(expression.index)),
        "interpretation": "Scores compare samples in this input matrix only. A synthetic example or relative z-score is not evidence of biological maturity."
    }
