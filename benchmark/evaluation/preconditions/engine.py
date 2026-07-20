from __future__ import annotations

from dataclasses import dataclass

from evaluation.handlers.base import (
    activities_for_type,
    edge_count,
    edge_durations,
    object_ids,
    reachable,
    shortest_path,
)


@dataclass(frozen=True)
class PreconditionResult:
    status: str
    explanation: str


class PreconditionEngine:
    def evaluate(self, expression: str, model, bindings: dict[str, str] | None = None) -> PreconditionResult:
        bindings = bindings or {}
        expression = expression.strip()

        if " in ocel.object_types" in expression:
            value = self._bind(expression.split(" in ")[0], bindings)
            if value is None:
                return PreconditionResult("unsupported", f"No binding provided for {expression.split(' in ')[0].strip()}")
            return self._result(value in model.object_types, f"{value} present in ocel.object_types", f"{value} not present in ocel.object_types")
        if " in ocel.activities" in expression:
            value = self._bind(expression.split(" in ")[0], bindings)
            if value is None:
                return PreconditionResult("unsupported", f"No binding provided for {expression.split(' in ')[0].strip()}")
            return self._result(value in model.activities, f"{value} present in ocel.activities", f"{value} not present in ocel.activities")

        if expression == "timestamps_available":
            return self._result(all(event.timestamp is not None for event in model.events), "timestamps are available", "timestamps are missing")
        if expression == "$OT_A != $OT_B":
            left = self._bind("$OT_A", bindings)
            right = self._bind("$OT_B", bindings)
            if left is None or right is None:
                return PreconditionResult("unsupported", "No binding provided for object-type inequality")
            return self._result(left != right, f"{left} and {right} are distinct", f"{left} and {right} are not distinct")

        name, args, op, threshold = self._parse_call(expression)
        if name is None:
            return PreconditionResult("unsupported", f"Unsupported precondition syntax: {expression}")

        values = [self._bind(arg, bindings) for arg in args]
        if any(value is None for value in values):
            return PreconditionResult("unsupported", f"No binding provided for {expression}")
        ok = self._evaluate_predicate(name, values, op, threshold, model)
        if ok is None:
            return PreconditionResult("unsupported", f"Unsupported precondition syntax: {expression}")
        rendered = f"{name}({', '.join(values)})"
        return self._result(ok, f"{rendered} passed", f"{rendered} failed")

    def evaluate_all(self, expressions, model, bindings=None):
        results = tuple(self.evaluate(expression, model, bindings) for expression in expressions)
        if any(result.status == "failed" for result in results):
            status = "failed"
        elif any(result.status == "unsupported" for result in results):
            status = "unsupported"
        else:
            status = "passed"
        return status, results

    def _evaluate_predicate(self, name: str, args: list[str], op: str | None, threshold: int | None, model) -> bool | None:
        if name == "object_type_exists" and len(args) == 1:
            return args[0] in model.object_types
        if name == "activity_exists" and len(args) == 1:
            return args[0] in model.activities
        if name == "activity_exists_for_type" and len(args) == 2:
            activity, object_type = args
            return activity in activities_for_type(model, object_type)
        if name == "has_activities_for_type" and len(args) == 1:
            return bool(activities_for_type(model, args[0]))
        if name == "k_defined":
            return True
        if name == "has_start_events_for_type" and len(args) == 1:
            return bool(self._source_activities(model, args[0]))
        if name == "object_frequency" and len(args) == 1 and op == ">" and threshold is not None:
            return self._compare(len(object_ids(model, args[0])), op, threshold)
        if name == "event_count_for_type" and len(args) == 1 and op == ">" and threshold is not None:
            return self._compare(self._event_count_for_type(model, args[0]), op, threshold)
        if name == "edge_exists" and len(args) == 3:
            return edge_count(model, args[0], args[1], args[2]) > 0
        if name == "edge_has_durations" and len(args) == 3:
            return bool(edge_durations(model, args[0], args[1], args[2]))
        if name == "has_duration_edges" and len(args) == 1:
            return any(edge.durations for edge in model.directly_follows_edges.get(args[0], ()))
        if name == "activity_has_outgoing_edges" and len(args) == 2:
            return any(edge.source == args[0] for edge in model.directly_follows_edges.get(args[1], ()))
        if name == "sum_outgoing_weight" and len(args) == 2 and op == ">" and threshold is not None:
            total = sum(edge.count for edge in model.directly_follows_edges.get(args[1], ()) if edge.source == args[0])
            return self._compare(total, op, threshold)
        if name == "duration_count" and len(args) == 3 and op == ">=" and threshold is not None:
            return self._compare(len(edge_durations(model, args[0], args[1], args[2])), op, threshold)
        if name == "reachable" and len(args) == 3:
            return reachable(model, args[0], args[1], args[2])
        if name == "has_source_activities" and len(args) == 1:
            return bool(self._source_activities(model, args[0]))
        if name == "has_sink_activities" and len(args) == 1:
            return bool(self._sink_activities(model, args[0]))
        if name == "has_edges" and len(args) == 1:
            return bool(model.directly_follows_edges.get(args[0], ()))
        if name == "shortest_path_length" and len(args) == 3 and op == ">=" and threshold is not None:
            path = shortest_path(model, args[0], args[1], args[2])
            return self._compare(max(0, len(path) - 1), op, threshold)
        if name == "has_reachable_sink" and len(args) == 2:
            return any(reachable(model, args[0], sink, args[1]) or args[0] == sink for sink in self._sink_activities(model, args[1]))
        if name == "has_multi_object_events" and len(args) == 1:
            return any(event.activity == args[0] and len({rel.object_type for rel in model.event_object_relations if rel.event_id == event.event_id}) > 1 for event in model.events)
        if name == "has_pair_events" and len(args) == 3:
            return self._has_pair_event(model, args[0], args[1], args[2])
        if name == "has_shared_activities" and len(args) == 2:
            return bool(set(activities_for_type(model, args[0])) & set(activities_for_type(model, args[1])))
        return None

    def _parse_call(self, expression: str) -> tuple[str | None, list[str], str | None, int | None]:
        op = None
        threshold = None
        call = expression
        for candidate in (">=", ">"):
            if candidate in expression:
                call, raw_threshold = expression.split(candidate, 1)
                op = candidate
                try:
                    threshold = int(raw_threshold.strip())
                except ValueError:
                    return None, [], op, None
                break
        if "(" not in call or not call.endswith(")"):
            return None, [], op, threshold
        name, raw_args = call.split("(", 1)
        args = [arg.strip() for arg in raw_args[:-1].split(",") if arg.strip()]
        return name.strip(), args, op, threshold

    def _bind(self, token: str, bindings: dict[str, str]) -> str | None:
        token = token.strip().strip("'\"")
        if "=" in token:
            value = token.split("=", 1)[1].strip().strip("'\"")
            if value.startswith("$"):
                return bindings.get(value)
            return value
        if token.startswith("$"):
            return bindings.get(token)
        return token

    def _result(self, condition: bool, passed: str, failed: str) -> PreconditionResult:
        if condition:
            return PreconditionResult("passed", passed)
        return PreconditionResult("failed", failed)

    def _compare(self, value: int, op: str, threshold: int) -> bool:
        if op == ">=":
            return value >= threshold
        if op == ">":
            return value > threshold
        return False

    def _event_count_for_type(self, model, object_type: str) -> int:
        return sum(1 for event in model.events if model.object_ids_for_event(event.event_id, object_type))

    def _source_activities(self, model, object_type: str) -> tuple[str, ...]:
        targets = {edge.target for edge in model.directly_follows_edges.get(object_type, ())}
        return tuple(activity for activity in activities_for_type(model, object_type) if activity not in targets)

    def _sink_activities(self, model, object_type: str) -> tuple[str, ...]:
        sources = {edge.source for edge in model.directly_follows_edges.get(object_type, ())}
        return tuple(activity for activity in activities_for_type(model, object_type) if activity not in sources)

    def _has_pair_event(self, model, activity: str, left_type: str, right_type: str) -> bool:
        for event in model.events:
            if event.activity != activity:
                continue
            types = {rel.object_type for rel in model.event_object_relations if rel.event_id == event.event_id}
            if left_type in types and right_type in types:
                return True
        return False
