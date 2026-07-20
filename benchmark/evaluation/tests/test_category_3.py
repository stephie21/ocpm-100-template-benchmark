from __future__ import annotations

import json
from pathlib import Path

from evaluation.handlers.category_3 import Category3Handler
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


def test_directly_follows_count_for_order_lifecycle_matches_tiny_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category3Handler()

    a_to_b = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "B Middle", "$OT_A": "Order"},
    )
    a_to_c = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "C Branch", "$OT_A": "Order"},
    )

    assert a_to_b["status"] == "success"
    assert a_to_b["value"] == 1
    assert "A Start" in a_to_b["message"]
    assert "B Middle" in a_to_b["message"]
    assert "Order" in a_to_b["message"]
    assert a_to_c["status"] == "success"
    assert a_to_c["value"] == 1


def test_directly_follows_count_for_item_lifecycle_matches_tiny_fixture() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = Category3Handler().execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "B Middle", "$ACT_X": "D End", "$OT_A": "Item"},
    )

    assert result["status"] == "success"
    assert result["value"] == 1


def test_existing_activities_without_specific_sequence_return_zero() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category3Handler()

    reverse_order = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "B Middle", "$ACT_X": "A Start", "$OT_A": "Order"},
    )
    cross_branch = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "B Middle", "$ACT_X": "C Branch", "$OT_A": "Order"},
    )

    assert reverse_order["status"] == "success"
    assert reverse_order["value"] == 0
    assert cross_branch["status"] == "success"
    assert cross_branch["value"] == 0


def test_missing_bindings_and_unsupported_template_return_error() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category3Handler()

    missing_x = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$OT_A": "Order"},
    )
    missing_y = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_X": "B Middle", "$OT_A": "Order"},
    )
    missing_object_type = handler.execute(
        Category3Handler.DIRECTLY_FOLLOWS_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "B Middle"},
    )
    unsupported = handler.execute("Unsupported Category 3 question", model, {})

    assert missing_x == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$ACT_X'",
    }
    assert missing_y == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$ACT_Y'",
    }
    assert missing_object_type == {
        "value": None,
        "status": "error",
        "message": "Missing required variable binding '$OT_A'",
    }
    assert unsupported["value"] is None
    assert unsupported["status"] == "error"
    assert "Unsupported Category 3 question template" in unsupported["message"]


def test_all_master_category_3_templates_are_supported_and_dispatch_successfully() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category3Handler()
    templates = _master_templates("Category_3")
    bindings = {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "D End", "$ACT_Z": "B Middle"}

    assert set(templates.values()) <= set(handler.supported_templates())
    for template in templates.values():
        result = handler.execute(template, model, bindings)
        assert result["status"] == "success", template


def test_master_category_3_path_metrics_have_handcoded_values() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category3Handler()
    templates = _master_templates("Category_3")
    base = {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "D End", "$ACT_Z": "B Middle"}

    assert handler.execute(templates["OCPM_GEN_051"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_052"], model, base)["value"] is False
    assert handler.execute(templates["OCPM_GEN_053"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_054"], model, base)["value"] == 2
    assert handler.execute(templates["OCPM_GEN_055"], model, base)["value"] == ["A Start", "B Middle", "D End"]
    assert handler.execute(templates["OCPM_GEN_056"], model, base)["value"] == ["B Middle", "C Branch", "D End"]
    assert handler.execute(templates["OCPM_GEN_057"], model, base)["value"] == ["A Start", "B Middle", "C Branch"]
    assert handler.execute(templates["OCPM_GEN_058"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_059"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_072"], model, base)["value"] == 3
    assert handler.execute(templates["OCPM_GEN_075"], model, base)["value"] == ["A Start -> B Middle", "B Middle -> D End"]
