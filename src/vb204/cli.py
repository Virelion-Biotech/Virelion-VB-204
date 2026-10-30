"""Command-line entry points for reproducible VB-204 exploratory analyses."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from .benchmark import evaluate_benchmark
from .scoring import DEFAULT_WEIGHTS, ScoreSettings, score_architectures

def main() -> int:
    parser = argparse.ArgumentParser(prog="vb204", description="VB-204 exploratory risk engine")
    sub = parser.add_subparsers(dest="command", required=True)
    score = sub.add_parser("score", help="score a candidate summary CSV")
    score.add_argument("input", type=Path)
    score.add_argument("--output", type=Path, default=Path("results/architecture_scores.csv"))
    score.add_argument("--draws", type=int, default=10_000)
    score.add_argument("--seed", type=int, default=204)
    score.add_argument("--gate-report", type=Path)
    gate = sub.add_parser("benchmark", help="run the five-study benchmark data gate")
    gate.add_argument("input", type=Path)
    gate.add_argument("--output", type=Path, default=Path("results/benchmark_gate.json"))
    args = parser.parse_args()
    if args.command == "benchmark":
        report = evaluate_benchmark(pd.read_csv(args.input))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report.to_dict(), indent=2))
        return 0 if report.passed else 2
    gate_passed = False
    if args.gate_report:
        gate_passed = json.loads(args.gate_report.read_text(encoding="utf-8")).get("passed") is True
    result = score_architectures(pd.read_csv(args.input),
        settings=ScoreSettings(weights=DEFAULT_WEIGHTS.copy(), draws=args.draws, seed=args.seed),
        benchmark_gate_passed=gate_passed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(result.to_string(index=False))
    if not gate_passed:
        print("\nWARNING: benchmark gate not passed; outputs are exploratory and blocked for design decisions.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
