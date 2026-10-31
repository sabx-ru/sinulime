"""Synchronous offline collection mechanics; adapters own platform-specific access."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import get_ident
from time import monotonic_ns
from typing import Any, Callable, Iterable, Protocol, Sequence


class Quality(str, Enum):
    GOOD = "good"
    BAD = "bad"
    STALE = "stale"
    MISSING = "missing"


@dataclass(frozen=True)
class ItemSpec:
    name: str
    key: str | None = None

    @property
    def result_key(self) -> str:
        return self.key if self.key is not None else self.name


@dataclass(frozen=True)
class ItemResult:
    spec: ItemSpec
    value: Any
    quality: Quality
    error: str | None = None
    updated_at_ns: int | None = None


@dataclass(frozen=True)
class Collection:
    items: tuple[ItemResult, ...]
    started_ns: int
    finished_ns: int
    duration_ns: int


@dataclass(frozen=True)
class Snapshot:
    items: tuple[ItemResult, ...]
    collected_at_ns: int
    duration_ns: int


class Adapter(Protocol):
    """Adapter implementation must perform one read per input position."""
    def read(self, specs: Sequence[ItemSpec]) -> Sequence[Any]: ...


class Collector:
    """Collect aligned values, isolating item failures and retaining last-good data.

    The first calling thread becomes the owner. This deliberately provides an
    ownership guard, not a COM implementation; a Windows adapter can supply its
    own STA-thread dispatcher behind the same contract.
    """
    def __init__(self, adapter: Adapter, *, clock_ns: Callable[[], int] = monotonic_ns):
        self._adapter = adapter
        self._clock = clock_ns
        self._owner: int | None = None
        self._last_good: dict[str, tuple[Any, int]] = {}
        self._closed = False

    def collect(self, names: Iterable[str | ItemSpec]) -> Collection:
        self._assert_owner()
        if self._closed:
            raise RuntimeError("collector is shut down")
        specs = tuple(n if isinstance(n, ItemSpec) else ItemSpec(n) for n in names)
        started = self._clock()
        try:
            raw = self._adapter.read(specs)
            raw_values = tuple(raw)
            batch_error = None
        except Exception as exc:
            raw_values = ()
            batch_error = _error_text(exc)
        results: list[ItemResult] = []
        for index, spec in enumerate(specs):
            now = self._clock()
            key = spec.result_key
            if batch_error:
                value, quality, error = self._retained(key), Quality.BAD, batch_error
            elif index >= len(raw_values):
                value, quality, error = self._retained(key), Quality.MISSING, "adapter returned fewer values than requested"
            else:
                entry = raw_values[index]
                if isinstance(entry, BaseException):
                    value, quality, error = self._retained(key), Quality.BAD, _error_text(entry)
                elif isinstance(entry, ItemResult):
                    if entry.spec != spec:
                        value, quality, error = self._retained(key), Quality.BAD, "adapter result spec does not match request position"
                    else:
                        quality, error = entry.quality, entry.error
                        if quality == Quality.GOOD:
                            value = entry.value
                            self._last_good[key] = (value, now)
                        else:
                            value = self._retained(key)
                else:
                    value, quality, error = entry, Quality.GOOD, None
                    self._last_good[key] = (value, now)
            retained = self._last_good.get(key)
            stamp = retained[1] if quality != Quality.GOOD and retained else (now if quality == Quality.GOOD else None)
            results.append(ItemResult(spec, value, quality, error, stamp))
        finished = self._clock()
        return Collection(tuple(results), started, finished, max(0, finished - started))

    def snapshot(self, collection: Collection, *, max_age_ns: int | None = None) -> Snapshot:
        now = self._clock()
        items = collection.items
        if max_age_ns is not None:
            items = tuple(ItemResult(i.spec, i.value,
                         Quality.STALE if i.updated_at_ns is not None and now - i.updated_at_ns > max_age_ns and i.quality == Quality.GOOD else i.quality,
                         i.error, i.updated_at_ns) for i in items)
        return Snapshot(items, collection.finished_ns, collection.duration_ns)

    def shutdown(self) -> None:
        self._assert_owner()
        if not self._closed:
            close = getattr(self._adapter, "close", None)
            if close is not None:
                close()
            self._closed = True

    def _retained(self, key: str) -> Any:
        return self._last_good[key][0] if key in self._last_good else None

    def _assert_owner(self) -> None:
        ident = get_ident()
        if self._owner is None:
            self._owner = ident
        elif ident != self._owner:
            raise RuntimeError("collector accessed outside its owner thread")


def normalize_name(value: str) -> str:
    """Canonicalize display/name input without changing sequence position."""
    if not isinstance(value, str):
        raise TypeError("item name must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError("item name must not be empty")
    return normalized


def _error_text(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"
