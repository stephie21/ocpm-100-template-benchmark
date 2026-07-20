from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.ingestion.ocel_loader import load_ocel

ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "evaluation" / "scripts" / "generate_fixtures.py"
FIXTURE_DIR = ROOT / "evaluation" / "fixtures" / "ocel"
EXPECTED_DIR = ROOT / "evaluation" / "fixtures" / "expected"

FIXTURES = {
    "category_1": (
        FIXTURE_DIR / "category1_node_activity.jsonocel",
        EXPECTED_DIR / "category1_node_activity_expected.json",
    ),
    "category_2": (
        FIXTURE_DIR / "category2_edge_time.jsonocel",
        EXPECTED_DIR / "category2_edge_time_expected.json",
    ),
    "category_3": (
        FIXTURE_DIR / "category3_path_reachability.jsonocel",
        EXPECTED_DIR / "category3_path_reachability_expected.json",
    ),
    "category_4": (
        FIXTURE_DIR / "category4_multi_object_sync.jsonocel",
        EXPECTED_DIR / "category4_multi_object_sync_expected.json",
    ),
}


def _read_expected(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_fixtures_script_runs_successfully() -> None:
    subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, check=True)


@pytest.mark.parametrize("category", sorted(FIXTURES))
def test_fixture_and_expected_files_exist(category: str) -> None:
    fixture_path, expected_path = FIXTURES[category]

    assert fixture_path.exists(), fixture_path
    assert expected_path.exists(), expected_path


@pytest.mark.parametrize("category", sorted(FIXTURES))
def test_fixtures_load_without_data_loss(category: str) -> None:
    fixture_path, expected_path = FIXTURES[category]
    expected = _read_expected(expected_path)
    model = load_ocel(fixture_path)

    assert list(model.object_types) == expected["object_types"]
    assert list(model.activities) == expected["activities"]
    assert len(model.events) == expected["event_count"]
    assert len(model.objects) == expected["object_count"]
    assert len(model.event_object_relations) == expected["relation_count"]
    assert model.directly_follows_edges


def test_category_1_node_activity_expected_values_are_manual_and_exact() -> None:
    expected = _read_expected(FIXTURES["category_1"][1])

    assert expected["assertions"] == {
        "out_degree(A Start)": 2,
        "in_degree(D End)": 2,
        "start_frequency(A Start)": 2,
        "end_frequency(D End)": 2,
        "zero_in_degree": ["A Start"],
        "zero_out_degree": ["D End"],
    }
    assert expected["node_metrics"]["A Start"]["out_degree"] == 2
    assert expected["node_metrics"]["D End"]["in_degree"] == 2


def test_category_2_edge_time_expected_values_are_manual_and_exact() -> None:
    expected = _read_expected(FIXTURES["category_2"][1])
    durations = expected["edge_durations"]

    assert durations["A Start->B Middle"]["durations_seconds"] == [3600]
    assert durations["A Start->C Branch"]["durations_seconds"] == [2700]
    assert durations["B Middle->D End"]["durations_seconds"] == [5400]
    assert durations["C Branch->D End"]["durations_seconds"] == [7200]
    assert durations["C Branch->D End"]["waiting_times_seconds"] == [7200]


def test_category_3_path_reachability_expected_values_are_manual_and_exact() -> None:
    expected = _read_expected(FIXTURES["category_3"][1])

    assert expected["activities"] == ["A", "B", "C", "D"]
    assert expected["reachability"] == {
        "path_exists_A_D": True,
        "reachable_from_A": ["B", "C", "D"],
        "shortest_path_distance_A_D": 2,
    }


def test_category_4_multi_object_cooccurrence_expected_values_are_manual_and_exact() -> None:
    expected = _read_expected(FIXTURES["category_4"][1])

    assert expected["object_types"] == ["Item", "Order"]
    assert expected["cooccurrence"] == {
        "activity_level_frequency": {
            "Pick Item": 2,
            "Ship": 1,
        },
        "cooccurrence_Order_Item": True,
        "cooccurring_event_ids": ["c4_e2", "c4_e3", "c4_e5"],
        "event_level_frequency": 3,
    }
