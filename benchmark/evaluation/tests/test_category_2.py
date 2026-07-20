from __future__ import annotations

import json
from pathlib import Path

from evaluation.handlers.category_2 import Category2Handler
from evaluation.ingestion.ocel_loader import load_ocel

ROOT = Path(__file__).resolve().parents[2]
TINY_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"


def _master_templates(category: str) -> dict[str, str]:
    data = json.loads((ROOT / "evaluation" / "data" / "OCPM_BENCHMARK_Q.json").read_text(encoding="utf-8"))
    return {
        entry["template_id"]: entry["analyst_question_template"]
        for entry in data
        if entry["category"] == category
    }


def test_activity_event_count_for_object_type_matches_tiny_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category2Handler()

    order_a_start = handler.execute(
        Category2Handler.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,
        model,
        {"$ACT_X": "A Start", "$OT_A": "Order"},
    )
    item_a_start = handler.execute(
        Category2Handler.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,
        model,
        {"$ACT_X": "A Start", "$OT_A": "Item"},
    )

    assert order_a_start["status"] == "success"
    assert order_a_start["value"] == 2
    assert "A Start" in order_a_start["message"]
    assert "Order" in order_a_start["message"]
    assert item_a_start["status"] == "success"
    assert item_a_start["value"] == 1


def test_activity_object_type_zero_interaction_boundary_case() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = Category2Handler().execute(
        Category2Handler.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,
        model,
        {"$ACT_X": "C Branch", "$OT_A": "Item"},
    )

    assert result["status"] == "success"
    assert result["value"] == 0
    assert "C Branch" in result["message"]
    assert "Item" in result["message"]


def test_unique_objects_interacting_with_activity_matches_tiny_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category2Handler()

    a_start = handler.execute(
        Category2Handler.UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION,
        model,
        {"$ACT_X": "A Start"},
    )
    c_branch = handler.execute(
        Category2Handler.UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION,
        model,
        {"$ACT_X": "C Branch"},
    )
    missing_activity = handler.execute(
        Category2Handler.UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION,
        model,
        {"$ACT_X": "Missing Activity"},
    )

    assert a_start["status"] == "success"
    assert a_start["value"] == 3
    assert c_branch["status"] == "success"
    assert c_branch["value"] == 1
    assert missing_activity["status"] == "success"
    assert missing_activity["value"] == 0


def test_missing_bindings_and_unsupported_template_return_error() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category2Handler()

    missing_activity = handler.execute(
        Category2Handler.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,
        model,
        {"$OT_A": "Order"},
    )
    missing_object_type = handler.execute(
        Category2Handler.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,
        model,
        {"$ACT_X": "A Start"},
    )
    unsupported = handler.execute("Unsupported Category 2 question", model, {})

    assert missing_activity == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$ACT_X'",
    }
    assert missing_object_type == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$OT_A'",
    }
    assert unsupported["value"] is None
    assert unsupported["status"] == "error"
    assert "Unsupported Category 2 question template" in unsupported["message"]


def test_all_master_category_2_templates_are_supported_and_dispatch_successfully() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category2Handler()
    templates = _master_templates("Category_2")
    bindings = {
        "$OT_A": "Order",
        "$OT_B": "Item",
        "$ACT_X": "A Start",
        "$ACT_Y": "B Middle",
        "$ACT_Z": "C Branch",
        "$SIGMA": "sum",
        "$NET_ATT": "cost",
    }

    assert set(templates.values()) <= set(handler.supported_templates())
    for template in templates.values():
        result = handler.execute(template, model, bindings)
        assert result["status"] == "success", template


def test_master_category_2_edge_metrics_have_handcoded_values() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category2Handler()
    templates = _master_templates("Category_2")
    base = {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "B Middle", "$ACT_Z": "C Branch", "$SIGMA": "sum"}

    assert handler.execute(templates["OCPM_GEN_026"], model, base)["value"] == 1
    assert handler.execute(templates["OCPM_GEN_027"], model, base)["value"] == 3600.0
    assert handler.execute(templates["OCPM_GEN_030"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_031"], model, base)["value"] == "A Start -> B Middle"
    assert handler.execute(templates["OCPM_GEN_033"], model, base)["value"] == ["A Start -> B Middle", "A Start -> C Branch"]
    assert handler.execute(templates["OCPM_GEN_035"], model, base)["value"] is False
    assert handler.execute(templates["OCPM_GEN_043"], model, base)["value"] == 0.5
    assert handler.execute(templates["OCPM_GEN_048"], model, base)["value"] is True
