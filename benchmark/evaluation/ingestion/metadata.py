from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from .reference_model import ReferenceModel

@dataclass(frozen=True)
class MetadataSummary:
    object_types: tuple[str, ...]
    activities: tuple[str, ...]
    event_count: int
    object_count: int
    relation_count: int
    start_timestamp: datetime
    end_timestamp: datetime
    support_status: dict[str, str]

def extract_metadata(model: ReferenceModel) -> MetadataSummary:
    ordered=tuple(sorted(model.events, key=lambda event: event.timestamp))
    return MetadataSummary(tuple(model.object_types), tuple(model.activities), len(model.events), len(model.objects), len(model.event_object_relations), ordered[0].timestamp, ordered[-1].timestamp, dict(model.support_status))
