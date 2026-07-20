from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evaluation.compiler.benchmark_compiler import (
    BenchmarkCompiler,
    BenchmarkDataset,
    load_templates_from_file,
)
from evaluation.schemas.benchmark import BenchmarkTemplate

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "category1_node_activity.jsonocel"
CLI_PATH = ROOT / "evaluation" / "scripts" / "compile_benchmark.py"


def _template() -> BenchmarkTemplate:
    return BenchmarkTemplate.model_validate(
        {
            "template_id": "OCPM_GEN_001",
            "category": "Category_1",
            "formal_pattern": "Object-Type-Specific Node Out-Degree",
            "dimensions_tested": ["factual_correctness"],
            "analyst_question_template": "What is the out-degree of activity $ACT_X for object type $OT_A?",
            "runtime_variables": ["$OT_A", "$ACT_X"],
            "preconditions": ["$OT_A in ocel.object_types", "$ACT_X in ocel.activities"],
            "evaluation_logic": {
                "expected_tool_chain": [
                    {"tool": "fetch_ocel_metadata", "required": True},
                    {"tool": "get_node_metrics", "required": True},
                ],
                "mathematical_assertion": {
                    "target_metric": "node_out_degree",
                    "aggregation_applied": "none",
                    "result_type": "integer",
                    "lookup_path": "ocdfg.nodes[$ACT_X].metrics[$OT_A].out_degree",
                },
            },
        }
    )


def test_benchmark_compiler_builds_exportable_dataset(tmp_path: Path) -> None:
    compiler = BenchmarkCompiler()
    dataset = compiler.compile(LOG_PATH, [_template()])

    assert dataset.source_log_path == LOG_PATH.as_posix()
    assert dataset.template_count == 1
    assert dataset.instance_count == 4
    assert dataset.object_types == ["Order"]
    assert dataset.activities == ["A Start", "B Middle", "C Branch", "D End"]
    assert [instance.analyst_question for instance in dataset.instances] == [
        "What is the out-degree of activity A Start for object type Order?",
        "What is the out-degree of activity B Middle for object type Order?",
        "What is the out-degree of activity C Branch for object type Order?",
        "What is the out-degree of activity D End for object type Order?",
    ]
    assert dataset.instances[0].runtime_variables_used == {"$OT_A": "Order", "$ACT_X": "A Start"}
    assert dataset.instances[0].mathematical_assertion["lookup_path"] == (
        "ocdfg.nodes[A Start].metrics[Order].out_degree"
    )

    output_path = tmp_path / "compiled_dataset.json"
    compiler.write_dataset(dataset, output_path)
    reloaded = BenchmarkDataset.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert reloaded == dataset


def test_template_file_loader_accepts_single_template_and_list(tmp_path: Path) -> None:
    template = _template().model_dump()
    single_path = tmp_path / "single.json"
    list_path = tmp_path / "list.json"
    single_path.write_text(json.dumps(template), encoding="utf-8")
    list_path.write_text(json.dumps([template]), encoding="utf-8")

    assert load_templates_from_file(single_path)[0].template_id == "OCPM_GEN_001"
    assert load_templates_from_file(list_path)[0].template_id == "OCPM_GEN_001"


def test_compile_benchmark_cli_writes_dataset(tmp_path: Path) -> None:
    templates_path = tmp_path / "templates.json"
    output_path = tmp_path / "compiled_cli_dataset.json"
    templates_path.write_text(json.dumps([_template().model_dump()]), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(CLI_PATH),
            "--log-path",
            str(LOG_PATH),
            "--templates-file",
            str(templates_path),
            "--output-path",
            str(output_path),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "compiled 4 benchmark instances" in result.stdout
    dataset = BenchmarkDataset.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert dataset.instance_count == 4
    assert dataset.instances[-1].analyst_question == "What is the out-degree of activity D End for object type Order?"
