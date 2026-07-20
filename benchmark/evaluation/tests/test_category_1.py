from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from evaluation.handlers.category_1 import Category1Handler
from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.ingestion.reference_model import EventObjectRelation, ReferenceEvent, ReferenceModel, ReferenceObject

ROOT = Path(__file__).resolve().parents[2]
TINY_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"
CATEGORY_1_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category1_node_activity.jsonocel"


def _master_templates(category: str) -> dict[str, str]:
    data = json.loads((ROOT / "evaluation" / "data" / "OCPM_BENCHMARK_Q.json").read_text(encoding="utf-8"))
    return {
        entry["template_id"]: entry["analyst_question_template"]
        for entry in data
        if entry["category"] == category
    }


def test_total_event_count_from_tiny_ocel2_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = Category1Handler().execute(Category1Handler.TOTAL_EVENTS_QUESTION, model)

    assert result == {
        "value": 6,
        "status": "success",
        "message": "Computed total event count from ReferenceModel.events",
    }


def test_object_count_by_type_from_tiny_ocel2_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category1Handler()

    order_result = handler.execute(Category1Handler.OBJECTS_BY_TYPE_QUESTION, model, {"$OT_A": "Order"})
    item_result = handler.execute(Category1Handler.OBJECTS_BY_TYPE_QUESTION, model, {"$OT_A": "Item"})

    assert order_result["status"] == "success"
    assert order_result["value"] == 2
    assert "Order" in order_result["message"]
    assert item_result["status"] == "success"
    assert item_result["value"] == 1


def test_category_1_fixture_matches_hardcoded_basic_counts() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    handler = Category1Handler()

    assert handler.execute(Category1Handler.TOTAL_EVENTS_QUESTION, model)["value"] == 6
    assert handler.execute(Category1Handler.OBJECTS_BY_TYPE_QUESTION, model, {"$OT_A": "Order"})["value"] == 2


def test_existing_object_type_with_zero_instances_returns_zero() -> None:
    model = ReferenceModel(
        object_types=("Ghost", "Order"),
        activities=("A Start",),
        events=(
            ReferenceEvent(
                event_id="e1",
                activity="A Start",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
        ),
        objects=(ReferenceObject(object_id="o1", object_type="Order"),),
        event_object_relations=(EventObjectRelation(event_id="e1", object_id="o1", object_type="Order"),),
        directly_follows_edges={},
    )

    result = Category1Handler().execute(Category1Handler.OBJECTS_BY_TYPE_QUESTION, model, {"$OT_A": "Ghost"})

    assert result["status"] == "success"
    assert result["value"] == 0
    assert "Ghost" in result["message"]


def test_missing_binding_and_unsupported_template_return_error() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category1Handler()

    missing_binding = handler.execute(Category1Handler.OBJECTS_BY_TYPE_QUESTION, model, {})
    unsupported = handler.execute("What is unsupported?", model, {})

    assert missing_binding == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$OT_A'",
    }
    assert unsupported["value"] is None
    assert unsupported["status"] == "error"
    assert "Unsupported Category 1 question template" in unsupported["message"]


def test_all_master_category_1_templates_are_supported_and_dispatch_successfully() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category1Handler()
    templates = _master_templates("Category_1")
    bindings = {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "B Middle"}

    assert set(templates.values()) <= set(handler.supported_templates())
    for template in templates.values():
        result = handler.execute(template, model, bindings)
        assert result["status"] == "success", template


def test_master_category_1_ocdfg_node_metrics_have_handcoded_values() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category1Handler()
    templates = _master_templates("Category_1")

    assert handler.execute(templates["OCPM_GEN_001"], model, {"$OT_A": "Order", "$ACT_X": "A Start"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_002"], model, {"$OT_A": "Order", "$ACT_X": "D End"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_003"], model, {"$OT_A": "Order", "$ACT_X": "A Start"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_004"], model, {"$OT_A": "Order", "$ACT_X": "A Start"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_005"], model, {"$OT_A": "Order", "$ACT_X": "D End"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_011"], model, {"$OT_A": "Order"})["value"] == ["A Start"]
    assert handler.execute(templates["OCPM_GEN_012"], model, {"$OT_A": "Order"})["value"] == ["D End"]
    assert handler.execute(templates["OCPM_GEN_018"], model, {"$OT_A": "Order", "$ACT_X": "A Start"})["value"] == 2
    assert handler.execute(templates["OCPM_GEN_022"], model, {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "B Middle"})["value"] is True
