import pandas as pd
import pytest
from vb204.scoring import ScoreSettings, score_architectures, validate_candidates

def candidates():
    return pd.DataFrame([
        {"architecture":"A","arrhythmia_risk_mean":.8,"arrhythmia_risk_sd":.05,"mechanical_contribution_mean":.4,"mechanical_contribution_sd":.05,"synchrony_mean":.3,"synchrony_sd":.05},
        {"architecture":"C","arrhythmia_risk_mean":.2,"arrhythmia_risk_sd":.03,"mechanical_contribution_mean":.8,"mechanical_contribution_sd":.04,"synchrony_mean":.9,"synchrony_sd":.02},
    ])

def settings():
    return ScoreSettings(weights={"arrhythmia_risk":.5,"mechanical_contribution":.25,"synchrony":.25},draws=500,seed=4)

def test_score_deterministic_and_gate_blocks_decisions():
    a, b = score_architectures(candidates(), settings=settings()), score_architectures(candidates(), settings=settings())
    pd.testing.assert_frame_equal(a,b)
    assert set(a.decision_status) == {"EXPLORATORY_GATE_BLOCKED"}
    assert a.iloc[0].architecture == "C"

def test_invalid_scale_rejected():
    frame=candidates(); frame.loc[0,"arrhythmia_risk_mean"]=1.1
    with pytest.raises(ValueError,match=r"\[0, 1\]"): validate_candidates(frame)

def test_negative_sd_rejected():
    frame=candidates(); frame.loc[0,"synchrony_sd"]=-.1
    with pytest.raises(ValueError,match="non-negative"): validate_candidates(frame)

def test_duplicate_architectures_rejected():
    frame=candidates(); frame.loc[1,"architecture"]="A"
    with pytest.raises(ValueError,match="unique"): validate_candidates(frame)
