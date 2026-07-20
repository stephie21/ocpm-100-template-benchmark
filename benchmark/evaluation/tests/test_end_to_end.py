from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from evaluation.evaluator.agent_runner import AgentRunner
from evaluation.evaluator.orchestrator import BenchmarkOrchestrator
from evaluation.evaluator.reference_runner import RESULT_FIELDS

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"
CLI_PATH = ROOT / "evaluation" / "scripts" / "run_benchmark.py"


class RecordingAgentRunner(AgentRunner):
    def __init__(self) -> None:
        super().__init__(api_base_url=None)
        self.enriched_questions: list[str] = []

    async def enrich(self, row: dict[str, Any], expected_tools: tuple[str, ...]) -> dict[str, Any]:
        self.enriched_questions.append(row["instantiated_question"])
        if row["final_status"] != "computed":
            row.update(
                {
                    "agent_status": "skipped",
                    "actual_tool_chain": [],
                    "tool_chain_alignment_score": 0.0,
                    "mode": "agent-comparison",
                }
            )
            return row
        row.update(
            {
                "agent_status": "completed",
                "llm_response": f"Reference answer: {row['reference_value']}",
                "used_llm": True,
                "used_agent": True,
                "actual_tool_chain": list(expected_tools),
                "tool_chain_alignment_score": 1.0,
                "response_contains_reference": True,
                "mode": "agent-comparison",
            }
        )
        return row


def _write_benchmark(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "template_id": "OCPM_GEN_001",
                    "category": "Category_1",
                    "formal_pattern": "Object-Type-Specific Node Out-Degree",
                    "dimensions_tested": ["factual_correctness"],
                    "analyst_question_template": "What is the out-degree of activity $ACT_X for object type $OT_A in the OC-DFG?",
                    "runtime_variables": ["$OT_A", "$ACT_X"],
                    "preconditions": [
                        "$OT_A in ocel.object_types",
                        "$ACT_X in ocel.activities",
                        "object_type_has_events($OT_A)",
                    ],
                    "evaluation_logic": {
                        "expected_tool_chain": [
                            {"tool": "fetch_ocel_metadata", "required": True},
                            {"tool": "validate_runtime_variables", "required": True},
                            {"tool": "fetch_ocdfg", "required": True},
                            {"tool": "get_node_metrics", "required": True},
                        ],
                        "mathematical_assertion": {
                            "target_metric": "node_out_degree",
                            "aggregation_applied": "none",
                            "result_type": "integer",
                            "lookup_path": "ocdfg.nodes[$ACT_X].metrics[$OT_A].out_degree",
                        },
                    },
                },
                {
                    "template_id": "OCPM_GEN_999",
                    "category": "Category_1",
                    "formal_pattern": "Unsupported E2E Safety Template",
                    "dimensions_tested": ["robustness"],
                    "analyst_question_template": "Unsupported E2E question for $OT_A?",
                    "runtime_variables": ["$OT_A"],
                    "preconditions": ["$OT_A in ocel.object_types"],
                    "evaluation_logic": {
                        "expected_tool_chain": [{"tool": "unsupported_reference_handler", "required": True}],
                        "mathematical_assertion": {
                            "target_metric": "test_metric",
                            "aggregation_applied": "none",
                            "result_type": "integer",
                            "lookup_path": "unsupported.path[$OT_A]",
                        },
                    },
                },
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_reference_only_orchestrator_writes_one_terminal_row_per_instantiation(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.json"
    output_dir = tmp_path / "reference_run"
    _write_benchmark(benchmark_path)

    result = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=output_dir,
        verbose=True,
    )

    assert len(RESULT_FIELDS) == 31
    assert len(result.rows) == 10
    assert all(tuple(row) == RESULT_FIELDS for row in result.rows)
    assert result.jsonl_path.exists()
    assert result.csv_path.exists()
    assert result.summary_path.exists()

    jsonl_rows = [json.loads(line) for line in result.jsonl_path.read_text(encoding="utf-8").splitlines()]
    with result.csv_path.open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))

    assert len(jsonl_rows) == len(result.rows)
    assert len(csv_rows) == len(result.rows)
    assert len(csv_rows[0]) == 31
    assert summary["row_count"] == len(result.rows)
    assert summary["jsonl_line_count"] == len(result.rows)
    assert summary["csv_data_line_count"] == len(result.rows)
    assert any(row["final_status"] == "skipped" for row in result.rows)
    assert all(row["final_status"] in {"computed", "skipped", "failed", "skipped_no_valid_variables", "skipped_unsupported_metric"} for row in result.rows)


def test_agent_comparison_awaits_injected_agent_without_live_http(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.json"
    output_dir = tmp_path / "agent_run"
    _write_benchmark(benchmark_path)
    agent_runner = RecordingAgentRunner()

    result = BenchmarkOrchestrator(agent_runner=agent_runner).run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="agent-comparison",
        api_base_url="http://127.0.0.1:9/unreachable",
        output_dir=output_dir,
    )

    computed_rows = [row for row in result.rows if row["final_status"] == "computed"]
    assert computed_rows
    assert len(agent_runner.enriched_questions) == len(result.rows)
    assert all(row["agent_status"] == "completed" for row in computed_rows)
    assert all(row["llm_response"] for row in computed_rows)
    assert all(row["tool_chain_alignment_score"] == 1.0 for row in computed_rows)


def test_run_benchmark_cli_matches_roadmap_reference_contract(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.json"
    output_dir = tmp_path / "cli_reference_run"
    _write_benchmark(benchmark_path)

    completed = subprocess.run(
        [
            sys.executable,
            CLI_PATH.as_posix(),
            "--benchmark-json",
            benchmark_path.as_posix(),
            "--ocel-path",
            LOG_PATH.as_posix(),
            "--mode",
            "reference-only",
            "--output-dir",
            output_dir.as_posix(),
            "--verbose",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "OCPM Benchmark End-to-End Run" in completed.stdout
    assert "terminal status rows: 10" in completed.stdout
    assert (output_dir / "benchmark_results.jsonl").exists()
    assert (output_dir / "benchmark_results.csv").exists()
