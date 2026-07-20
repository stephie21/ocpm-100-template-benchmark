from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path

import pytest

from evaluation.ingestion.metadata import extract_metadata
from evaluation.ingestion.ocel_loader import load_ocel

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"
EXPECTED_PATH = ROOT / "evaluation" / "expected" / "tiny_ocel2_expected_values.json"


def _expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))



def _assert_no_pm4py_or_pandas(value) -> None:
    module = type(value).__module__
    assert not module.startswith(("pm4py", "pandas")), f"leaked unstable type: {module}.{type(value).__name__}"
    if isinstance(value, dict):
        raise AssertionError("ReferenceModel boundary exposed a mutable dict")
    if isinstance(value, list | set):
        raise AssertionError(f"ReferenceModel boundary exposed mutable {type(value).__name__}")
    if isinstance(value, str | int | float | bool | datetime | type(None)):
        return
    if isinstance(value, tuple):
        for item in value:
            _assert_no_pm4py_or_pandas(item)
        return
    if hasattr(value, "items"):
        for key, item in value.items():
            _assert_no_pm4py_or_pandas(key)
            _assert_no_pm4py_or_pandas(item)
        return
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_pm4py_or_pandas(getattr(value, field.name))


def _edge_dicts(model, object_type: str) -> list[dict]:
    return [
        {
            "source": edge.source,
            "target": edge.target,
            "count": edge.count,
            "object_ids": list(edge.object_ids),
        }
        for edge in model.directly_follows_edges.get(object_type, ())
    ]


def test_json_ocel_fixture_loads_into_reference_model() -> None:
    model = load_ocel(FIXTURE_PATH)
    expected = _expected()

    assert list(model.object_types) == expected["object_types"]
    assert list(model.activities) == expected["activities"]
    assert len(model.events) == expected["event_count"]
    assert len(model.objects) == expected["object_count"]
    assert len(model.event_object_relations) == expected["relation_count"]
    assert model.support_status["json_ocel"].startswith("supported")
    assert "sqlite_ocel" in model.support_status


def test_reference_model_contains_objects_relations_and_timestamps() -> None:
    model = load_ocel(FIXTURE_PATH)
    expected = _expected()

    objects = [
        {"object_id": obj.object_id, "object_type": obj.object_type}
        for obj in model.objects
    ]
    timestamps = {
        event_id: timestamp.isoformat()
        for event_id, timestamp in model.timestamps.items()
    }
    relation_pairs = {
        (relation.event_id, relation.object_id, relation.object_type)
        for relation in model.event_object_relations
    }

    assert objects == expected["objects"]
    assert timestamps == expected["timestamps"]
    assert ("e1", "o1", "Order") in relation_pairs
    assert ("e1", "i1", "Item") in relation_pairs
    assert ("e6", "o2", "Order") in relation_pairs


def test_directly_follows_edges_are_deterministic_per_object_type() -> None:
    model = load_ocel(FIXTURE_PATH)
    expected = _expected()

    assert _edge_dicts(model, "Item") == expected["directly_follows"]["Item"]
    assert _edge_dicts(model, "Order") == expected["directly_follows"]["Order"]
    assert model.directly_follows_counts("Order") == {
        ("A Start", "B Middle"): 1,
        ("A Start", "C Branch"): 1,
        ("B Middle", "D End"): 1,
        ("C Branch", "D End"): 1,
    }


def test_metadata_extraction_uses_normalized_reference_model() -> None:
    model = load_ocel(FIXTURE_PATH)
    expected = _expected()
    metadata = extract_metadata(model)

    assert list(metadata.object_types) == expected["object_types"]
    assert list(metadata.activities) == expected["activities"]
    assert metadata.event_count == expected["event_count"]
    assert metadata.object_count == expected["object_count"]
    assert metadata.relation_count == expected["relation_count"]
    assert metadata.start_timestamp.isoformat() == expected["timestamps"]["e1"]
    assert metadata.end_timestamp.isoformat() == expected["timestamps"]["e6"]


def test_unsupported_extension_fails_explicitly() -> None:
    try:
        load_ocel(ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.txt")
    except ValueError as exc:
        assert "Unsupported OCEL file extension" in str(exc)
    else:
        raise AssertionError("Unsupported OCEL extension did not fail explicitly")


def test_reference_model_boundary_is_immutable_and_pm4py_free() -> None:
    model = load_ocel(FIXTURE_PATH)

    assert type(next(iter(model.timestamps.values()))) is datetime
    assert not isinstance(model.directly_follows_edges, dict)
    assert not isinstance(model.support_status, dict)
    assert not isinstance(model.events[0].attributes, dict)
    assert not isinstance(model.objects[0].attributes, dict)

    _assert_no_pm4py_or_pandas(model.object_types)
    _assert_no_pm4py_or_pandas(model.activities)
    _assert_no_pm4py_or_pandas(model.events)
    _assert_no_pm4py_or_pandas(model.objects)
    _assert_no_pm4py_or_pandas(model.event_object_relations)
    _assert_no_pm4py_or_pandas(model.directly_follows_edges)
    _assert_no_pm4py_or_pandas(model.timestamps)

    with pytest.raises(TypeError):
        model.support_status["new"] = "not allowed"
    with pytest.raises(TypeError):
        model.directly_follows_edges["Order"] = ()
