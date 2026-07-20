from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass
from typing import Any

class ValidationError(ValueError):
    pass

class BaseModel:
    def __init__(self, **data: Any):
        annotations = getattr(self.__class__, "__annotations__", {})
        for key in annotations:
            if key in data:
                setattr(self, key, data[key])
            elif hasattr(self.__class__, key):
                setattr(self, key, getattr(self.__class__, key))
            else:
                raise ValidationError(f"missing field: {key}")
        for key, value in data.items():
            if key not in annotations:
                setattr(self, key, value)

    @classmethod
    def model_validate(cls, data: Any):
        if isinstance(data, cls):
            return data
        if not isinstance(data, dict):
            raise ValidationError("expected object")
        return cls(**data)

    @classmethod
    def model_validate_json(cls, text: str):
        return cls.model_validate(json.loads(text))

    def model_dump(self):
        def conv(value):
            if isinstance(value, BaseModel):
                return value.model_dump()
            if is_dataclass(value):
                return conv(asdict(value))
            if isinstance(value, list):
                return [conv(v) for v in value]
            if isinstance(value, tuple):
                return [conv(v) for v in value]
            if isinstance(value, dict):
                return {k: conv(v) for k, v in value.items()}
            return value
        return {k: conv(v) for k, v in self.__dict__.items()}

    def model_dump_json(self):
        return json.dumps(self.model_dump(), sort_keys=True)

    def __eq__(self, other):
        return type(self) is type(other) and self.model_dump() == other.model_dump()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__dict__!r})"
