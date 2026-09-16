# Virelion-VB-204

**VB-204 — Computational Graft Integration & Risk Engine**

VB-204 is a discovery-stage program for an engineered, stem-cell-derived cardiomyocyte graft intended to restore lost myocardial mass. This repository implements the fully computational discovery workstream (WS-C1) that ranks candidate graft architectures by predicted arrhythmogenic risk and mechanical contribution **before any wet-lab tissue is fabricated**.

The work uses only public data, published large-animal/NHP graft studies, and open-source cardiac modeling software. No cells, grafts, animals, or wet-lab reagents are required to execute the pipeline described here.

> **Primary scientific question**  
> Which combination of (1) cardiomyocyte phenotype maturity axes, (2) tissue architecture, and (3) interface properties yields the lowest predicted arrhythmogenic risk while maximizing predicted mechanical contribution and electrical synchrony?

## Why this step exists

VB-204’s discovery roadmap includes an Integration risk model and an electrophysiology characterization workstream. Both currently rest on literature-derived qualitative judgments. This repository converts that qualitative risk register into quantitative, testable predictions, validates those predictions against real published outcomes, and hands off a minimal set of targeted first wet-lab experiments.

The result is architecture down-selection that is evidence-based rather than assumption-based, at zero animal cost.

## What this repository delivers

- A ranked architecture × phenotype matrix with quantitative, uncertainty-bounded risk scores
- Virtual arrhythmia risk maps (re-entry propensity, conduction delay, ectopic automaticity)
- A simulation pipeline that is **required to reproduce known outcomes** from five independent published large-animal/NHP graft studies before any novel ranking is treated as decision-grade
- Sensitivity and uncertainty analysis identifying the highest-leverage design parameters
- Go/no-go thresholds derived by structured expert elicitation and anchored to real experimental outcomes
- A minimal, targeted set of first wet-lab experiments that would most reduce residual uncertainty
- Fully open, reproducible simulation code and a complete parameter-provenance record

## Computational pipeline (Layers 0–4 + gate)

```text
Layer 0   Phenotype library (distributions, not point estimates)
                ↓
Layer 1   Tissue / graft geometry generator (Architectures A–D)
                ↓
Layer 2   Multiphysics electromechanical simulation (openCARP)
                ↓
Layer 2.5 Benchmark validation gate  ←  mandatory before design ranking
                ↓
Layer 3   Risk aggregation & decision layer (HeartTwin-compatible)
                ↓
Layer 4   Experimental prioritization (minimal wet-lab package)
```

**Layer 2.5 is a hard gate.** The pipeline is not used to rank novel VB-204 architectures until it correctly rank-orders the five named benchmark cases by relative arrhythmic risk (including placing the low-risk epicardial-patch case below the four high-risk cell-suspension cases).

### Benchmark case set (already identified)

| Study | Architecture | Role |
|-------|--------------|------|
| Chong et al., *Nature* 2014 | Cell suspension (A) | Positive / quantitative |
| Liu et al., *Nat Biotechnol* 2018 | Cell suspension (A) | Positive / mapping |
| Shiba et al., *Nature* 2016 | Cell suspension (A) | Positive / moderate |
| Romagnuolo et al., *Stem Cell Reports* 2019 | Cell suspension (A), porcine | Positive / host-matched |
| Jebran et al., *Nature* 2025 | Epicardial EHM patch (C) | Negative / architecture-matched |

### Candidate architectures

- **A** — Cell suspension  
- **B** — Matrix-supported microtissue  
- **C** — Epicardial engineered heart-muscle patch *(current lead strategic architecture)*  
- **D** — Composite mechanically reinforcing graft  

## Key technical foundations (public & citable)

| Component | Source |
|-----------|--------|
| hiPSC-CM ionic model | Kernik et al., *J Physiol* 2019 |
| Porcine host EP | Gaur et al., *PLoS Comput Biol* 2021 |
| Validated porcine MI geometries | Rosales et al., *PLOS Comput Biol* 2026 |
| Human translational check | Ten Tusscher & Panfilov, 2006 + Gaur translation method |
| Solver | openCARP (Plank et al., 2021) |
| Patch–host interaction framework | Fassina et al., *PLoS Comput Biol* 2022 / *Comput Biol Med* 2023 |
| Independent mechanism check | Gibbs et al., *J Physiol* 2023 |

## Execution timeline (≈18 weeks)

| Weeks | Focus | Critical path? |
|-------|-------|----------------|
| 1–2 | Acquire & adapt models + extract benchmark data | Yes |
| 3–6 | Implement Layer 2 + mesh-convergence / monodomain–bidomain validation | Yes |
| 7–9 | Layer 2.5 benchmark reproduction → go/no-go gate | Yes |
| 10–13 | Architecture × phenotype sweep (porcine host) | — |
| 14–15 | Human-substrate translational check | — |
| 16–17 | Uncertainty quantification + structured threshold elicitation | — |
| 18 | Package for experimental hand-off | — |

Nothing in the design-space sweep is treated as decision-grade until the Layer 2.5 gate is passed.

## Boundaries (locked)

- This work generates **predictions and prioritization only**, not efficacy or safety claims.
- All parameters remain literature- or public-data-derived until experimental calibration data exist.
- No gene-editing sequences, culture recipes, or release criteria are specified.
- Risk scores produced before the Layer 2.5 gate are provisional/exploratory and must not drive architecture down-selection or experimental resource allocation.
- The entire stack relies only on public, published data and open-source methodology. No proprietary third-party code or unpublished data is required to start.

## Repository structure

```text
Virelion-VB-204/
├── README.md
├── LICENSE
├── configs/                 # Architecture, phenotype, host, solver, threshold definitions
├── data/
│   ├── benchmarks/          # Quantitative extracts from the five named studies
│   ├── phenotypes/          # Kernik / CiPA distributions & provenance
│   ├── geometries/          # Host geometry manifests (Rosales et al.)
│   └── manifests/           # Dataset & parameter registries
├── docs/
│   ├── proposal/            # Full WS-C1 proposal & addenda
│   ├── layers/              # Layer-by-layer technical specifications
│   └── boundaries.md        # Locked scientific & regulatory guardrails
├── scripts/                 # Environment setup, benchmark runs, sweeps
├── src/vb204/               # Python package (phenotype → geometry → simulation → risk)
├── notebooks/               # Exploratory analysis & visualization
├── results/                 # Generated outputs (mostly gitignored)
└── workflows/               # Optional orchestration (Snakemake etc.)
```

## Relationship to Virelion platforms

VB-204 is one of Virelion Biotech’s therapeutic discovery programs. The risk-aggregation layer (Layer 3) is designed to be compatible with the VB-310 HeartTwin digital-heart-twin stack so that computational predictions can later be updated as real experimental data arrive.

## Getting started

1. Read `docs/boundaries.md` and the Layer 2.5 gate definition before treating any ranking as actionable.
2. Install the environment (see `scripts/setup_environment.sh` once populated).
3. Begin with Weeks 1–2: acquisition of the named public models and extraction of quantitative data from the five benchmark studies.

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later). See `LICENSE`.

---

*Discovery-stage concept. No experimental data are claimed. Statements about VB-204 itself are proposals and hypotheses unless explicitly marked otherwise.*
