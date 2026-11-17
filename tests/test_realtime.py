"""Realtime rotary adjustments retain the newest pending value."""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "ha_menu_c3"))
from realtime import LatestAdjustmentQueue


class LatestAdjustmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_and_latest_updates_are_delivered(self):
        gate = asyncio.Event()
        deliveries = []
        first_started = asyncio.Event()

        async def send(item_id, field, value):
            deliveries.append((item_id, field, value))
            if value == "32":
                first_started.set()
                await gate.wait()

        queue = LatestAdjustmentQueue(asyncio.create_task, send)
        queue.push("bureau", "brightness", "32")
        await asyncio.wait_for(first_started.wait(), timeout=1)
        queue.push("bureau", "brightness", "64")
        queue.push("bureau", "brightness", "96")
        queue.push("bureau", "brightness", "128")
        gate.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertEqual(deliveries, [
            ("bureau", "brightness", "32"),
            ("bureau", "brightness", "128"),
        ])
        queue.close()

    async def test_different_controls_are_independent(self):
        delivered = []
        async def send(item_id, field, value):
            delivered.append((item_id, field, value))

        queue = LatestAdjustmentQueue(asyncio.create_task, send)
        queue.push("bureau", "brightness", "90")
        queue.push("salon", "brightness", "120")
        queue.push("bureau", "color_temp", "3100")
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.assertCountEqual(delivered, [
            ("bureau", "brightness", "90"),
            ("salon", "brightness", "120"),
            ("bureau", "color_temp", "3100"),
        ])
        queue.close()

    async def test_close_discards_pending_commands(self):
        gate = asyncio.Event()
        started = asyncio.Event()
        delivered = []

        async def send(item_id, field, value):
            delivered.append(value)
            started.set()
            await gate.wait()

        queue = LatestAdjustmentQueue(asyncio.create_task, send)
        queue.push("bureau", "brightness", "20")
        await asyncio.wait_for(started.wait(), timeout=1)
        queue.push("bureau", "brightness", "40")
        queue.close()
        gate.set()
        await asyncio.sleep(0)
        self.assertEqual(delivered, ["20"])


if __name__ == "__main__":
    unittest.main()
