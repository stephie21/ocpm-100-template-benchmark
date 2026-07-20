from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evaluation.scripts.create_sample import create_sample, sample_records

ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = ROOT / "evaluation" / "scripts" / "create_sample.py"


def _record(index: int, category: str, status: str = "passed", reference_value: int = 1) -> dict[str, object]:
    return {
        "question_id": f"q-{index}",
        "category": category,
        "preconditions_status": status,
        "reference_value": reference_value,
        "field_count_marker": 23,
    }


def test_sample_records_returns_requested_passed_rows() -> None:
    records = [
        _record(1, "Category_1"),
        _record(2, "Category_1"),
        _record(3, "Category_2"),
        _record(4, "Category_2"),
        _record(5, "Category_3"),
        _record(6, "Category_4"),
    ]

    sampled = sample_records(records, sample_size=4)

    assert len(sampled) == 4
    assert all(record["preconditions_status"] == "passed" for record in sampled)
    assert len({record["category"] for record in sampled}) == 4


def test_create_sample_filters_failed_and_zero_answers(tmp_path: Path) -> None:
    input_path = tmp_path / "benchmark_results.jsonl"
    output_path = tmp_path / "sampled.jsonl"
    rows = [
        _record(1, "Category_1", reference_value=0),
        _record(2, "Category_1", reference_value=3),
        _record(3, "Category_2", status="failed", reference_value=4),
        _record(4, "Category_2", reference_value=5),
    ]
    input_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    sampled = create_sample(
        input_jsonl=input_path,
        output_jsonl=output_path,
        sample_size=10,
        exclude_zero_answers=True,
    )
    written = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert sampled == written
    assert [record["question_id"] for record in written] == ["q-2", "q-4"]
    assert all(record["preconditions_status"] == "passed" for record in written)
    assert all(record["reference_value"] != 0 for record in written)


def test_cli_writes_requested_sample_size(tmp_path: Path) -> None:
    input_path = tmp_path / "benchmark_results.jsonl"
    output_path = tmp_path / "sampled.jsonl"
    rows = [_record(index, f"Category_{(index % 4) + 1}") for index in range(12)]
    input_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            CLI_PATH.as_posix(),
            "--input-jsonl",
            input_path.as_posix(),
            "--output-jsonl",
            output_path.as_posix(),
            "--sample-size",
            "5",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    written = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert "sampled 5 rows" in result.stdout
    assert len(written) == 5
    assert all(record["preconditions_status"] == "passed" for record in written)
