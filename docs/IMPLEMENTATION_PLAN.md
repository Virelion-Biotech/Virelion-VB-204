# VB-204 implementation plan derived from supplied sources

This plan combines the uploaded VB-204 Discovery Toolkit PLAN.md/VALIDATION.md and the VB-204 Computational Graft Integration & Risk Engine proposal.

## Working assumptions preserved from the toolkit

- Lead strategic architecture C (epicardial EHM patch), backup B (matrix-supported microtissue); A and D remain comparators.
- The default decision call is HOLD until every GO criterion is supported by evidence and no NO-GO criterion is triggered.
- Architecture scores and risk-register ratings are qualitative/illustrative until replaced with reviewed comparative data.
- A gene-expression scorecard is relative and must not be treated as a release test.
- Wet-lab-only workstreams remain human/partner responsibilities, not fabricated outputs from code.

## Proposal-specific computational path

Layer 0: phenotype marker panels and sourced distributions.
Layer 1: A–D architecture parameterization and compatible host geometry.
Layer 2: solver execution, electromechanics, mesh/time-step convergence and model comparison.
Layer 2.5: five-study ordinal and study-specific quantitative benchmark reproduction.
Layer 3: uncertainty-aware risk aggregation, cross-species/OOD checks and versioned expert thresholds.
Layer 4: prioritize additional measurements by expected information gain and residual uncertainty.

## Critical path and gates

1. Acquire and cite source data/models; verify licensing and SHA-256.
2. Validate the phenotype panel against actual public, appropriately preprocessed expression data.
3. Validate source anatomy, tissue labels, fiber field, mesh quality and solver input compatibility.
4. Demonstrate three spatial resolutions, two timestep sizes, and <=5% convergence band on each declared metric; compare monodomain with bidomain on a benchmark case.
5. Run all five benchmark cases with study-specific endpoint extraction and preregistered expected labels.
6. Only after independent review of those results should a design sweep be treated as decision-grade.
7. Compare leading designs on the human substrate and record ranking changes.
8. Carry uncertainty and out-of-distribution indicators through the final report; set thresholds only with documented expert elicitation.

## What is executable now

- Planning/risk/architecture decision reports.
- Relative expression scorecard implementation.
- Source inventory and explicitly selected Zenodo file downloads.
- Solver invocation wrapper when compatible case manifests, meshes, parameter files and binaries are present.
- Convergence calculations from supplied solver metrics.
- Benchmark ordinal check and evidence-signoff registry.
- Monte Carlo exploratory scoring and sweep-manifest generation.

## What is not claimed complete

This repository does not yet contain a validated electrophysiology or mechanics solver implementation, original public datasets/meshes, extracted benchmark outcome measurements, geometry generation for each architecture, validated electromechanics coupling, empirical parameter calibration, expert threshold decisions or proof of biological generalization. These are scientific work packages, not documentation bugs. All numerical outputs must preserve the provenance and validation state of their inputs.
