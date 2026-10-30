# VB-204 executable scaffold

This package adds a reproducible exploratory scoring layer and a strict input gate. It does not yet implement cardiac electrophysiology or electromechanical solvers and is not a validated arrhythmia predictor.

## Install and test

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[dev]'
pytest -q
```

## Score candidates

Populate `examples/candidates_template.csv` with documented estimates and standard deviations scaled to [0, 1]. Explain the source and meaning of every metric in a study-specific data dictionary.

```bash
vb204 score candidates.csv --output results/architecture_scores.csv --draws 10000 --seed 204
```

Unless a passing benchmark-gate JSON is explicitly supplied, scores are marked `EXPLORATORY_GATE_BLOCKED`. Min-max scaling is candidate-set-dependent and outputs are not calibrated probabilities.

## Run the five-study gate

Extract comparable, sourced numeric endpoints into a copy of `examples/benchmark_template.csv`; do not guess missing values.

```bash
vb204 benchmark benchmark_extracted.csv --output results/benchmark_gate.json
vb204 score candidates.csv --gate-report results/benchmark_gate.json
```

The gate requires the five pre-specified studies, provenance and endpoint units, four cell-suspension cases A and one epicardial patch case C, and checks the proposed qualitative order that C has lower observed risk than each A case. If endpoints are not comparable across studies, do not combine them; harmonize and justify the endpoint first.

Passing this input/order gate does not validate a solver or establish biological generalization, safety, or clinical validity. Synthetic test fixtures are not scientific inputs.

## Implemented

- Candidate-table validation and missing-data rejection
- Seeded Monte Carlo propagation of supplied mean/SD estimates
- Relative trade-off score and rank uncertainty
- Fail-closed benchmark completeness/order gate
- CLI and regression tests

## Still required

- Phenotype distributions derived from source datasets
- Graft/host mesh construction and convergence checks
- openCARP or another electrophysiology solver adapter
- Electromechanical coupling
- Extraction/harmonization of source-study outcomes
- Independent numerical reproduction of the five studies
- Expert-elicited decision thresholds

No ranking is decision-grade until those gates are completed and independently reviewed.
