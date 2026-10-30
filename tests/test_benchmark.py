import pandas as pd
from vb204.benchmark import evaluate_benchmark

def benchmark_frame():
    return pd.DataFrame([
        {"study":"Chong et al. 2014","architecture":"A","observed_class":"high","predicted_risk":.9,"source":"https://doi.org/10.1038/nature13235","observed_endpoint":"arrhythmia burden","notes":"test fixture only"},
        {"study":"Liu et al. 2018","architecture":"A","observed_class":"high","predicted_risk":.8,"source":"https://doi.org/10.1038/nbt.4162","observed_endpoint":"arrhythmia mapping","notes":"test fixture only"},
        {"study":"Shiba et al. 2016","architecture":"A","observed_class":"moderate","predicted_risk":.6,"source":"https://doi.org/10.1038/nature19815","observed_endpoint":"VT incidence","notes":"test fixture only"},
        {"study":"Romagnuolo et al. 2019","architecture":"A","observed_class":"high","predicted_risk":.7,"source":"https://doi.org/10.1016/j.stemcr.2019.04.012","observed_endpoint":"tachyarrhythmias","notes":"test fixture only"},
        {"study":"Jebran et al. 2025","architecture":"C","observed_class":"low","predicted_risk":.2,"source":"https://doi.org/10.1038/s41586-024-08463-0","observed_endpoint":"patch outcome","notes":"test fixture only"},
    ])

def test_ordinal_benchmark_gate_passes_good_test_fixture():
    result = evaluate_benchmark(benchmark_frame())
    assert result["passed"]
    assert result["decision_grade_eligible"] is False

def test_benchmark_gate_fails_wrong_order():
    frame = benchmark_frame()
    frame.loc[frame.study == "Jebran et al. 2025", "predicted_risk"] = .95
    result = evaluate_benchmark(frame)
    assert not result["passed"]
    assert not result["checks"]["predicted_ordinal_risk_order_matches_labels"]

def test_missing_study_fails():
    result = evaluate_benchmark(benchmark_frame().iloc[:-1])
    assert not result["passed"]
    assert not result["checks"]["exactly_five_unique_named_cases"]
