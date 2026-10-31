"""Polling-backed subscriptions; no native MCVar event/connection-point claims."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class SubscriptionUpdate:
    """A changed snapshot returned by the read adapter."""

    values: Mapping[str, Any]
    observed_at: datetime
    poll_number: int


class PollingSubscription:
    """Poll a read function and emit changed snapshots until cancelled.

    The read function must cooperate with task cancellation. ``cancel`` has a
    timeout so a blocked adapter cannot make shutdown unbounded. Equality is
    applied to the complete mapping; no freshness or snapshot consistency is
    inferred from the result.
    """

    def __init__(
        self,
        read: Callable[[], Awaitable[Mapping[str, Any]]],
        on_update: Callable[[SubscriptionUpdate], Any],
        *,
        interval: float = 1.0,
        max_polls: int | None = None,
    ) -> None:
        if interval < 0:
            raise ValueError("interval must be non-negative")
        if max_polls is not None and max_polls < 1:
            raise ValueError("max_polls must be positive or None")
        self._read = read
        self._on_update = on_update
        self._interval = interval
        self._max_polls = max_polls
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self.poll_count = 0
        self.cancelled = False

    async def run(self) -> None:
        if self._task is not None and self._task is not asyncio.current_task():
            raise RuntimeError("subscription is already running")
        self._task = asyncio.current_task()
        previous: Mapping[str, Any] | None = None
        try:
            while not self._stop.is_set():
                snapshot = await self._read()
                self.poll_count += 1
                if previous is None or dict(snapshot) != dict(previous):
                    update = SubscriptionUpdate(
                        values=dict(snapshot),
                        observed_at=datetime.now(timezone.utc),
                        poll_number=self.poll_count,
                    )
                    result = self._on_update(update)
                    if asyncio.iscoroutine(result):
                        await result
                    previous = dict(snapshot)
                if self._max_polls is not None and self.poll_count >= self._max_polls:
                    break
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.cancelled = self._stop.is_set()
            self._task = None

    async def cancel(self, *, timeout: float = 1.0) -> None:
        if timeout < 0:
            raise ValueError("timeout must be non-negative")
        self._stop.set()
        task = self._task
        if task is None or task is asyncio.current_task():
            self.cancelled = True
            return
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError:
            # Keep the task alive: the adapter may still be using external state.
            raise
        self.cancelled = True
