# VB-204 — Computational Graft Integration & Risk Engine

VB-204 is a discovery-stage computational program for comparing engineered cardiomyocyte-graft architectures before any wet-lab tissue is fabricated. This repository now combines the supplied VB-204 Discovery Toolkit decision logic with executable analysis utilities and a fail-closed orchestration layer aligned to the uploaded 18-week computational proposal.

## Run it

    python -m pip install -e ".[dev]"
    pytest -q
    python -m vb204 plan
    python -m vb204 plan --json --out outputs/vb204-plan.json
    python -m vb204 risks --out outputs/risks.json
    python -m vb204 architectures
    python -m vb204 gonogo
    python -m vb204 maturity expression_matrix.csv
    python -m vb204 assets --record all
    python -m vb204 convergence convergence_metrics.csv
    python -m vb204 benchmark benchmark_filled.csv
    python -m vb204 gates examples/validation_gates_template.json

The CLI also supports candidate scoring, sweep-manifest preparation, parametric geometry-spec validation and explicit solver execution. See docs/EXECUTION.md for the full workflow and file contracts.

## Included executable layers

- **Layer 0:** literature-derived maturity axes and a relative expression-scorecard framework.
- **Layer 1:** A–D parametric geometry specification validation, host-case manifest preparation, source/license/hash tracking, and explicitly selected public asset retrieval.
- **Layer 2:** solver execution wrapper for real case manifests; convergence analysis requires real postprocessed numerical outputs.
- **Layer 2.5:** five-case benchmark ordinal gate, designed not to compare unlike published endpoint units as if they were identical.
- **Layer 3:** uncertainty-aware relative scoring, risk register, GO/NO-GO tracking, and mandatory validation-gate checklist.
- **Layer 4:** roadmap/report scaffolding and explicit residual evidence gaps for measurement prioritization.

## Scientific status

The tests check software behavior, not the truth of the biological assumptions. Architecture scores and RPNs are planning judgments. The expression scorecard is relative and not validated for release. A passing ordinal benchmark check is not quantitative reproduction. The solver wrapper can invoke a configured binary but does not create a valid ventricular mesh, validate constitutive models, or prove solver correctness.

No novel architecture ranking is decision-grade until provenance, mesh/anatomy validation, convergence, mono-/bidomain comparison, all five benchmark reproductions, mechanics validation, cross-species transfer, uncertainty/OOD and independent expert-review gates are documented as passed. See docs/IMPLEMENTATION_PLAN.md and docs/EXECUTION.md.

## Solver/data compatibility note

The 2026 Rosales et al. article's data-availability statement names HeartModelling, simOmPP and ELECTRA and provides Zenodo data records 17415592 and 17435811. Those model files must not be assumed compatible with openCARP without a verified adapter. Links and provenance hooks live in src/vb204/assets/public_assets.json.

## Boundaries

This repository supports research planning and computational prioritization only. It does not contain gene-editing sequences, culture recipes, release thresholds, cell doses, surgical/implantation instructions or clinical recommendations.

License: GPL-3.0-or-later.
