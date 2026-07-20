from __future__ import annotations

from pathlib import Path

import pytest

from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.schemas.benchmark import BenchmarkTemplate
from evaluation.templates.instantiation_engine import (
    VariableDefinition,
    VariableInstantiationEngine,
    VariableResolutionError,
)

ROOT = Path(__file__).resolve().parents[2]
CATEGORY_1_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category1_node_activity.jsonocel"
CATEGORY_3_FIXTURE = ROOT / "evaluation" / "fixtures" / "ocel" / "category3_path_reachability.jsonocel"


def _template(
    runtime_variables: list[str],
    question: str | None = None,
    lookup_path: str = "ocdfg.nodes[$ACT_X].metrics[$OT_A].out_degree",
    preconditions: list[str] | None = None,
) -> BenchmarkTemplate:
    return BenchmarkTemplate.model_validate(
        {
            "template_id": "OCPM_GEN_001",
            "category": "Category_1",
            "formal_pattern": "Test template",
            "dimensions_tested": ["factual_correctness"],
            "analyst_question_template": question or "What is $ACT_X for $OT_A?",
            "runtime_variables": runtime_variables,
            "preconditions": preconditions or ["$OT_A in ocel.object_types", "$ACT_X in ocel.activities"],
            "evaluation_logic": {
                "expected_tool_chain": [{"tool": "fetch_ocel_metadata", "required": True}],
                "mathematical_assertion": {
                    "target_metric": "node_out_degree",
                    "aggregation_applied": "none",
                    "result_type": "integer",
                    "lookup_path": lookup_path,
                },
            },
        }
    )


def test_instantiates_minimal_template_from_category_1_fixture_domains() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = VariableInstantiationEngine()
    template = _template(["$OT_A", "$ACT_X"])

    instances = engine.instantiate_template(template, model)

    assert len(instances) == 4
    assert [instance.runtime_variables_used for instance in instances] == [
        {"$ACT_X": "A Start", "$OT_A": "Order"},
        {"$ACT_X": "B Middle", "$OT_A": "Order"},
        {"$ACT_X": "C Branch", "$OT_A": "Order"},
        {"$ACT_X": "D End", "$OT_A": "Order"},
    ]
    assert instances[0].analyst_question == "What is A Start for Order?"
    assert instances[0].lookup_path == "ocdfg.nodes[A Start].metrics[Order].out_degree"
    assert instances[0].preconditions == ("Order in ocel.object_types", "A Start in ocel.activities")
    assert instances[0].template is template


def test_direct_lookup_path_navigation_uses_reference_model_only() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = VariableInstantiationEngine()

    assert engine.resolve_lookup_path("activities", model) == ("A Start", "B Middle", "C Branch", "D End")
    assert engine.resolve_lookup_path("object_types[0]", model) == "Order"
    assert engine.resolve_lookup_path("model.events[0].activity", model) == "A Start"
    assert engine.resolve_lookup_path("timestamps[c1_e1]", model).isoformat() == "2024-01-01T09:00:00+00:00"


def test_explicit_variable_definition_lookup_path_and_type_validation() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = VariableInstantiationEngine(
        {
            "$TARGET_ACTIVITY": VariableDefinition(
                name="$TARGET_ACTIVITY",
                lookup_path="activities",
                value_type="str",
            )
        }
    )
    template = _template(["$TARGET_ACTIVITY"], question="Investigate $TARGET_ACTIVITY", lookup_path="activities[$TARGET_ACTIVITY]", preconditions=["$TARGET_ACTIVITY in ocel.activities"])

    instances = engine.instantiate_template(template, model)

    assert [instance.runtime_variables_used["$TARGET_ACTIVITY"] for instance in instances] == [
        "A Start",
        "B Middle",
        "C Branch",
        "D End",
    ]
    assert instances[2].analyst_question == "Investigate C Branch"


def test_category_3_activity_domain_instantiates_reachability_fixture() -> None:
    model = load_ocel(CATEGORY_3_FIXTURE)
    engine = VariableInstantiationEngine()
    template = _template(["$ACT_X"], question="Which nodes are reachable from $ACT_X?", lookup_path="activities", preconditions=["$ACT_X in ocel.activities"])

    instances = engine.instantiate_template(template, model)

    assert [instance.runtime_variables_used["$ACT_X"] for instance in instances] == ["A", "B", "C", "D"]
    assert instances[0].analyst_question == "Which nodes are reachable from A?"


def test_invalid_lookup_path_raises_precise_resolution_error() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)
    engine = VariableInstantiationEngine()

    with pytest.raises(VariableResolutionError, match="Unknown lookup root"):
        engine.resolve_lookup_path("missing_root.values", model)

    with pytest.raises(VariableResolutionError, match="Missing attribute"):
        engine.resolve_lookup_path("model.not_a_field", model)

    with pytest.raises(VariableResolutionError, match="Sequence index must be numeric"):
        engine.resolve_lookup_path("activities[first]", model)


def test_unknown_or_empty_variable_domains_are_rejected() -> None:
    model = load_ocel(CATEGORY_1_FIXTURE)

    with pytest.raises(VariableResolutionError, match="No domain lookup configured"):
        VariableInstantiationEngine().instantiate_template(_template(["$UNKNOWN"]), model)

    with pytest.raises(VariableResolutionError, match="empty domain"):
        VariableInstantiationEngine().instantiate_template(_template(["$NET_ATT"]), model)
