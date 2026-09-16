# Layer 2.5 — Benchmark Validation Gate

**Purpose:** Establish that the solver reproduces known qualitative and quantitative outcomes before its rankings on untested architectures are treated as decision-grade.

This is a **hard gate**. Nothing in the design-space sweep (Layers 3–4) is decision-grade until this gate is passed.

## Requirements

1. Reconstruct each of the five named benchmark cases (see `data/manifests/benchmark_registry.yaml`) as closely as the publications allow within the Layer 0/1 parameter framework.
2. Run the Layer 2 pipeline unmodified on each case.
3. Primary pass criterion: correct rank-ordering of relative arrhythmic risk (all four positive cases above the Jebran et al. negative case).
4. Secondary criterion: point-estimate error on conduction velocity / APD / arrhythmia burden where numeric ground truth exists.
5. Document every parameter gap filled by assumption — these become explicit calibration uncertainty.

## Failure mode

If the pipeline fails the rank-order test, the failure is diagnostic. Trace it to a specific layer (phenotype parameterization, geometry representation, or solver physics) before proceeding. Do not proceed to novel-architecture ranking.

## Independent mechanism check

Gibbs et al., *J Physiol* 2023 provides an independent computational reproduction of the engraftment-arrhythmia mechanism underlying Chong/Liu. Use it as a second check that Layer 2 recovers the correct mechanism, not merely the correct incidence ranking.
