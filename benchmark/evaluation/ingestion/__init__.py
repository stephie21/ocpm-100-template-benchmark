"""OCEL ingestion helpers for deterministic evaluation."""

from evaluation.ingestion.ocel_loader import load_ocel
from evaluation.ingestion.reference_model import ReferenceModel

__all__ = ["ReferenceModel", "load_ocel"]
