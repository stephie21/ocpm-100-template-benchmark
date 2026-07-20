from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse, json

def sample_records(records, sample_size: int):
    passed=[row for row in records if row.get("preconditions_status") == "passed"]
    by_category=[]; seen=set()
    for row in passed:
        cat=row.get("category")
        if cat not in seen:
            by_category.append(row); seen.add(cat)
    for row in passed:
        if row not in by_category:
            by_category.append(row)
    return by_category[:sample_size]

def create_sample(input_jsonl: Path, output_jsonl: Path, sample_size: int, exclude_zero_answers: bool=False):
    records=[json.loads(line) for line in Path(input_jsonl).read_text(encoding="utf-8").splitlines() if line.strip()]
    if exclude_zero_answers:
        records=[row for row in records if row.get("reference_value") != 0]
    sampled=sample_records(records, sample_size)
    Path(output_jsonl).write_text("".join(json.dumps(row, sort_keys=True)+"\n" for row in sampled), encoding="utf-8")
    return sampled

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--input-jsonl", required=True); parser.add_argument("--output-jsonl", required=True); parser.add_argument("--sample-size", type=int, required=True); parser.add_argument("--exclude-zero-answers", action="store_true")
    args=parser.parse_args(); rows=create_sample(args.input_jsonl,args.output_jsonl,args.sample_size,args.exclude_zero_answers); print(f"wrote {len(rows)} sampled records")
if __name__ == "__main__": main()
