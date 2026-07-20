from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.schemas.benchmark import (
    DEFAULT_BENCHMARK_PATH,
    DEFAULT_SUMMARY_PATH,
    BenchmarkTemplate,
    REQUIRED_FIELDS_CHECKED,
    validate_benchmark_templates,
    write_schema_summary,
)

ROOT = Path(__file__).resolve().parents[2]


def test_all_master_benchmark_templates_validate() -> None:
    templates, failures = validate_benchmark_templates(DEFAULT_BENCHMARK_PATH)

    assert failures == []
    assert len(templates) == 100
    assert templates[0].template_id == "OCPM_GEN_001"
    assert templates[-1].template_id == "OCPM_GEN_100"
    assert {template.category for template in templates} == {
        "Category_1",
        "Category_2",
        "Category_3",
        "Category_4",
    }


def test_representative_category_1_template_loads_nested_assertion() -> None:
    templates, _ = validate_benchmark_templates(DEFAULT_BENCHMARK_PATH)
    category_1 = next(template for template in templates if template.category == "Category_1")

    assert category_1.template_id == "OCPM_GEN_001"
    assert category_1.evaluation_logic.expected_tool_chain[0].tool == "fetch_ocel_metadata"
    assert category_1.evaluation_logic.expected_tool_chain[0].required is True
    assert category_1.evaluation_logic.mathematical_assertion.target_metric == "node_out_degree"
    assert category_1.evaluation_logic.mathematical_assertion.aggregation_applied == "none"
    assert category_1.evaluation_logic.mathematical_assertion.result_type == "integer"
    assert category_1.evaluation_logic.mathematical_assertion.lookup_path == (
        "ocdfg.nodes[$ACT_X].metrics[$OT_A].out_degree"
    )


def test_representative_category_4_template_loads_nested_assertion() -> None:
    templates, _ = validate_benchmark_templates(DEFAULT_BENCHMARK_PATH)
    category_4 = next(template for template in templates if template.category == "Category_4")

    assert category_4.template_id.startswith("OCPM_GEN_")
    assert category_4.category == "Category_4"
    assert category_4.evaluation_logic.expected_tool_chain
    assertion = category_4.evaluation_logic.mathematical_assertion
    assert assertion.target_metric
    assert assertion.aggregation_applied
    assert assertion.result_type
    assert assertion.lookup_path


def test_schema_summary_report_is_written() -> None:
    summary = write_schema_summary(DEFAULT_BENCHMARK_PATH, DEFAULT_SUMMARY_PATH)

    assert DEFAULT_SUMMARY_PATH.exists()
    written_summary = json.loads(DEFAULT_SUMMARY_PATH.read_text(encoding="utf-8"))
    assert written_summary == summary
    assert summary["validated"] is True
    assert summary["raw_template_count"] == 100
    assert summary["validated_template_count"] == 100
    assert summary["validation_failed_count"] == 0
    assert summary["categories"] == {
        "Category_1": 25,
        "Category_2": 25,
        "Category_3": 25,
        "Category_4": 25,
    }
    assert summary["required_fields_checked"] == REQUIRED_FIELDS_CHECKED
    assert "evaluation_logic.expected_tool_chain" in summary["nested_fields_checked"]
    assert "evaluation_logic.mathematical_assertion.lookup_path" in summary["nested_fields_checked"]
    assert summary["failures"] == []


def test_missing_required_nested_lookup_path_fails_validation() -> None:
    raw = json.loads(DEFAULT_BENCHMARK_PATH.read_text(encoding="utf-8"))[0]
    broken = dict(raw)
    broken["evaluation_logic"] = dict(raw["evaluation_logic"])
    broken["evaluation_logic"]["mathematical_assertion"] = dict(
        raw["evaluation_logic"]["mathematical_assertion"]
    )
    del broken["evaluation_logic"]["mathematical_assertion"]["lookup_path"]

    with pytest.raises(ValidationError):
        BenchmarkTemplate.model_validate(broken)
