from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "evaluation" / "scripts" / "inspect_repo.py"
JSON_REPORT = ROOT / "evaluation" / "reports" / "repo_inventory.json"
MARKDOWN_REPORT = ROOT / "evaluation" / "reports" / "repo_inventory.md"

EXPECTED_TOP_LEVEL_KEYS = {
    "repository_root",
    "benchmark_locations",
    "api_entrypoints",
    "agent_workflow_files",
    "pm4py_references",
    "ocel_related_code",
    "candidate_integration_points",
}


def test_repo_inventory_reports_are_created_with_expected_keys() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, check=True)

    assert JSON_REPORT.exists()
    assert MARKDOWN_REPORT.exists()

    inventory = json.loads(JSON_REPORT.read_text(encoding="utf-8"))
    assert EXPECTED_TOP_LEVEL_KEYS <= set(inventory)

    assert "generated_files_found" in inventory["benchmark_locations"]
    assert "fastapi_files" in inventory["api_entrypoints"]
    assert "routes" in inventory["api_entrypoints"]
    assert "workflow_files" in inventory["agent_workflow_files"]
    assert "present" in inventory["pm4py_references"]
    assert "references" in inventory["ocel_related_code"]
    assert inventory["candidate_integration_points"]

    markdown = MARKDOWN_REPORT.read_text(encoding="utf-8")
    assert "# Repository Inventory" in markdown
    assert "## Benchmark JSON Locations" in markdown
    assert "## API Entrypoints" in markdown
    assert "## Candidate Integration Points" in markdown
