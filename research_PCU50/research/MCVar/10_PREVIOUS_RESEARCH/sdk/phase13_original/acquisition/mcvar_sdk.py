from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence


class Quality(str, Enum):
    GOOD = "good"
    UNCERTAIN = "uncertain"
    BAD = "bad"
    UNAVAILABLE = "unavailable"


class Freshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Observation:
    address: str
    value: Any = None
    quality: Quality = Quality.UNAVAILABLE
    freshness: Freshness = Freshness.UNKNOWN
    observed_at: datetime | None = None
    source_timestamp: datetime | None = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadResult:
    items: tuple[Observation, ...]
    observed_at: datetime


@dataclass(frozen=True)
class RawValue:
    value: Any
    quality: Quality = Quality.GOOD
    source_timestamp: datetime | None = None
    error: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class ReadOnlyAdapter(Protocol):
    """Transport seam. Implementations must expose read only; no write method."""

    def read(self, addresses: Sequence[str]) -> Sequence[RawValue | Any | None]: ...
    def reconnect(self) -> None: ...
    def close(self) -> None: ...


def plan_batches(addresses: Iterable[str], max_batch_size: int) -> list[list[str]]:
    if max_batch_size < 1:
        raise ValueError("max_batch_size must be positive")
    batch: list[str] = []
    batches: list[list[str]] = []
    for address in addresses:
        batch.append(address)
        if len(batch) == max_batch_size:
            batches.append(batch)
            batch = []
    if batch:
        batches.append(batch)
    return batches


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 1
    delay: float = 0.0
    max_delay: float = 5.0

    def __post_init__(self) -> None:
        if self.attempts < 1 or self.delay < 0 or self.max_delay < 0:
            raise ValueError("invalid retry policy")


class AcquisitionClient:
    """Portable acquisition orchestrator with one serialized adapter worker."""

    def __init__(self, adapter: ReadOnlyAdapter, *, max_batch_size: int = 20,
                 retry_policy: RetryPolicy = RetryPolicy(), stale_after: float = 5.0):
        if max_batch_size < 1 or stale_after < 0:
            raise ValueError("invalid client limits")
        self.adapter = adapter
        self.max_batch_size = max_batch_size
        self.retry_policy = retry_policy
        self.stale_after = stale_after
        self._single_flight = threading.Lock()
        self._last_success: dict[str, tuple[Any, datetime | None, datetime]] = {}
        self._closed = False

    def read(self, addresses: Iterable[str]) -> ReadResult:
        requested = list(addresses)
        stamp = datetime.now(timezone.utc)
        observations: list[Observation] = []
        if self._closed:
            return ReadResult(tuple(self._unavailable(a, "client is closed", stamp) for a in requested), stamp)
        with self._single_flight:
            for batch in plan_batches(requested, self.max_batch_size):
                response: Sequence[RawValue | Any | None] | None = None
                error: Exception | None = None
                for attempt in range(self.retry_policy.attempts):
                    try:
                        response = self.adapter.read(batch)
                        error = None
                        break
                    except Exception as exc:
                        error = exc
                        if attempt + 1 < self.retry_policy.attempts:
                            try:
                                self.adapter.reconnect()
                            except Exception as reconnect_error:
                                error = reconnect_error
                            delay = min(self.retry_policy.delay * (2 ** attempt), self.retry_policy.max_delay)
                            if delay:
                                time.sleep(delay)
                if response is None:
                    observations.extend(self._unavailable(address, str(error or "transport failed"), stamp) for address in batch)
                    continue
                if len(response) != len(batch):
                    observations.extend(self._unavailable(address, "adapter returned wrong item count", stamp) for address in batch)
                    continue
                for address, raw in zip(batch, response):
                    if raw is None:
                        observations.append(self._unavailable(address, "adapter returned no item", stamp))
                        continue
                    item = raw if isinstance(raw, RawValue) else RawValue(raw)
                    fresh = item.source_timestamp
                    self._last_success[address] = (item.value, item.source_timestamp, stamp)
                    observations.append(Observation(
                        address=address, value=item.value, quality=item.quality,
                        freshness=self._freshness(fresh, stamp), observed_at=stamp,
                        source_timestamp=item.source_timestamp, error=item.error, metadata=item.metadata,
                    ))
        return ReadResult(tuple(observations), stamp)

    def _freshness(self, timestamp: datetime | None, now: datetime) -> Freshness:
        if timestamp is None:
            return Freshness.UNKNOWN
        age = max(0.0, (now - timestamp).total_seconds())
        return Freshness.FRESH if age <= self.stale_after else Freshness.STALE

    def _unavailable(self, address: str, error: str, now: datetime) -> Observation:
        previous = self._last_success.get(address)
        if previous is None:
            return Observation(address, quality=Quality.UNAVAILABLE, freshness=Freshness.UNKNOWN, observed_at=now, error=error)
        value, source_timestamp, last_observed = previous
        if source_timestamp is not None:
            age_state = self._freshness(source_timestamp, now)
        else:
            age = max(0.0, (now - last_observed).total_seconds())
            age_state = Freshness.STALE if age > self.stale_after else Freshness.UNKNOWN
        return Observation(address, value=value, quality=Quality.UNAVAILABLE,
                           freshness=age_state, observed_at=now, source_timestamp=source_timestamp, error=error)

    def close(self) -> None:
        with self._single_flight:
            if not self._closed:
                self._closed = True
                self.adapter.close()


class SubscriptionRegistry:
    """Polling-backed subscriptions; callbacks execute on a dedicated worker per subscription."""

    def __init__(self, client: AcquisitionClient):
        self.client = client
        self._lock = threading.Lock()
        self._subscriptions: dict[str, tuple[threading.Event, threading.Thread]] = {}

    def subscribe(self, addresses: Iterable[str], callback: Callable[[ReadResult], None], *, interval: float = 1.0) -> str:
        if interval < 0:
            raise ValueError("interval cannot be negative")
        requested = tuple(addresses)
        token = uuid.uuid4().hex
        stop = threading.Event()
        def poll() -> None:
            while not stop.is_set():
                try:
                    callback(self.client.read(requested))
                except Exception:
                    pass
                if stop.wait(interval):
                    break
        thread = threading.Thread(target=poll, name=f"mcvar-poll-{token[:8]}", daemon=True)
        with self._lock:
            self._subscriptions[token] = (stop, thread)
        thread.start()
        return token

    def unsubscribe(self, token: str) -> None:
        with self._lock:
            subscription = self._subscriptions.pop(token, None)
        if subscription is not None:
            stop, thread = subscription
            stop.set()
            if thread is not threading.current_thread():
                thread.join(timeout=2.0)

    def close(self) -> None:
        with self._lock:
            tokens = list(self._subscriptions)
        for token in tokens:
            self.unsubscribe(token)


class MockAdapter:
    """DEMO/TEST ONLY mock; not a Siemens MCVar or vendor transport."""

    def __init__(self, values: Mapping[str, Any]):
        self.values = dict(values)
        self.reconnect_count = 0
        self.closed = False

    def read(self, addresses: Sequence[str]) -> Sequence[RawValue | Any | None]:
        if self.closed:
            raise ConnectionError("mock adapter closed")
        result: list[RawValue | Any | None] = []
        for address in addresses:
            if address not in self.values:
                result.append(None)
                continue
            value = self.values[address]
            if isinstance(value, Exception):
                result.append(RawValue(None, quality=Quality.BAD, error=str(value)))
            else:
                result.append(value)
        return result

    def reconnect(self) -> None:
        self.reconnect_count += 1
        self.closed = False

    def close(self) -> None:
        self.closed = True
