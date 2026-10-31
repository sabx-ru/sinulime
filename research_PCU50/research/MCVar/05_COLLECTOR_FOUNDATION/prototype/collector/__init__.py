"""Offline collector core with an adapter boundary for platform-specific IO."""

from .core import (
    Adapter, Collection, Collector, ItemResult, ItemSpec, Quality,
    Snapshot, normalize_name,
)

__all__ = ["Adapter", "Collection", "Collector", "ItemResult", "ItemSpec", "Quality", "Snapshot", "normalize_name"]
