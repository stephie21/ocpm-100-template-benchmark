from __future__ import annotations

from pathlib import Path

from evaluation.compiler.benchmark_compiler import BenchmarkCompiler, EvaluationReport
from evaluation.schemas.benchmark import BenchmarkTemplate

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"


def _template(
    template_id: str,
    question: str,
    runtime_variables: list[str],
    preconditions: list[str],
    category: str = "Category_1",
) -> BenchmarkTemplate:
    return BenchmarkTemplate.model_validate(
        {
            "template_id": template_id,
            "category": category,
            "formal_pattern": "E2E test template",
            "dimensions_tested": ["factual_correctness"],
            "analyst_question_template": question,
            "runtime_variables": runtime_variables,
            "preconditions": preconditions,
            "evaluation_logic": {
                "expected_tool_chain": [{"tool": "reference_handler", "required": True}],
                "mathematical_assertion": {
                    "target_metric": "test_metric",
                    "aggregation_applied": "none",
                    "result_type": "integer",
                    "lookup_path": "compiled.value",
                },
            },
        }
    )


def test_compiler_e2e_runs_valid_template_and_exports_report() -> None:
    template = _template(
        "OCPM_GEN_001",
        "How many events are in the log?",
        [],
        [],
    )

    report = BenchmarkCompiler().evaluate(LOG_PATH, [template])

    assert report.summary == {
        "total_templates": 1,
        "total_records": 1,
        "passed": 1,
        "failed": 0,
        "skipped": 0,
    }
    record = report.details[0]
    assert record.template_id == "OCPM_GEN_001"
    assert record.runtime_variables_used == {}
    assert record.precondition_status == "passed"
    assert record.handler_status == "success"
    assert record.value == 6
    assert "Computed total event count" in record.messages[-1]

    reloaded = EvaluationReport.model_validate_json(report.model_dump_json())
    assert reloaded == report


def test_compiler_e2e_skips_failed_preconditions() -> None:
    template = _template(
        "OCPM_GEN_002",
        "How many objects of type $OT_A are in the log?",
        ["$OT_A"],
        ["'MissingType' in ocel.object_types"],
    )

    report = BenchmarkCompiler().evaluate(LOG_PATH, [template])

    assert report.summary == {
        "total_templates": 1,
        "total_records": 2,
        "passed": 0,
        "failed": 2,
        "skipped": 2,
    }
    assert {record.runtime_variables_used["$OT_A"] for record in report.details} == {"Item", "Order"}
    assert all(record.precondition_status == "failed" for record in report.details)
    assert all(record.handler_status == "skipped" for record in report.details)
    assert all(record.value is None for record in report.details)
    assert all("Skipped because at least one precondition failed" in record.messages for record in report.details)


def test_compiler_e2e_flags_unsupported_precondition_and_handler_gracefully() -> None:
    unsupported_precondition_template = _template(
        "OCPM_GEN_003",
        "How many events are in the log?",
        [],
        ["unknown_predicate('A Start', 'B Middle', 'Order')"],
    )
    unsupported_handler_template = _template(
        "OCPM_GEN_004",
        "Unsupported question?",
        [],
        [],
    )

    report = BenchmarkCompiler().evaluate(LOG_PATH, [unsupported_precondition_template, unsupported_handler_template])

    by_id = {record.template_id: record for record in report.details}
    unsupported_precondition = by_id["OCPM_GEN_003"]
    unsupported_handler = by_id["OCPM_GEN_004"]

    assert unsupported_precondition.precondition_status == "unsupported"
    assert unsupported_precondition.handler_status == "success"
    assert unsupported_precondition.value == 6
    assert any("Unsupported predicate" in message for message in unsupported_precondition.messages)

    assert unsupported_handler.precondition_status == "passed"
    assert unsupported_handler.handler_status == "unsupported"
    assert unsupported_handler.value is None
    assert "No category handler supports question template" in unsupported_handler.messages[-1]

    assert report.summary == {
        "total_templates": 2,
        "total_records": 2,
        "passed": 0,
        "failed": 0,
        "skipped": 2,
    }


def test_compiler_e2e_computes_exact_metrics_across_categories() -> None:
    templates = [
        _template(
            "OCPM_GEN_005",
            "How many events of activity $ACT_X are related to object type $OT_A?",
            ["$OT_A", "$ACT_X"],
            ["$OT_A in ocel.object_types", "$ACT_X in ocel.activities"],
            category="Category_2",
        ),
        _template(
            "OCPM_GEN_006",
            "How many times does activity $ACT_X directly follow activity $ACT_Y for object type $OT_A?",
            ["$OT_A", "$ACT_X", "$ACT_Y"],
            ["$OT_A in ocel.object_types", "$ACT_X in ocel.activities", "$ACT_Y in ocel.activities"],
            category="Category_3",
        ),
    ]

    report = BenchmarkCompiler().evaluate(LOG_PATH, templates)
    category2_record = next(
        record
        for record in report.details
        if record.template_id == "OCPM_GEN_005"
        and record.runtime_variables_used == {"$ACT_X": "A Start", "$OT_A": "Order"}
    )
    category3_record = next(
        record
        for record in report.details
        if record.template_id == "OCPM_GEN_006"
        and record.runtime_variables_used == {"$ACT_X": "B Middle", "$ACT_Y": "A Start", "$OT_A": "Order"}
    )

    assert category2_record.value == 2
    assert category2_record.handler_status == "success"
    assert category3_record.value == 1
    assert category3_record.handler_status == "success"
    assert report.summary["passed"] > 0
    assert report.summary["failed"] == 0
