# VB-204 independent software/scientific integrity audit

Audit scope: repository code and configuration on the implementation line, with hardening changes in feat/vb204-audit-hardening. This is a source review plus regression-test additions; it is not a claim that every external solver or model has been executed.

## Findings fixed in this change

### P1 — external asset downloads did not verify the record checksum
Before this change the download path recorded a SHA-256 hash but did not compare downloaded bytes against the Zenodo checksum or declared byte size. A truncated or corrupted file could be retained as if the download completed. Downloads now enforce a default 10 GiB cap, check HTTPS Zenodo origin, verify declared size and supported md5/sha256 checksums, write to a temporary file, fsync and atomically publish only after validation, and remove partial files on failure. Existing destinations are not overwritten.

### P1 — gene identifiers could collide after normalization
The expression loader checked duplicate symbols before uppercasing and trimming. tnni3 and TNNI3 could therefore become duplicate index entries after the check. It now normalizes first and rejects duplicates afterward; sample IDs are checked too. Direct score calls also reject empty/undersized or non-finite inputs.

### P1 — ranking ties were broken arbitrarily
The Monte Carlo rank calculation used a double argsort, which assigns different ranks to exact ties based on row position. Average ranks now preserve ties, preventing false winner probabilities for equal candidates. Candidate IDs are normalized before duplicate checks, and ScoreSettings rejects booleans as integer draw counts.

## Important remaining risks (not all addressed by this patch)

1. Benchmark validity is not empirical replication. The current Layer 2.5 gate checks that five records match the protocol's expected labels and that predictions order those labels. It does not calculate study-specific endpoint effect sizes, uncertainty, or independent reproduction. A pass must remain an ordinal protocol-concordance check only.
2. Scoring is relative to the candidate set. Min-max scaling means scores change when candidates are added/removed; SDs are treated as independent normal perturbations and clipped to [0,1]. No empirical calibration, covariance model, external validation, or clinically meaningful risk probability exists.
3. Gate attestations are not cryptographically authenticated. A JSON report can be manually authored. Reviewer fields and URLs are metadata, not proof of independence or correctness. Decision-grade eligibility therefore stays hard-coded false.
4. Solver execution is a process wrapper, not a validated solver adapter. The runner records process status and hashes, but does not validate physics, mesh labels, fiber orientation, boundary conditions, output schema, convergence or scientific plausibility. Arbitrary command arrays must be treated as trusted local configuration.
5. Timeout/output handling needs further hardening. Current subprocess output capture is in-memory; a solver producing enormous logs can exhaust memory. Timeout logs and child-process cleanup need dedicated integration tests.
6. Phenotype scoring is descriptive only. Per-gene z-scores are calculated across samples in the supplied matrix, so values are cohort-relative and sensitive to sample composition. The marker panel and directionality require external biological review.
7. Geometry schema is not geometry generation. Parametric checks do not establish that an anatomical mesh exists, is valid, or is solver-compatible.
8. Roadmap status is calendar-derived. A passed date window is not evidence that a deliverable was completed; output must not be interpreted as progress tracking.
9. Reproducibility metadata is incomplete. Full environment lockfiles, input dataset fingerprints, solver version probes, and standardized output metric schemas remain to be added.
10. No full external solver run is claimed. Current CI validates Python package/tests/lint, not openCARP/ELECTRA installation, physiological behavior, or quantitative reproduction of the five studies.

## Next audit tranche

- Replace in-memory subprocess capture with streamed log files, terminate process groups on timeout, and atomically finalize run manifests.
- Add property-based and mutation tests for schema validation, benchmark gates, convergence grids, and malformed metadata.
- Separate protocol label concordance from evidence-backed empirical benchmark acceptance in names, output schema, and CLI exit semantics.
- Add source dataset manifests with version, accession, licence, subject/sample units, processing code hash, and raw-to-derived lineage.
- Add a machine-readable run-output contract and validate solver outputs before downstream scoring.
- Add pinned CI dependencies, coverage reporting, security scanning and package build/install smoke tests.
- Independently review the marker panel, five study endpoint extractions, model assumptions, and architecture weights.

## Decision

The package is useful as planning, data-integrity and orchestration scaffolding. It is not yet a scientifically validated graft-integration predictor. The code should remain exploratory and must not be used to claim arrhythmia safety, graft efficacy, or clinical readiness.
