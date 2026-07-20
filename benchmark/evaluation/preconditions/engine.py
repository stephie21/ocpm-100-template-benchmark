from __future__ import annotations
from dataclasses import dataclass
from evaluation.handlers.base import activities_for_type

@dataclass(frozen=True)
class PreconditionResult:
    status: str
    explanation: str

class PreconditionEngine:
    def evaluate(self, expression: str, model, bindings: dict[str, str] | None = None) -> PreconditionResult:
        bindings=bindings or {}
        if " in ocel.object_types" in expression:
            value=expression.split(" in ")[0].strip()
            value=bindings.get(value, value)
            if value in model.object_types:
                return PreconditionResult("passed", f"{value} present in ocel.object_types")
            return PreconditionResult("failed", f"{value} not present in ocel.object_types")
        if " in ocel.activities" in expression:
            value=expression.split(" in ")[0].strip()
            value=bindings.get(value, value)
            if value in model.activities:
                return PreconditionResult("passed", f"{value} present in ocel.activities")
            return PreconditionResult("failed", f"{value} not present in ocel.activities")
        if expression.startswith("object_type_has_events("):
            token=expression[len("object_type_has_events("):-1]
            ot=bindings.get(token, token)
            count=sum(1 for event in model.events if model.object_ids_for_event(event.event_id, ot))
            if count:
                return PreconditionResult("passed", f"{ot} has {count} related events")
            return PreconditionResult("failed", f"{ot} has no related events")
        if expression.startswith("at_least_two_activities_for_object_type("):
            token=expression[len("at_least_two_activities_for_object_type("):-1]
            ot=bindings.get(token, token)
            count=len(activities_for_type(model, ot))
            if count >= 2:
                return PreconditionResult("passed", f"{ot} has {count} activities")
            return PreconditionResult("failed", f"{ot} has fewer than two activities")
        return PreconditionResult("unsupported", f"Unsupported precondition syntax: {expression}")

    def evaluate_all(self, expressions, model, bindings=None):
        results=tuple(self.evaluate(expression, model, bindings) for expression in expressions)
        if any(result.status == "failed" for result in results):
            status="failed"
        elif any(result.status == "unsupported" for result in results):
            status="unsupported"
        else:
            status="passed"
        return status, results
