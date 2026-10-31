import asyncio
import unittest

from core.polling import PollingSubscription, SubscriptionUpdate


class PollingSubscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_emits_initial_and_changed_values_then_stops(self):
        values = iter([1, 1, 2])
        updates = []

        async def read():
            return {"$A": next(values)}

        subscription = PollingSubscription(
            read,
            updates.append,
            interval=0,
            max_polls=3,
        )
        await subscription.run()

        self.assertEqual([u.values["$A"] for u in updates], [1, 2])
        self.assertTrue(all(isinstance(u, SubscriptionUpdate) for u in updates))
        self.assertEqual(subscription.poll_count, 3)

    async def test_cancel_is_bounded_and_prevents_future_polls(self):
        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def read():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return {"$A": calls}

        subscription = PollingSubscription(read, lambda _: None, interval=0)
        task = asyncio.create_task(subscription.run())
        await asyncio.wait_for(started.wait(), timeout=0.2)

        release.set()
        await subscription.cancel(timeout=0.05)
        self.assertTrue(task.done())
        self.assertTrue(subscription.cancelled)
        self.assertEqual(calls, 1)

    async def test_cancel_timeout_is_reported_for_non_cooperative_reader(self):
        started = asyncio.Event()
        gate = asyncio.Event()

        async def read():
            started.set()
            await gate.wait()
            return {"$A": 1}

        subscription = PollingSubscription(read, lambda _: None, interval=0)
        task = asyncio.create_task(subscription.run())
        await asyncio.wait_for(started.wait(), timeout=0.2)

        with self.assertRaises(asyncio.TimeoutError):
            await subscription.cancel(timeout=0.001)
        self.assertFalse(subscription.cancelled)

        gate.set()
        await asyncio.wait_for(task, timeout=0.2)
        self.assertTrue(subscription.cancelled)


if __name__ == "__main__":
    unittest.main()
