from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from .reference_model import DirectlyFollowsEdge, EventObjectRelation, ReferenceEvent, ReferenceModel, ReferenceObject


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_ocel(path: str | Path) -> ReferenceModel:
    path = Path(path)
    if path.suffix != ".jsonocel":
        raise ValueError(f"Unsupported OCEL file extension: {path.suffix}")
    data = json.loads(path.read_text(encoding="utf-8"))
    events = tuple(ReferenceEvent(str(e["id"]), str(e["activity"]), _parse_time(str(e["timestamp"]))) for e in data["events"])
    objects = tuple(ReferenceObject(str(o["id"]), str(o["type"])) for o in data["objects"])
    raw_relations = data["relations"]
    object_types = tuple(dict.fromkeys(o.object_type for o in objects))
    activities = tuple(dict.fromkeys(e.activity for e in events))
    event_map = {event.event_id: event for event in events}
    object_map = {obj.object_id: obj for obj in objects}
    relations = tuple(
        EventObjectRelation(str(r["event_id"]), str(r["object_id"]), object_map[str(r["object_id"])].object_type, str(r.get("qualifier", "")))
        for r in raw_relations if str(r["object_id"]) in object_map
    )
    by_object: dict[str, list[ReferenceEvent]] = defaultdict(list)
    for rel in relations:
        if rel.object_id in object_map and rel.event_id in event_map:
            by_object[rel.object_id].append(event_map[rel.event_id])
    edge_acc: dict[str, dict[tuple[str, str], dict[str, object]]] = defaultdict(dict)
    for object_id, object_events in by_object.items():
        obj_type = object_map[object_id].object_type
        ordered = sorted(object_events, key=lambda event: event.timestamp)
        for left, right in zip(ordered, ordered[1:]):
            bucket = edge_acc[obj_type].setdefault((left.activity, right.activity), {"object_ids": [], "durations": []})
            bucket["object_ids"].append(object_id)
            bucket["durations"].append((right.timestamp - left.timestamp).total_seconds())
    edges = {
        obj_type: tuple(
            DirectlyFollowsEdge(source, target, len(values["object_ids"]), tuple(values["object_ids"]), tuple(values["durations"]))
            for (source, target), values in transitions.items()
        )
        for obj_type, transitions in edge_acc.items()
    }
    return ReferenceModel(
        object_types=object_types,
        activities=activities,
        events=events,
        objects=objects,
        event_object_relations=relations,
        directly_follows_edges=edges,
        support_status={"json_ocel": "supported (minimal local JSON)", "sqlite_ocel": "not supported in standalone"},
    )
