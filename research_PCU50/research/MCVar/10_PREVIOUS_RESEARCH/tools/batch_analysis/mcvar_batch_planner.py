"""Portable, side-effect-free planner for bounded MCVar benchmark variants."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Variant = Literal["one_call", "singles", "chunks"]
SUPPORTED_SIZES = (1, 2, 5, 10, 20, 40)


@dataclass(frozen=True)
class BatchPlan:
    requested_items: int
    variant: Variant
    max_batch_size: int
    calls: tuple[int, ...]
    bounded: bool
    note: str

    @property
    def call_count(self) -> int:
        return len(self.calls)


def plan_batch(requested_items: int, variant: Variant, *, max_batch_size: int = 20) -> BatchPlan:
    """Return intended SDK invocations; this does not claim server transaction counts."""
    if requested_items < 1:
        raise ValueError("requested_items must be positive")
    if max_batch_size < 1:
        raise ValueError("max_batch_size must be positive")
    if variant not in ("one_call", "singles", "chunks"):
        raise ValueError(f"unknown variant: {variant}")
    if variant == "one_call":
        if requested_items > max_batch_size:
            raise ValueError("one_call exceeds max_batch_size; use chunks")
        calls = (requested_items,)
    elif variant == "singles":
        calls = (1,) * requested_items
    else:
        full, remainder = divmod(requested_items, max_batch_size)
        calls = (max_batch_size,) * full + ((remainder,) if remainder else ())
    return BatchPlan(
        requested_items=requested_items,
        variant=variant,
        max_batch_size=max_batch_size,
        calls=calls,
        bounded=all(1 <= size <= max_batch_size for size in calls),
        note="SDK call plan only; backend transaction count is not observed by this package",
    )


def plans_for_sizes(sizes=SUPPORTED_SIZES, *, max_batch_size: int = 20) -> list[BatchPlan]:
    return [plan_batch(size, variant, max_batch_size=max_batch_size)
            for size in sizes for variant in ("one_call", "singles", "chunks")
            if not (variant == "one_call" and size > max_batch_size)]
