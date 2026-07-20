from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.ingestion.reference_model import EventObjectRelation, ReferenceEvent, ReferenceModel, ReferenceObject
from evaluation.preconditions.engine import PreconditionEngine
from evaluation.templates.instantiation_engine import VariableInstantiationEngine
from evaluation.tests.test_instantiation import _template

ROOT = Path(__file__).resolve().parents[2]
CATEGORY_1_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category1_node_activity.jsonocel"
CATEGORY_4_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category4_multi_object_sync.jsonocel"


def test_membership_precondition_passes_and_fails_against_fixture() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = PreconditionEngine()

    passed = engine.evaluate("$OT_A in ocel.object_types", model, {"$OT_A": "Order"})
    failed = engine.evaluate("$OT_A in ocel.object_types", model, {"$OT_A": "Missing"})

    assert passed.status == "passed"
    assert "present" in passed.explanation
    assert failed.status == "failed"
    assert "not present" in failed.explanation


def test_object_type_has_events_predicate_passes_and_fails() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = PreconditionEngine()

    passed = engine.evaluate("object_type_has_events($OT_A)", model, {"$OT_A": "Order"})
    failed = engine.evaluate("object_type_has_events($OT_A)", model, {"$OT_A": "Missing"})

    assert passed.status == "passed"
    assert "6 related events" in passed.explanation
    assert failed.status == "failed"
    assert "no related events" in failed.explanation


def test_at_least_two_activities_for_object_type_predicate_passes_and_fails() -> None:
    model = load_ocel(CATEGORY_4_FIXTURE)
    engine = PreconditionEngine()

    passed = engine.evaluate("at_least_two_activities_for_object_type($OT_A)", model, {"$OT_A": "Item"})
    failed = engine.evaluate("at_least_two_activities_for_object_type($OT_A)", model, {"$OT_A": "Missing"})

    assert passed.status == "passed"
    assert "3 activities" in passed.explanation
    assert failed.status == "failed"
    assert "fewer than two activities" in failed.explanation


def test_unknown_precondition_is_unsupported_not_crashing() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = PreconditionEngine()

    unknown_predicate = engine.evaluate("unknown_predicate($ACT_X, $ACT_Y, $OT_A)", model, {"$OT_A": "Order"})
    unsupported_syntax = engine.evaluate("$ACT_X == $ACT_Y", model, {"$ACT_X": "A Start", "$ACT_Y": "B Middle"})
    missing_binding = engine.evaluate("$OT_A in ocel.object_types", model, {})

    assert unknown_predicate.status == "unsupported"
    assert "Unsupported predicate" in unknown_predicate.explanation
    assert unsupported_syntax.status == "unsupported"
    assert "Unsupported precondition syntax" in unsupported_syntax.explanation
    assert missing_binding.status == "unsupported"
    assert "No binding provided" in missing_binding.explanation


def test_inequality_precondition_passes_fails_and_handles_missing_binding() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = PreconditionEngine()

    passed = engine.evaluate("$ACT_X != $ACT_Y", model, {"$ACT_X": "A Start", "$ACT_Y": "B Middle"})
    failed = engine.evaluate("$ACT_X != $ACT_Y", model, {"$ACT_X": "A Start", "$ACT_Y": "A Start"})
    missing = engine.evaluate("$ACT_X != $ACT_Y", model, {"$ACT_X": "A Start"})

    assert passed.status == "passed"
    assert "differs" in passed.explanation
    assert failed.status == "failed"
    assert "equals" in failed.explanation
    assert missing.status == "unsupported"
    assert "No binding provided" in missing.explanation


def test_evaluate_all_integrates_with_instantiated_variables() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    template = _template(
        ["$OT_A", "$ACT_X"],
        preconditions=[
            "$OT_A in ocel.object_types",
            "$ACT_X in ocel.activities",
            "object_type_has_events($OT_A)",
            "at_least_two_activities_for_object_type($OT_A)",
        ],
    )
    instance = VariableInstantiationEngine().instantiate_template(template, model)[0]
    results = PreconditionEngine().evaluate_all(template.preconditions, model, instance.runtime_variables_used)

    assert [result.status for result in results] == ["passed", "passed", "passed", "passed"]
    assert results[0].precondition == "$OT_A in ocel.object_types"
    assert instance.runtime_variables_used == {"$ACT_X": "A Start", "$OT_A": "Order"}


def test_unbound_object_type_predicate_uses_safe_existential_fallback() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    result = PreconditionEngine().evaluate("at_least_two_activities_for_object_type($OT_A)", model, {})

    assert result.status == "passed"
    assert "passed existentially" in result.explanation


def test_edge_exists_predicate_passes_and_fails_against_fixture() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = PreconditionEngine()

    passed = engine.evaluate(
        "edge_exists($ACT_Y, $ACT_X, $OT_A)",
        model,
        {"$ACT_Y": "A Start", "$ACT_X": "B Middle", "$OT_A": "Order"},
    )
    failed = engine.evaluate(
        "edge_exists($ACT_Y, $ACT_X, $OT_A)",
        model,
        {"$ACT_Y": "B Middle", "$ACT_X": "A Start", "$OT_A": "Order"},
    )

    assert passed.status == "passed"
    assert "exists" in passed.explanation
    assert "count 1" in passed.explanation
    assert failed.status == "failed"
    assert "does not exist" in failed.explanation


def test_has_attribute_predicate_passes_for_object_and_event_attributes_and_fails() -> None:
    model = ReferenceModel.build(
        events=[
            ReferenceEvent(
                event_id="e1",
                activity="Create",
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
                attributes={"cost": 12.5},
            )
        ],
        objects=[
            ReferenceObject(
                object_id="o1",
                object_type="Order",
                attributes={"priority": "high"},
            )
        ],
        relations=[EventObjectRelation(event_id="e1", object_id="o1", object_type="Order")],
    )
    engine = PreconditionEngine()

    object_attr = engine.evaluate("has_attribute($OT_A, $ATTR_NAME)", model, {"$OT_A": "Order", "$ATTR_NAME": "priority"})
    event_attr = engine.evaluate("has_attribute($OT_A, $ATTR_NAME)", model, {"$OT_A": "Order", "$ATTR_NAME": "cost"})
    missing_attr = engine.evaluate("has_attribute($OT_A, $ATTR_NAME)", model, {"$OT_A": "Order", "$ATTR_NAME": "missing"})

    assert object_attr.status == "passed"
    assert "object(s)" in object_attr.explanation
    assert event_attr.status == "passed"
    assert "event(s)" in event_attr.explanation
    assert missing_attr.status == "failed"
    assert "does not exist" in missing_attr.explanation


def test_master_structural_predicates_pass_and_fail_against_fixtures() -> None:
    model = load_ocel(ROOT / "evaluation" / "fixtures" / "ocel" / "tiny_ocel2.jsonocel")
    engine = PreconditionEngine()

    path = engine.evaluate(
        "path_exists($ACT_X, $ACT_Y, $OT_A)",
        model,
        {"$ACT_X": "A Start", "$ACT_Y": "D End", "$OT_A": "Order"},
    )
    no_path = engine.evaluate(
        "path_exists($ACT_X, $ACT_Y, $OT_A)",
        model,
        {"$ACT_X": "D End", "$ACT_Y": "A Start", "$OT_A": "Order"},
    )
    cooccurs = engine.evaluate("object_types_cooccur($OT_A, $OT_B)", model, {"$OT_A": "Order", "$OT_B": "Item"})
    sync = engine.evaluate("synchronization_observable($OT_A, $OT_B)", model, {"$OT_A": "Order", "$OT_B": "Item"})
    trace = engine.evaluate("trace_exists_for_object_type($OT_A)", model, {"$OT_A": "Order"})
    declare = engine.evaluate(
        "declare_constraint_applicable($ACT_X, $ACT_Y, $OT_A)",
        model,
        {"$ACT_X": "A Start", "$ACT_Y": "D End", "$OT_A": "Order"},
    )

    assert path.status == "passed"
    assert no_path.status == "failed"
    assert cooccurs.status == "passed"
    assert sync.status == "passed"
    assert trace.status == "passed"
    assert declare.status == "passed"


def test_numeric_attribute_and_loop_predicates_pass_and_fail() -> None:
    model = ReferenceModel.build(
        events=[
            ReferenceEvent("e1", "A", datetime(2024, 1, 1, tzinfo=timezone.utc), {"cost": 1.5}),
            ReferenceEvent("e2", "B", datetime(2024, 1, 1, 1, tzinfo=timezone.utc)),
            ReferenceEvent("e3", "A", datetime(2024, 1, 1, 2, tzinfo=timezone.utc)),
        ],
        objects=[ReferenceObject("o1", "Order")],
        relations=[
            EventObjectRelation("e1", "o1", "Order"),
            EventObjectRelation("e2", "o1", "Order"),
            EventObjectRelation("e3", "o1", "Order"),
        ],
    )
    engine = PreconditionEngine()

    numeric = engine.evaluate("numeric_attribute_exists($NET_ATT)", model, {"$NET_ATT": "cost"})
    missing_numeric = engine.evaluate("numeric_attribute_exists($NET_ATT)", model, {"$NET_ATT": "missing"})
    loop = engine.evaluate("loop_exists($ACT_X, $OT_A)", model, {"$ACT_X": "A", "$OT_A": "Order"})
    no_loop = engine.evaluate("loop_exists($ACT_X, $OT_A)", model, {"$ACT_X": "C", "$OT_A": "Order"})

    assert numeric.status == "passed"
    assert missing_numeric.status == "failed"
    assert loop.status == "passed"
    assert no_loop.status == "failed"


def test_advanced_predicates_still_do_not_use_forbidden_eval_or_exec() -> None:
    for relative_path in ["evaluation/preconditions/engine.py", "evaluation/preconditions/predicates.py"]:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "eval(" not in text
        assert "exec(" not in text
