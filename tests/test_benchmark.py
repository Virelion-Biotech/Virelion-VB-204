import pandas as pd
from vb204.benchmark import evaluate_benchmark

def fixture(patch=.1):
    studies=["Chong et al. 2014","Liu et al. 2018","Shiba et al. 2016","Romagnuolo et al. 2019","Jebran et al. 2025"]
    return pd.DataFrame([{"study":s,"architecture":"C" if s.startswith("Jebran") else "A",
      "observed_risk":patch if s.startswith("Jebran") else .5,
      "source":"https://example.org/test-fixture-not-evidence","unit":"synthetic test units",
      "notes":"Synthetic software-test fixture only"} for s in studies])

def test_gate_passes_for_complete_ordered_fixture():
    report=evaluate_benchmark(fixture())
    assert report.passed
    assert report.checks["all_named_studies_present"]

def test_gate_fails_when_patch_not_lower():
    report=evaluate_benchmark(fixture(.5))
    assert not report.passed
    assert not report.checks["patch_below_all_suspension_cases"]

def test_missing_study_fails():
    report=evaluate_benchmark(fixture().iloc[:-1])
    assert not report.passed
    assert not report.checks["exactly_five_unique_studies"]
