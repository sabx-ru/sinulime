"""Versioned benchmark-result contract; measured fields are optional by design."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Metric:
    value: float | None
    unit: str
    status: str  # measured, unavailable, not_measured
    source: str

    def __post_init__(self) -> None:
        if self.status not in {"measured", "unavailable", "not_measured"}:
            raise ValueError("invalid metric status")
        if self.status == "measured" and self.value is None:
            raise ValueError("measured metrics require value")
        if self.status != "measured" and self.value is not None:
            raise ValueError("unmeasured metrics must have null value")


@dataclass(frozen=True)
class BenchmarkResult:
    size: int
    variant: str
    planned_calls: tuple[int, ...]
    invocation_latency_ms: Metric
    per_item_latency_ms: Metric
    backend_transaction_count: Metric
    evidence: str
    observed: bool

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["planned_calls"] = list(self.planned_calls)
        result["schema_version"] = SCHEMA_VERSION
        return result


def unavailable_result(size: int, variant: str, planned_calls: tuple[int, ...], *, evidence: str) -> BenchmarkResult:
    unavailable = Metric(None, "ms", "unavailable", evidence)
    unknown_count = Metric(None, "count", "unavailable", "saved captures do not expose backend transaction boundaries")
    return BenchmarkResult(size, variant, planned_calls, unavailable, unavailable, unknown_count, evidence, False)
