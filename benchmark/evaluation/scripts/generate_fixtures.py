from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "ocel"
EXPECTED_DIR = ROOT / "fixtures" / "expected"
LEGACY_EXPECTED_DIR = ROOT / "expected"

def _write(name: str, data: dict, assertions: dict | None = None) -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    LEGACY_EXPECTED_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURE_DIR / f"{name}.jsonocel").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    object_types = list(dict.fromkeys(o["type"] for o in data["objects"]))
    activities = list(dict.fromkeys(e["activity"] for e in data["events"]))
    object_map = {o["id"]: o["type"] for o in data["objects"]}
    event_map = {e["id"]: e for e in data["events"]}
    directly_follows = {}
    for object_type in object_types:
        edges = {}
        for obj in [o for o in data["objects"] if o["type"] == object_type]:
            rel_events = [event_map[r["event_id"]] for r in data["relations"] if r["object_id"] == obj["id"]]
            rel_events.sort(key=lambda event: event["timestamp"])
            for left, right in zip(rel_events, rel_events[1:]):
                edge = edges.setdefault((left["activity"], right["activity"]), {"source": left["activity"], "target": right["activity"], "count": 0, "object_ids": []})
                edge["count"] += 1
                edge["object_ids"].append(obj["id"])
        directly_follows[object_type] = list(edges.values())
    expected = {
        "object_types": object_types,
        "activities": activities,
        "event_count": len(data["events"]),
        "object_count": len(data["objects"]),
        "relation_count": len(data["relations"]),
        "objects": [{"object_id": o["id"], "object_type": o["type"]} for o in data["objects"]],
        "timestamps": {e["id"]: e["timestamp"] for e in data["events"]},
        "directly_follows": directly_follows,
        "assertions": assertions or {},
    }
    text = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    (EXPECTED_DIR / f"{name}_expected.json").write_text(text, encoding="utf-8")
    (LEGACY_EXPECTED_DIR / f"{name}_expected_values.json").write_text(text, encoding="utf-8")

def _tiny() -> dict:
    return {
        "events": [
            {"id": "e1", "activity": "A Start", "timestamp": "2024-01-01T00:00:00+00:00"},
            {"id": "e2", "activity": "B Middle", "timestamp": "2024-01-01T01:00:00+00:00"},
            {"id": "e3", "activity": "D End", "timestamp": "2024-01-01T02:00:00+00:00"},
            {"id": "e4", "activity": "A Start", "timestamp": "2024-01-02T00:00:00+00:00"},
            {"id": "e5", "activity": "C Branch", "timestamp": "2024-01-02T01:30:00+00:00"},
            {"id": "e6", "activity": "D End", "timestamp": "2024-01-02T03:00:00+00:00"},
        ],
        "objects": [{"id": "o1", "type": "Order"}, {"id": "o2", "type": "Order"}, {"id": "i1", "type": "Item"}],
        "relations": [
            {"event_id": "e1", "object_id": "o1"}, {"event_id": "e2", "object_id": "o1"}, {"event_id": "e3", "object_id": "o1"},
            {"event_id": "e4", "object_id": "o2"}, {"event_id": "e5", "object_id": "o2"}, {"event_id": "e6", "object_id": "o2"},
            {"event_id": "e1", "object_id": "i1"}, {"event_id": "e2", "object_id": "i1"}, {"event_id": "e3", "object_id": "i1"},
        ],
    }

def _order_only() -> dict:
    data = _tiny()
    data["objects"] = data["objects"][:2]
    data["relations"] = [r for r in data["relations"] if r["object_id"].startswith("o")]
    return data

def _edge_time() -> dict:
    return {
        "events": [
            {"id": "p1a", "activity": "A Start", "timestamp": "2024-01-01T00:00:00+00:00"},
            {"id": "p1b", "activity": "B Middle", "timestamp": "2024-01-01T01:00:00+00:00"},
            {"id": "p1d", "activity": "D End", "timestamp": "2024-01-01T02:00:00+00:00"},
            {"id": "p2a", "activity": "A Start", "timestamp": "2024-01-02T00:00:00+00:00"},
            {"id": "p2c", "activity": "C Branch", "timestamp": "2024-01-02T01:15:00+00:00"},
            {"id": "p2d", "activity": "D End", "timestamp": "2024-01-02T03:15:00+00:00"},
        ],
        "objects": [{"id": "o1", "type": "Order"}, {"id": "o2", "type": "Order"}],
        "relations": [{"event_id": event_id, "object_id": obj} for obj, ids in {"o1": ["p1a", "p1b", "p1d"], "o2": ["p2a", "p2c", "p2d"]}.items() for event_id in ids],
    }

def main() -> None:
    _write("tiny_ocel2", _tiny())
    _write("category1_node_activity", _order_only(), {
        "out_degree(A Start)": 2,
        "in_degree(D End)": 2,
        "start_frequency(A Start)": 2,
        "end_frequency(D End)": 2,
        "zero_in_degree": ["A Start"],
        "zero_out_degree": ["D End"],
    })
    _write("category2_edge_time", _edge_time())
    _write("category3_path_reachability", _order_only())
    _write("category4_multi_object_sync", _tiny())

if __name__ == "__main__":
    main()
