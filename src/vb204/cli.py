"""Command line for VB-204 planning, data gates and solver orchestration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from .acquisition import download_record_file, record_inventory
from .benchmark import evaluate_benchmark
from .convergence import evaluate_file
from .gates import evaluate_gate_file, validate_gate_report
from .geometry import validate_geometry_spec
from .phenotype import load_expression, score_maturity
from .plan import architecture_scores, evaluate_go_no_go, render_report, report_data, risk_scores
from .scoring import DEFAULT_WEIGHTS, ScoreSettings, score_architectures
from .simulation import prepare_sweep, run_simulation


def _write(data, path: str | None, markdown: bool = False) -> None:
    text = data if markdown and isinstance(data, str) else json.dumps(data, indent=2, default=str)
    if path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {target}")
    else:
        print(text)


def _add_output(parser: argparse.ArgumentParser, default: str | None = None) -> None:
    parser.add_argument("--out", "--output", dest="out", default=default, help="Output file (JSON unless command says otherwise)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vb204", description="VB-204 discovery planning and computational pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="Generate the program report and 12-month/18-week plans")
    p.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    _add_output(p)
    p = sub.add_parser("architectures", help="Show illustrative architecture matrix")
    p.add_argument("--weights", help="Comma-separated axis=weight pairs; all axes required")
    _add_output(p)
    p = sub.add_parser("risks", help="Rank the risk register by RPN and hard-gate status")
    _add_output(p)
    p = sub.add_parser("gonogo", help="Evaluate program GO/NO-GO decision records")
    p.add_argument("--set", dest="overrides", action="append", default=[], metavar="ID=STATUS")
    _add_output(p)
    p = sub.add_parser("maturity", help="Score a normalized gene-by-sample expression matrix")
    p.add_argument("expression_csv")
    _add_output(p)
    p = sub.add_parser("benchmark", help="Check five-case ordinal benchmark agreement")
    p.add_argument("input_csv")
    _add_output(p, "results/benchmark_gate.json")
    p = sub.add_parser("score", help="Score architecture summary metrics with uncertainty")
    p.add_argument("input_csv")
    p.add_argument("--draws", type=int, default=10000)
    p.add_argument("--seed", type=int, default=204)
    p.add_argument("--gate-report", help="Generated validation-gates report; unlocks independent-review status only")
    _add_output(p, "results/architecture_scores.csv")
    p = sub.add_parser("convergence", help="Evaluate >=3 spatial resolutions and >=2 time steps")
    p.add_argument("input_csv")
    p.add_argument("--tolerance-percent", type=float, default=5.0)
    _add_output(p, "results/convergence_report.json")
    p = sub.add_parser("gates", help="Evaluate the full evidence/validation checklist")
    p.add_argument("input_json")
    _add_output(p, "results/validation_gates.json")
    p = sub.add_parser("geometry", help="Validate a sourced parametric design spec; does not create a mesh")
    p.add_argument("input_json")
    _add_output(p, "results/geometry_spec_validated.json")
    p = sub.add_parser("sweep", help="Prepare architecture x phenotype x host run matrix without inventing simulation outputs")
    p.add_argument("--hosts", required=True, help="JSON list of host records with mesh path, source URL, species and verified license status")
    p.add_argument("--phenotypes", required=True, help="Comma-separated phenotype IDs")
    p.add_argument("--architectures", default="A,B,C,D")
    _add_output(p, "results/sweep_manifest.json")
    p = sub.add_parser("simulate", help="Execute an explicit validated solver run manifest")
    p.add_argument("run_manifest")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--timeout-seconds", type=int, default=86400)
    _add_output(p, "results/solver_run_summary.json")
    p = sub.add_parser("assets", help="Inspect public Zenodo assets; download only an explicitly selected file")
    p.add_argument("--record", required=True, help="Zenodo record ID or 'all'")
    p.add_argument("--download-file", help="Exact filename to download from a single record")
    p.add_argument("--accept-license", action="store_true", help="Acknowledge that you reviewed the source license before download")
    p.add_argument("--download-dir", default="data/external")
    _add_output(p, "results/asset_inventory.json")
    return parser


def _parse_overrides(pairs: list[str]) -> dict[str, str]:
    out = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"Override {pair!r} must be ID=STATUS")
        key, value = pair.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _parse_weights(spec: str | None) -> dict[str, float] | None:
    if not spec:
        return None
    weights = {}
    for pair in spec.split(","):
        if "=" not in pair:
            raise ValueError(f"Weight {pair!r} must be axis=value")
        key, value = pair.split("=", 1)
        weights[key.strip()] = float(value)
    return weights


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "plan":
            _write(report_data() if args.json else render_report(), args.out, markdown=not args.json)
        elif args.command == "architectures":
            _write(architecture_scores(_parse_weights(args.weights)), args.out)
        elif args.command == "risks":
            _write(risk_scores(), args.out)
        elif args.command == "gonogo":
            _write(evaluate_go_no_go(_parse_overrides(args.overrides)), args.out)
        elif args.command == "maturity":
            _write(score_maturity(load_expression(args.expression_csv)), args.out)
        elif args.command == "benchmark":
            result = evaluate_benchmark(pd.read_csv(args.input_csv))
            _write(result, args.out)
            if not result["passed"]:
                return 2
        elif args.command == "score":
            gates_complete = False
            if args.gate_report:
                payload = json.loads(Path(args.gate_report).read_text(encoding="utf-8"))
                gates_complete = validate_gate_report(payload)
            result = score_architectures(
                pd.read_csv(args.input_csv),
                settings=ScoreSettings(weights=DEFAULT_WEIGHTS.copy(), draws=args.draws, seed=args.seed),
                validation_gates_complete=gates_complete,
            )
            if args.out:
                target = Path(args.out)
                target.parent.mkdir(parents=True, exist_ok=True)
                result.to_csv(target, index=False)
                print(f"Wrote {target}")
            else:
                print(result.to_string(index=False))
            if not gates_complete:
                print("WARNING: outputs are exploratory; validation sign-offs remain incomplete.", file=sys.stderr)
        elif args.command == "convergence":
            result = evaluate_file(args.input_csv, tolerance_percent=args.tolerance_percent)
            _write(result, args.out)
            if not result["passed"]:
                return 2
        elif args.command == "gates":
            result = evaluate_gate_file(args.input_json)
            _write(result, args.out)
            if not result["all_signoff_gates_recorded"]:
                return 2
        elif args.command == "geometry":
            payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
            result = validate_geometry_spec(payload["architecture"], payload["parameters"], payload.get("parameter_provenance", {}))
            _write(result, args.out)
        elif args.command == "sweep":
            hosts = json.loads(Path(args.hosts).read_text(encoding="utf-8"))
            result = prepare_sweep(hosts, [x.strip() for x in args.phenotypes.split(",") if x.strip()], [x.strip().upper() for x in args.architectures.split(",")])
            _write(result, args.out)
        elif args.command == "simulate":
            result = run_simulation(args.run_manifest, args.out_dir, args.timeout_seconds)
            _write(result, args.out)
            if result["status"] != "PROCESS_SUCCEEDED":
                return 2
        elif args.command == "assets":
            records = ["17415592", "17435811"] if args.record.lower() == "all" else [args.record]
            if args.download_file and len(records) != 1:
                raise ValueError("Select one record to download a file; --record all is inventory-only.")
            output = {"records": [record_inventory(record) for record in records]}
            if args.download_file:
                output["download"] = download_record_file(records[0], args.download_file, args.download_dir, accept_license=args.accept_license)
            _write(output, args.out)
    except (ValueError, OSError, KeyError, TypeError, PermissionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
