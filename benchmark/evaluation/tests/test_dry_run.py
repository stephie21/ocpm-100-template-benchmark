from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from evaluation.compiler.benchmark_compiler import load_templates_from_file
from evaluation.reporting.dry_run import BenchmarkDryRun

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"
CLI_PATH = ROOT / "evaluation" / "scripts" / "run_benchmark.py"


def _write_template(path: Path) -> None:
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
            ],
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_dry_run_prints_required_observability_fields(tmp_path: Path, capsys) -> None:
    templates_path = tmp_path / "templates.json"
    output_path = tmp_path / "report.json"
    _write_template(templates_path)

    BenchmarkDryRun().run(
        benchmark_path=templates_path,
        ocel_path=LOG_PATH,
        templates=load_templates_from_file(templates_path),
        output_paths=[output_path],
    )

    stdout = capsys.readouterr().out
    assert "OCPM Benchmark Dry-Run Trace" in stdout
    assert "benchmark JSON path:" in stdout
    assert "OCEL path:" in stdout
    assert "number of templates loaded: 1" in stdout
    assert "loaded template IDs: [OCPM_GEN_001]" in stdout
    assert "loaded object types: [Item, Order]" in stdout
    assert "loaded activities: [A Start, B Middle, C Branch, D End]" in stdout
    assert "generated variable candidates:" in stdout
    assert "instantiated variables:" in stdout
    assert "precondition evaluation outcomes:" in stdout
    assert "selected reference handler: Category1Handler" in stdout
    assert "reference result:" in stdout
    assert "final output paths:" in stdout


def test_run_benchmark_cli_dry_run_writes_trace_to_stdout(tmp_path: Path) -> None:
    templates_path = tmp_path / "templates.json"
    output_path = tmp_path / "report.json"
    _write_template(templates_path)

    completed = subprocess.run(
        [
            sys.executable,
            CLI_PATH.as_posix(),
            "--log-path",
            LOG_PATH.as_posix(),
            "--templates-file",
            templates_path.as_posix(),
            "--output-path",
            output_path.as_posix(),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "OCPM Benchmark Dry-Run Trace" in completed.stdout
    assert "generated variable candidates:" in completed.stdout
    assert "precondition evaluation outcomes:" in completed.stdout
    assert "final output paths:" in completed.stdout
    assert not output_path.exists()


def test_run_benchmark_cli_verbose_live_run_prints_execution_metrics(tmp_path: Path) -> None:
    templates_path = tmp_path / "templates.json"
    output_path = tmp_path / "report.json"
    _write_template(templates_path)

    completed = subprocess.run(
        [
            sys.executable,
            CLI_PATH.as_posix(),
            "--log-path",
            LOG_PATH.as_posix(),
            "--templates-file",
            templates_path.as_posix(),
            "--output-path",
            output_path.as_posix(),
            "--verbose",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.exists()
    assert "OCPM Benchmark Verbose Evaluation" in completed.stdout
    assert "number of execution records:" in completed.stdout
    assert "precondition evaluation outcomes:" in completed.stdout
    assert "reference result:" in completed.stdout
