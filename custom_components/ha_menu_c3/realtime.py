"""Deliver rotary adjustments in order, keeping only the newest pending value."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


class LatestAdjustmentQueue:
    def __init__(
        self,
        spawn: Callable[[Awaitable[None]], asyncio.Task],
        deliver: Callable[[str, str, str], Awaitable[None]],
    ) -> None:
        self._spawn = spawn
        self._deliver = deliver
        self._pending: dict[tuple[str, str], str] = {}
        self._workers: dict[tuple[str, str], asyncio.Task] = {}

    def push(self, item_id: str, field: str, value: str) -> None:
        key = (item_id, field)
        self._pending[key] = value
        worker = self._workers.get(key)
        if worker is None or worker.done():
            self._workers[key] = self._spawn(self._run(key))

    async def _run(self, key: tuple[str, str]) -> None:
        try:
            while key in self._pending:
                value = self._pending.pop(key)
                await self._deliver(key[0], key[1], value)
        finally:
            self._workers.pop(key, None)

    def close(self) -> None:
        self._pending.clear()
        for task in self._workers.values():
            task.cancel()
        self._workers.clear()
