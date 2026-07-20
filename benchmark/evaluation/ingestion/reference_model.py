from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True)
class ReferenceEvent:
    event_id: str
    activity: str
    timestamp: datetime

@dataclass(frozen=True)
class ReferenceObject:
    object_id: str
    object_type: str

@dataclass(frozen=True)
class EventObjectRelation:
    event_id: str
    object_id: str
    object_type: str = ""
    qualifier: str = ""

@dataclass(frozen=True)
class DirectlyFollowsEdge:
    source: str
    target: str
    count: int
    object_ids: tuple[str, ...]
    durations: tuple[float, ...] = ()

@dataclass(frozen=True)
class ReferenceModel:
    object_types: tuple[str, ...]
    activities: tuple[str, ...]
    events: tuple[ReferenceEvent, ...]
    objects: tuple[ReferenceObject, ...]
    event_object_relations: tuple[EventObjectRelation, ...]
    directly_follows_edges: Mapping[str, tuple[DirectlyFollowsEdge, ...]] = field(default_factory=dict)
    support_status: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "object_types", tuple(self.object_types))
        object.__setattr__(self, "activities", tuple(self.activities))
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "objects", tuple(self.objects))
        object.__setattr__(self, "event_object_relations", tuple(self.event_object_relations))
        edge_map = {key: tuple(value) for key, value in dict(self.directly_follows_edges).items()}
        object.__setattr__(self, "directly_follows_edges", MappingProxyType(edge_map))
        status = dict(self.support_status) or {"json_ocel": "supported (minimal local JSON)", "sqlite_ocel": "not supported in standalone"}
        object.__setattr__(self, "support_status", MappingProxyType(status))

    @property
    def objects_by_id(self) -> Mapping[str, ReferenceObject]:
        return MappingProxyType({obj.object_id: obj for obj in self.objects})

    @property
    def events_by_id(self) -> Mapping[str, ReferenceEvent]:
        return MappingProxyType({event.event_id: event for event in self.events})

    @property
    def timestamps(self) -> Mapping[str, datetime]:
        return MappingProxyType({event.event_id: event.timestamp for event in self.events})

    def directly_follows_counts(self, object_type: str) -> Mapping[tuple[str, str], int]:
        return MappingProxyType({(edge.source, edge.target): edge.count for edge in self.directly_follows_edges.get(object_type, ())})

    def object_ids_for_event(self, event_id: str, object_type: str | None = None) -> tuple[str, ...]:
        objects = self.objects_by_id
        ids = []
        for rel in self.event_object_relations:
            if rel.event_id == event_id and rel.object_id in objects:
                obj = objects[rel.object_id]
                if object_type is None or obj.object_type == object_type:
                    ids.append(rel.object_id)
        return tuple(ids)

    def events_for_object(self, object_id: str) -> tuple[ReferenceEvent, ...]:
        event_ids = [rel.event_id for rel in self.event_object_relations if rel.object_id == object_id]
        events = self.events_by_id
        return tuple(sorted((events[eid] for eid in event_ids if eid in events), key=lambda event: event.timestamp))
