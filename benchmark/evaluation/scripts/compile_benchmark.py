from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from evaluation.compiler.benchmark_compiler import BenchmarkCompiler, load_templates_from_file

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--templates-file", required=True)
    parser.add_argument("--output-path", required=True)
    args=parser.parse_args()
    compiler=BenchmarkCompiler(); dataset=compiler.compile(args.log_path, load_templates_from_file(args.templates_file)); compiler.write_dataset(dataset, args.output_path)
    print(f"compiled {dataset.instance_count} benchmark instances")
if __name__ == "__main__": main()
