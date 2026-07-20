from __future__ import annotations
from collections import defaultdict, deque
from statistics import mean


def ok(value, message):
    return {"value": value, "status": "success", "message": message}

def err(message):
    return {"value": None, "status": "error", "message": message}

def need(bindings, name):
    if bindings is None or name not in bindings:
        return err(f"Missing required variable binding '{name}'")
    return None

def object_ids(model, object_type):
    return tuple(obj.object_id for obj in model.objects if obj.object_type == object_type)

def event_object_types(model, event):
    ids = set(model.object_ids_for_event(event.event_id))
    by_id = model.objects_by_id
    return {by_id[oid].object_type for oid in ids if oid in by_id}

def count_activity_for_type(model, activity, object_type):
    return sum(1 for event in model.events if event.activity == activity and model.object_ids_for_event(event.event_id, object_type))

def unique_objects_for_activity(model, activity):
    ids = set()
    for event in model.events:
        if event.activity == activity:
            ids.update(model.object_ids_for_event(event.event_id))
    return ids

def edge_count(model, source, target, object_type):
    return sum(edge.count for edge in model.directly_follows_edges.get(object_type, ()) if edge.source == source and edge.target == target)

def edge_durations(model, source, target, object_type):
    values=[]
    for edge in model.directly_follows_edges.get(object_type, ()):
        if edge.source == source and edge.target == target:
            values.extend(edge.durations)
    return values

def eventually_follows_durations(model, source, target, object_type):
    durations=[]
    for oid in object_ids(model, object_type):
        events=model.events_for_object(oid)
        for i,event in enumerate(events):
            if event.activity != source:
                continue
            for later in events[i+1:]:
                if later.activity == target:
                    durations.append((later.timestamp-event.timestamp).total_seconds())
                    break
    return durations

def activity_graph(model, object_type):
    graph=defaultdict(set)
    for edge in model.directly_follows_edges.get(object_type, ()):
        graph[edge.source].add(edge.target)
    return graph

def reachable(model, source, target, object_type):
    graph=activity_graph(model, object_type)
    seen={source}
    queue=deque([source])
    while queue:
        node=queue.popleft()
        for nxt in graph[node]:
            if nxt == target:
                return True
            if nxt not in seen:
                seen.add(nxt); queue.append(nxt)
    return False

def shortest_path(model, source, target, object_type):
    graph=activity_graph(model, object_type)
    queue=deque([(source,[source])]); seen={source}
    while queue:
        node,path=queue.popleft()
        if node == target:
            return path
        for nxt in sorted(graph[node]):
            if nxt not in seen:
                seen.add(nxt); queue.append((nxt,path+[nxt]))
    return []

def activities_for_type(model, object_type):
    vals=[]
    for event in model.events:
        if model.object_ids_for_event(event.event_id, object_type) and event.activity not in vals:
            vals.append(event.activity)
    return vals

def start_activities(model, object_type):
    vals=[]
    for oid in object_ids(model, object_type):
        events=model.events_for_object(oid)
        if events and events[0].activity not in vals:
            vals.append(events[0].activity)
    return vals

def end_activities(model, object_type):
    vals=[]
    for oid in object_ids(model, object_type):
        events=model.events_for_object(oid)
        if events and events[-1].activity not in vals:
            vals.append(events[-1].activity)
    return vals
