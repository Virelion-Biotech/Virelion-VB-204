# VB-204 execution and validation guide

The package operationalizes the supplied discovery-toolkit plan and computational proposal. It includes planning reports, risk/architecture decision logic, expression-scorecard utilities, explicit public-asset retrieval, solver-run orchestration, convergence checks, ordinal benchmark checks and a fail-closed validation checklist.

## Install

    python -m pip install -e ".[dev]"
    pytest -q
    vb204 plan --out outputs/vb204-plan.md
    vb204 plan --json --out outputs/vb204-plan.json

The same commands work through python -m vb204.

## Layer 0 — phenotype and provenance

Use a pre-normalized expression matrix with genes in rows and biological samples in columns:

    vb204 maturity expression_matrix.csv --out results/maturity_scorecard.json

The score is a relative, within-matrix z-score aggregation. It is not an absolute maturation scale, an independently validated biomarker, or a release criterion. Record data source, normalization, species, cell line, differentiation day, replicate and processing version alongside the input.

## Layer 1 — geometry and external model assets

The proposal identifies the Rosales et al. 2026 modeling software and datasets. Current source links are recorded in src/vb204/assets/public_assets.json. The article's data-availability statement names HeartModelling, simOmPP and ELECTRA and Zenodo records 17415592 and 17435811. Do not assume the paper's ELECTRA meshes or configs run unchanged in openCARP.

Inspect record metadata without downloading:

    vb204 assets --record all --out results/asset_inventory.json

Download only an explicitly selected filename after reviewing the record and license:

    vb204 assets --record 17415592 --download-file FILENAME --accept-license --download-dir data/external

The geometry command validates an explicit parameter spec, but does not generate anatomical geometry or invent parameter values. Use reviewed host geometry assets and a compatible meshing pipeline. Keep source citation, license, species, units and SHA-256 for all assets.

## Layer 2 — solver run

Copy examples/run_manifest_template.json to a case-specific file. Set absolute paths for the parameter/configuration file and input meshes, set the source URL and asset license_status to verified only after reviewing the actual asset conditions, and record model ID, species and solver version. Then:

    vb204 simulate case_manifest.json --out-dir results/case_001

openCARP uses its documented +F parameter-file invocation. ELECTRA requires a version-specific command array because the Rosales solver is not assumed to share openCARP's CLI. Commands are executed as argument arrays (not shell strings); stdout, stderr, hashes and run metadata are archived. A successful process exit is not a scientifically validated simulation. Solver input configs, mesh labels, fiber fields, tissue parameters and boundary conditions still require review.

## Mesh/time-step convergence

Create a CSV with columns case_id, spatial_level, dt_ms, metric, value and unit; include at least 3 spatial levels and 2 timestep sizes for every case and every reported metric. Values must be actual post-processed solver outputs, not test examples.

    vb204 convergence convergence_metrics.csv --tolerance-percent 5 --out results/convergence_report.json

Each reported metric is compared to the finest-spatial-resolution / smallest-time-step reference. A convergence pass is necessary, not sufficient, for model validity. The proposal requires a monodomain-versus-bidomain comparison on at least one benchmark case; that is an additional independent gate.

## Layer 2.5 — five published benchmarks

Fill examples/benchmark_template.csv with exact study labels, case architecture, observed outcome class, model-predicted scalar on a common documented scale, source URL and extracted endpoint notes. Expected classes are pre-registered from the supplied proposal. The gate checks the expected ordinal ordering; it intentionally does not compare unlike endpoint units across papers or pretend that ordinal agreement is a quantitative reproduction.

    vb204 benchmark examples/benchmark_filled.csv --out results/benchmark_gate.json

A passing ordinal check alone cannot unlock decision-grade ranking. Extract and harmonize study-specific endpoints, reproduce the numerical/physiological observations where possible, document uncertainty and have results independently reviewed.

## Layer 3 — scoring and evidence gates

Candidate summaries can be scored with:

    vb204 score candidates.csv --gate-report results/validation_gates.json --out results/architecture_scores.csv

Candidate metrics must have documented definitions and be scaled to [0,1]. Weights are stated in the code and must be reviewed. The score is relative to the set of candidates included and is not a calibrated probability. The gate report must mark every required gate passed and include evidence URI plus reviewer. Use examples/validation_gates_template.json as a starting point; it is intentionally all pending.

Required gates: phenotype data provenance; geometry/mesh validation; mesh/time-step convergence; mono-/bidomain check; five-case benchmark reproduction; mechanics validation; cross-species check; uncertainty/OOD review; expert threshold review. The checklist records evidence/sign-off but is not itself a truth oracle.

## Sweep preparation and Layer 4

Supply a JSON list of host cases with real mesh paths, species, source URL and reviewed license status. Phenotype IDs should refer to frozen, provenance-bearing phenotype distributions.

    vb204 sweep --hosts hosts.json --phenotypes phenotype_01,phenotype_02 --architectures A,B,C,D --out results/sweep_manifest.json

This builds a case matrix only. It does not generate meshes, solve the PDEs or fabricate results. The next required implementation is to build and validate architecture-specific geometry adapters and post-process solver outputs into a versioned metrics schema. Sensitivity analysis should then be run on actual results; no experimental prioritization should be inferred from the placeholder scorecards.

## 18-week critical path from the proposal

- Weeks 1–2: source and version phenotype models, porcine geometries, solver packages, and benchmark endpoints.
- Weeks 3–6: adapt the host/graft model, then demonstrate >=3 mesh resolutions, >=2 time steps and mono-/bidomain agreement.
- Weeks 7–9: reproduce the five benchmark cases and document the gate decision.
- Weeks 10–13: run the architecture × phenotype × porcine-host sweep only after benchmark acceptance.
- Weeks 14–15: human-substrate translation check and explicit ranking-change flags.
- Weeks 16–17: uncertainty/OOD analysis and expert threshold review.
- Week 18: evidence package and recommended minimum follow-up measurements.

No ranking should guide architecture down-selection before the benchmark and all other required validation gates pass. The toolkit contains no gene-editing sequences, culture recipes, cell doses, release thresholds, surgical instructions, or clinical recommendations.
