from __future__ import annotations

from pathlib import Path

from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.preconditions.engine import PreconditionEngine

ROOT = Path(__file__).resolve().parents[2]
TINY_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel"


def test_cleaned_catalog_valid_precondition_passes() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate(
        "activity_exists_for_type($ACT_X,$OT_A)",
        model,
        {"$ACT_X": "A Start", "$OT_A": "Order"},
    )

    assert result.status == "passed"


def test_cleaned_catalog_failed_precondition_fails() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate(
        "edge_exists($ACT_X,$ACT_Y,$OT_A)",
        model,
        {"$ACT_X": "D End", "$ACT_Y": "A Start", "$OT_A": "Order"},
    )

    assert result.status == "failed"


def test_cleaned_catalog_missing_data_precondition_fails() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate(
        "edge_has_durations($ACT_X,$ACT_Y,$OT_A)",
        model,
        {"$ACT_X": "D End", "$ACT_Y": "A Start", "$OT_A": "Order"},
    )

    assert result.status == "failed"


def test_all_cleaned_catalog_precondition_syntaxes_are_supported() -> None:
    model = load_ocel(TINY_FIXTURE)
    engine = PreconditionEngine()
    bindings = {"$OT_A": "Order", "$OT_B": "Item", "$ACT_X": "A Start", "$ACT_Y": "D End"}
    expressions = [
        "object_type_exists($OT_A)",
        "activity_exists_for_type($ACT_X,$OT_A)",
        "has_activities_for_type($OT_A)",
        "k_defined(default=3)",
        "has_start_events_for_type($OT_A)",
        "object_frequency($OT_A)>0",
        "edge_exists($ACT_X,$ACT_Y,$OT_A)",
        "edge_has_durations($ACT_X,$ACT_Y,$OT_A)",
        "timestamps_available",
        "has_duration_edges($OT_A)",
        "activity_has_outgoing_edges($ACT_X,$OT_A)",
        "sum_outgoing_weight($ACT_X,$OT_A)>0",
        "duration_count($ACT_X,$ACT_Y,$OT_A)>=2",
        "reachable($ACT_X,$ACT_Y,$OT_A)",
        "has_source_activities($OT_A)",
        "has_sink_activities($OT_A)",
        "has_edges($OT_A)",
        "shortest_path_length($ACT_X,$ACT_Y,$OT_A)>=1",
        "has_reachable_sink($ACT_X,$OT_A)",
        "object_type_exists($OT_B)",
        "$OT_A != $OT_B",
        "activity_exists($ACT_X)",
        "activity_exists($ACT_Y)",
        "has_multi_object_events($ACT_X)",
        "has_pair_events($ACT_X,$OT_A,$OT_B)",
        "event_count_for_type($OT_A)>0",
        "has_edges($OT_B)",
        "has_shared_activities($OT_A,$OT_B)",
    ]

    statuses = [engine.evaluate(expression, model, bindings).status for expression in expressions]

    assert "unsupported" not in statuses


def test_missing_binding_is_unsupported() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate(
        "activity_exists_for_type($ACT_X,$OT_A)",
        model,
        {"$OT_A": "Order"},
    )

    assert result.status == "unsupported"


def test_malformed_numeric_threshold_is_unsupported() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate(
        "object_frequency($OT_A)>abc",
        model,
        {"$OT_A": "Order"},
    )

    assert result.status == "unsupported"


def test_named_argument_missing_binding_is_unsupported() -> None:
    model = load_ocel(TINY_FIXTURE)
    result = PreconditionEngine().evaluate("object_type_exists(object_type=$OT_A)", model, {})

    assert result.status == "unsupported"
