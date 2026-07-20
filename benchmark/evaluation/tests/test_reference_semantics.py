from __future__ import annotations

import json
from pathlib import Path

from evaluation.evaluator.orchestrator import BenchmarkOrchestrator

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "category2_edge_time.jsonocel"


def _template(
    template_id: str,
    category: str,
    question: str,
    runtime_variables: list[str],
    target_metric: str,
    lookup_path: str,
) -> dict[str, object]:
    return {
        "template_id": template_id,
        "category": category,
        "formal_pattern": f"Reference semantics test {template_id}",
        "dimensions_tested": ["factual_correctness"],
        "analyst_question_template": question,
        "runtime_variables": runtime_variables,
        "preconditions": [],
        "evaluation_logic": {
            "expected_tool_chain": [{"tool": "fetch_ocdfg", "required": True}],
            "mathematical_assertion": {
                "target_metric": target_metric,
                "aggregation_applied": "$SIGMA" if "$SIGMA" in runtime_variables else "none",
                "result_type": "reference",
                "lookup_path": lookup_path,
            },
        },
    }


def _write_reference_semantics_benchmark(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                _template(
                    "OCPM_GEN_027",
                    "Category_2",
                    "What is the $SIGMA edge duration of the directed transition from $ACT_X to $ACT_Y for object type $OT_A?",
                    ["$OT_A", "$ACT_X", "$ACT_Y", "$SIGMA"],
                    "edge_duration",
                    "aggregate($SIGMA, ocdfg.edges[$ACT_X,$ACT_Y,$OT_A].durations)",
                ),
                _template(
                    "OCPM_GEN_076",
                    "Category_4",
                    "What is the average throughput time between activity $ACT_Y and activity $ACT_X for object type $OT_A?",
                    ["$OT_A", "$ACT_Y", "$ACT_X"],
                    "throughput_time",
                    "eventually_follows_duration($ACT_Y, $ACT_X, $OT_A)",
                ),
                _template(
                    "OCPM_GEN_081",
                    "Category_4",
                    "What is the convergence degree of object type $OT_A at activity $ACT_X?",
                    ["$OT_A", "$ACT_X"],
                    "convergence_degree",
                    "object_interactions.convergence_degree(activity == $ACT_X, object_type == $OT_A)",
                ),
            ]
        ),
        encoding="utf-8",
    )


def test_reference_rows_do_not_compute_success_with_null_value(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "reference_semantics.json"
    _write_reference_semantics_benchmark(benchmark_path)

    rows = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=tmp_path / "out",
    ).rows

    assert not [
        row for row in rows
        if row["final_status"] == "computed"
        and row["reference_status"] == "success"
        and row["reference_value"] is None
    ]


def test_no_valid_interaction_nulls_are_skipped_not_success(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "reference_semantics.json"
    _write_reference_semantics_benchmark(benchmark_path)

    rows = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=tmp_path / "out",
    ).rows
    skipped = [
        row for row in rows
        if row["template_id"] == "OCPM_GEN_076"
        and row["runtime_variables_used"] == {"$OT_A": "Order", "$ACT_Y": "D End", "$ACT_X": "A Start"}
    ]

    assert skipped
    assert skipped[0]["final_status"] == "skipped_no_valid_variables"
    assert skipped[0]["reference_status"] == "failed"
    assert skipped[0]["reference_value"] is None


def test_unsupported_none_aggregation_is_labeled_explicitly(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "reference_semantics.json"
    _write_reference_semantics_benchmark(benchmark_path)

    rows = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=tmp_path / "out",
    ).rows
    unsupported = [row for row in rows if row["runtime_variables_used"].get("$SIGMA") == "none"]

    assert unsupported
    assert {row["final_status"] for row in unsupported} == {"skipped_unsupported_metric"}
    assert {row["reference_status"] for row in unsupported} == {"unsupported"}
    assert {row["error_or_skip_reason"] for row in unsupported} == {"Unsupported aggregation 'none'"}


def test_reference_only_rows_record_graph_provenance_without_llm_or_agent(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "reference_semantics.json"
    _write_reference_semantics_benchmark(benchmark_path)

    rows = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=tmp_path / "out",
    ).rows

    assert rows
    assert {row["used_llm"] for row in rows} == {False}
    assert {row["used_agent"] for row in rows} == {False}
    assert {row["used_pm4py"] for row in rows} == {False}
    assert {row["used_graph"] for row in rows} == {True}
    assert all(row["reference_source"] for row in rows)
    assert all(row["graph_source"] for row in rows)


def test_category_4_rows_have_metric_definitions(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "reference_semantics.json"
    _write_reference_semantics_benchmark(benchmark_path)

    rows = BenchmarkOrchestrator().run(
        benchmark_json=benchmark_path,
        ocel_path=LOG_PATH,
        mode="reference-only",
        output_dir=tmp_path / "out",
    ).rows
    category_4_rows = [row for row in rows if row["category"] == "Category_4"]

    assert category_4_rows
    assert all(row["metric_definition"] for row in category_4_rows)
    assert any("convergence_degree" in row["metric_definition"] for row in category_4_rows)
