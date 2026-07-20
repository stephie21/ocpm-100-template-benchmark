from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_PATH = ROOT / "data" / "OCPM_BENCHMARK_Q.json"
DEFAULT_SUMMARY_PATH = ROOT / "reports" / "benchmark_schema_summary.json"
REQUIRED_FIELDS_CHECKED = [
    "template_id",
    "category",
    "formal_pattern",
    "dimensions_tested",
    "analyst_question_template",
    "runtime_variables",
    "preconditions",
    "evaluation_logic",
]

class ExpectedTool(BaseModel):
    tool: str
    required: bool = True

class MathematicalAssertion(BaseModel):
    target_metric: str
    aggregation_applied: str
    result_type: str
    lookup_path: str

class EvaluationLogic(BaseModel):
    expected_tool_chain: list[ExpectedTool]
    mathematical_assertion: MathematicalAssertion

    @classmethod
    def model_validate(cls, data: Any):
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValidationError("evaluation_logic must be an object")
        tools = [ExpectedTool.model_validate(item) for item in data.get("expected_tool_chain", [])]
        assertion = MathematicalAssertion.model_validate(data.get("mathematical_assertion", {}))
        return cls(expected_tool_chain=tools, mathematical_assertion=assertion)

class BenchmarkTemplate(BaseModel):
    template_id: str
    category: str
    formal_pattern: str
    dimensions_tested: list[str]
    analyst_question_template: str
    runtime_variables: list[str]
    preconditions: list[str]
    evaluation_logic: EvaluationLogic

    @classmethod
    def model_validate(cls, data: Any):
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValidationError("template must be an object")
        missing = [field for field in REQUIRED_FIELDS_CHECKED if field not in data]
        if missing:
            raise ValidationError("missing required fields: " + ", ".join(missing))
        return cls(
            template_id=str(data["template_id"]),
            category=str(data["category"]),
            formal_pattern=str(data["formal_pattern"]),
            dimensions_tested=list(data["dimensions_tested"]),
            analyst_question_template=str(data["analyst_question_template"]),
            runtime_variables=list(data["runtime_variables"]),
            preconditions=list(data["preconditions"]),
            evaluation_logic=EvaluationLogic.model_validate(data["evaluation_logic"]),
        )

def validate_benchmark_templates(path: Path = DEFAULT_BENCHMARK_PATH) -> tuple[list[BenchmarkTemplate], list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = [raw]
    templates: list[BenchmarkTemplate] = []
    failures: list[str] = []
    for index, item in enumerate(raw, start=1):
        try:
            templates.append(BenchmarkTemplate.model_validate(item))
        except Exception as exc:
            failures.append(f"template {index}: {exc}")
    return templates, failures

def write_schema_summary(benchmark_path: Path = DEFAULT_BENCHMARK_PATH, summary_path: Path = DEFAULT_SUMMARY_PATH) -> dict[str, Any]:
    templates, failures = validate_benchmark_templates(benchmark_path)
    category_counts: dict[str, int] = {}
    for template in templates:
        category_counts[template.category] = category_counts.get(template.category, 0) + 1
    raw = json.loads(benchmark_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw_count = 1
    else:
        raw_count = len(raw)
    summary = {
        "benchmark_path": benchmark_path.as_posix(),
        "validated": not failures,
        "raw_template_count": raw_count,
        "validated_template_count": len(templates),
        "validation_failed_count": len(failures),
        "total_templates": len(templates),
        "failure_count": len(failures),
        "failures": failures,
        "categories": category_counts,
        "required_fields_checked": REQUIRED_FIELDS_CHECKED,
        "nested_fields_checked": [
            "evaluation_logic.expected_tool_chain",
            "evaluation_logic.mathematical_assertion.lookup_path",
        ],
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
