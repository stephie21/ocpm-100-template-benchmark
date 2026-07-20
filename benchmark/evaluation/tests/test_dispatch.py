from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from evaluation.handlers.category_1 import Category1Handler
from evaluation.handlers.category_2 import Category2Handler
from evaluation.handlers.category_3 import Category3Handler
from evaluation.handlers.category_4 import Category4Handler
from evaluation.handlers.dispatch import dispatch_question, execute_reference_metric
from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.ingestion.reference_model import DirectlyFollowsEdge, EventObjectRelation, ReferenceEvent, ReferenceModel, ReferenceObject
from evaluation.schemas.benchmark import BenchmarkTemplate

ROOT = Path(__file__).resolve().parents[2]
TINY_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"


def _handlers():
    return {
        "Category_1": Category1Handler(),
        "Category_2": Category2Handler(),
        "Category_3": Category3Handler(),
        "Category_4": Category4Handler(),
    }


def _template(template_id: str, category: str, target_metric: str, question: str = "Changed wording") -> BenchmarkTemplate:
    return BenchmarkTemplate.model_validate(
        {
            "template_id": template_id,
            "category": category,
            "formal_pattern": "dispatch test",
            "dimensions_tested": ["factual_correctness"],
            "analyst_question_template": question,
            "runtime_variables": ["$OT_A", "$ACT_X", "$ACT_Y"],
            "preconditions": [],
            "evaluation_logic": {
                "expected_tool_chain": [{"tool": "reference_handler", "required": True}],
                "mathematical_assertion": {
                    "target_metric": target_metric,
                    "aggregation_applied": "none",
                    "result_type": "integer",
                    "lookup_path": "handler_derived",
                },
            },
        }
    )


def test_template_dispatch_uses_template_id_not_question_text() -> None:
    model = load_ocel(TINY_FIXTURE)
    template = _template("OCPM_GEN_001", "Category_1", "node_out_degree")

    result = execute_reference_metric(
        template,
        model,
        {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "B Middle"},
        _handlers(),
    )

    assert dispatch_question(template) == Category1Handler.NODE_OUT_DEGREE_QUESTION
    assert result["status"] == "success"
    assert result["value"] == 2


def test_target_metric_dispatch_works_without_known_template_id() -> None:
    model = load_ocel(TINY_FIXTURE)
    template = _template("LOCAL_TEST", "Category_3", "eventual_reachability")

    result = execute_reference_metric(
        template,
        model,
        {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "D End"},
        _handlers(),
    )

    assert dispatch_question(template) == Category3Handler.REACHABLE_QUESTION
    assert result["status"] == "success"
    assert result["value"] is True


def test_unsupported_metric_fails_closed() -> None:
    model = load_ocel(TINY_FIXTURE)
    template = _template("OCPM_GEN_082", "Category_4", "synchronization_candidate")

    result = execute_reference_metric(
        template,
        model,
        {"$OT_A": "Order", "$OT_B": "Item", "$ACT_X": "A Start", "$ACT_Y": "D End"},
        _handlers(),
    )

    assert result["status"] == "unsupported"
    assert result["value"] is None
    assert "synchronization_candidate" in result["message"]


def test_missing_duration_data_returns_no_reference_value() -> None:
    model = ReferenceModel(
        object_types=("Order",),
        activities=("A Start", "B Middle"),
        events=(
            ReferenceEvent("e1", "A Start", datetime(2024, 1, 1, tzinfo=timezone.utc)),
            ReferenceEvent("e2", "B Middle", datetime(2024, 1, 1, 1, tzinfo=timezone.utc)),
        ),
        objects=(ReferenceObject("o1", "Order"),),
        event_object_relations=(
            EventObjectRelation("e1", "o1", "Order"),
            EventObjectRelation("e2", "o1", "Order"),
        ),
        directly_follows_edges={"Order": (DirectlyFollowsEdge("A Start", "B Middle", 1, ("o1",)),)},
    )
    template = _template("OCPM_GEN_033", "Category_2", "avg_edge_duration")

    result = execute_reference_metric(
        template,
        model,
        {"$OT_A": "Order", "$ACT_X": "A Start", "$ACT_Y": "B Middle"},
        _handlers(),
    )

    assert result["status"] == "success"
    assert result["value"] is None
