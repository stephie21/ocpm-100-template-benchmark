from __future__ import annotations

import json
from pathlib import Path

from evaluation.handlers.category_4 import Category4Handler
from evaluation.ingestion.ocel_loader import load_ocel

ROOT = Path(__file__).resolve().parents[2]
EDGE_TIME_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category2_edge_time.jsonocel"
TINY_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"


def _master_templates(category: str) -> dict[str, str]:
    data = json.loads((ROOT / "evaluation" / "data" / "OCPM_BENCHMARK_Q.json").read_text(encoding="utf-8"))
    return {
        entry["template_id"]: entry["analyst_question_template"]
        for entry in data
        if entry["category"] == category
    }


def test_average_throughput_time_for_direct_pairs_matches_edge_time_fixture() -> None:
    model = load_ocel(EDGE_TIME_FIXTURE)
    handler = Category4Handler()

    a_to_b = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "B Middle", "$OT_A": "Order"},
    )
    c_to_d = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "C Branch", "$ACT_X": "D End", "$OT_A": "Order"},
    )

    assert a_to_b["status"] == "success"
    assert a_to_b["value"] == 3600.0
    assert "eventually-follows" in a_to_b["message"]
    assert c_to_d["status"] == "success"
    assert c_to_d["value"] == 7200.0


def test_average_throughput_time_uses_next_eventually_following_activity() -> None:
    model = load_ocel(EDGE_TIME_FIXTURE)
    result = Category4Handler().execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "D End", "$OT_A": "Order"},
    )

    assert result["status"] == "success"
    assert result["value"] == 9450.0
    assert "2 pair(s)" in result["message"]


def test_tiny_fixture_multi_object_type_throughput_values_are_exact() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category4Handler()

    order_a_to_d = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "D End", "$OT_A": "Order"},
    )
    item_a_to_d = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "D End", "$OT_A": "Item"},
    )

    assert order_a_to_d["status"] == "success"
    assert order_a_to_d["value"] == 9000.0
    assert item_a_to_d["status"] == "success"
    assert item_a_to_d["value"] == 7200.0


def test_no_valid_transition_returns_success_with_none_value() -> None:
    model = load_ocel(EDGE_TIME_FIXTURE)
    result = Category4Handler().execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "D End", "$ACT_X": "A Start", "$OT_A": "Order"},
    )

    assert result["status"] == "success"
    assert result["value"] is None
    assert "No eventually-follows throughput pairs" in result["message"]


def test_missing_bindings_and_unsupported_template_return_error() -> None:
    model = load_ocel(EDGE_TIME_FIXTURE)
    handler = Category4Handler()

    missing_x = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$OT_A": "Order"},
    )
    missing_y = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_X": "D End", "$OT_A": "Order"},
    )
    missing_object_type = handler.execute(
        Category4Handler.THROUGHPUT_TIME_QUESTION,
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "D End"},
    )
    unsupported = handler.execute("Unsupported Category 4 question", model, {})

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
    assert "Unsupported Category 4 question template" in unsupported["message"]


def test_all_master_category_4_templates_are_supported_and_dispatch_successfully() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category4Handler()
    templates = _master_templates("Category_4")
    bindings = {
        "$OT_A": "Order",
        "$OT_B": "Item",
        "$ACT_X": "A Start",
        "$ACT_Y": "D End",
        "$SIGMA": "sum",
    }

    assert set(templates.values()) <= set(handler.supported_templates())
    for template in templates.values():
        result = handler.execute(template, model, bindings)
        assert result["status"] == "success", template


def test_master_category_4_interaction_and_constraint_values_are_handcoded() -> None:
    model = load_ocel(TINY_FIXTURE)
    handler = Category4Handler()
    templates = _master_templates("Category_4")
    base = {"$OT_A": "Order", "$OT_B": "Item", "$ACT_X": "A Start", "$ACT_Y": "D End", "$SIGMA": "sum"}

    assert handler.execute(templates["OCPM_GEN_076"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_077"], model, base)["value"] == 3
    assert handler.execute(templates["OCPM_GEN_078"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_079"], model, base)["value"] == 1
    assert handler.execute(templates["OCPM_GEN_080"], model, base)["value"] == "A Start"
    assert handler.execute(templates["OCPM_GEN_081"], model, base)["value"] == 1
    assert handler.execute(templates["OCPM_GEN_082"], model, base)["value"] == 2
    assert handler.execute(templates["OCPM_GEN_089"], model, base)["value"] == ["A Start", "B Middle", "D End"]
    assert handler.execute(templates["OCPM_GEN_090"], model, base)["value"] == "Item|Order"
    assert handler.execute(templates["OCPM_GEN_094"], model, base)["value"] is True
    assert handler.execute(templates["OCPM_GEN_095"], model, base)["value"] == 0
    assert handler.execute(templates["OCPM_GEN_098"], model, base)["value"] is False
    assert handler.execute(templates["OCPM_GEN_099"], model, base)["value"] == 2
    assert handler.execute(templates["OCPM_GEN_100"], model, base)["value"] == ["Item|Order"]
