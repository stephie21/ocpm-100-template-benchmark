from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import json

from evaluation.compiler.benchmark_compiler import BenchmarkCompiler, load_templates_from_file
from evaluation.evaluator.orchestrator import BenchmarkOrchestrator
from evaluation.reporting.dry_run import BenchmarkDryRun

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--benchmark-json")
    parser.add_argument("--ocel-path")
    parser.add_argument("--mode", default="reference-only")
    parser.add_argument("--output-dir")
    parser.add_argument("--api-base-url")
    parser.add_argument("--log-path")
    parser.add_argument("--templates-file")
    parser.add_argument("--output-path")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args=parser.parse_args()
    if args.log_path and args.templates_file and args.output_path:
        templates=load_templates_from_file(args.templates_file)
        if args.dry_run:
            BenchmarkDryRun().run(args.templates_file, args.log_path, templates, [args.output_path], write_outputs=False)
            return
        if args.verbose:
            print("OCPM Benchmark Verbose Evaluation")
            BenchmarkDryRun().run(args.templates_file, args.log_path, templates, [args.output_path], write_outputs=False)
        report=BenchmarkCompiler().evaluate(Path(args.log_path), templates)
        Path(args.output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_path).write_text(report.model_dump_json()+"\n", encoding="utf-8")
        if args.verbose:
            print(f"number of execution records: {report.summary['total_records']}")
        return
    print("OCPM Benchmark End-to-End Run")
    result=BenchmarkOrchestrator().run(args.benchmark_json, args.ocel_path, args.mode, args.output_dir, args.api_base_url, args.verbose)
    print(f"terminal status rows: {len(result.rows)}")
if __name__ == "__main__": main()
