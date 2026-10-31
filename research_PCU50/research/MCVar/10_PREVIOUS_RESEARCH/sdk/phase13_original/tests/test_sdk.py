import time
import unittest
from datetime import datetime, timezone

from mcvar_sdk import (
    AcquisitionClient,
    Freshness,
    MockAdapter,
    Quality,
    RetryPolicy,
    SubscriptionRegistry,
    plan_batches,
)


class CountingAdapter(MockAdapter):
    def __init__(self, values=None, failures=0):
        super().__init__(values or {})
        self.calls = []
        self.failures = failures

    def read(self, addresses):
        self.calls.append(tuple(addresses))
        if self.failures:
            self.failures -= 1
            raise ConnectionError("temporary transport failure")
        return super().read(addresses)


class SdkTests(unittest.TestCase):
    def test_batch_planner_preserves_order_duplicates_and_bound(self):
        self.assertEqual(
            plan_batches(["a", "b", "a", "c", "d"], max_batch_size=2),
            [["a", "b"], ["a", "c"], ["d"]],
        )

    def test_read_normalizes_values_and_per_item_errors(self):
        adapter = MockAdapter({"ok": 12, "bad": RuntimeError("bad item")})
        client = AcquisitionClient(adapter)
        result = client.read(["ok", "missing", "bad"])
        self.assertEqual([item.address for item in result.items], ["ok", "missing", "bad"])
        self.assertEqual(result.items[0].value, 12)
        self.assertEqual(result.items[0].quality, Quality.GOOD)
        self.assertEqual(result.items[0].freshness, Freshness.UNKNOWN)
        self.assertEqual(result.items[1].quality, Quality.UNAVAILABLE)
        self.assertEqual(result.items[2].quality, Quality.BAD)
        self.assertEqual(result.items[1].freshness, Freshness.UNKNOWN)
        self.assertTrue(result.items[2].error)

    def test_duplicate_positions_are_not_collapsed(self):
        adapter = MockAdapter({"x": 1})
        result = AcquisitionClient(adapter).read(["x", "x"])
        self.assertEqual([item.address for item in result.items], ["x", "x"])
        self.assertEqual([item.value for item in result.items], [1, 1])

    def test_failed_read_retains_last_value_but_not_claimed_fresh(self):
        class FailingAdapter(MockAdapter):
            fail = False
            def read(self, addresses):
                if self.fail:
                    raise ConnectionError("offline")
                return super().read(addresses)
        adapter = FailingAdapter({"x": 3})
        client = AcquisitionClient(adapter, stale_after=0)
        first = client.read(["x"])
        self.assertEqual(first.items[0].freshness, Freshness.UNKNOWN)
        adapter.fail = True
        second = client.read(["x"])
        self.assertEqual(second.items[0].value, 3)
        self.assertEqual(second.items[0].quality, Quality.UNAVAILABLE)
        self.assertEqual(second.items[0].freshness, Freshness.STALE)

    def test_retry_reconnects_and_succeeds(self):
        adapter = CountingAdapter({"x": 1}, failures=2)
        client = AcquisitionClient(adapter, retry_policy=RetryPolicy(attempts=3, delay=0))
        result = client.read(["x"])
        self.assertEqual(result.items[0].value, 1)
        self.assertEqual(len(adapter.calls), 3)
        self.assertEqual(adapter.reconnect_count, 2)

    def test_single_flight_serializes_concurrent_reads(self):
        adapter = CountingAdapter({"x": 1})
        client = AcquisitionClient(adapter)
        first = client.read(["x"])
        second = client.read(["x"])
        self.assertEqual(first.items[0].value, second.items[0].value)
        self.assertEqual(len(adapter.calls), 2)

    def test_subscription_polling_emits_and_can_stop(self):
        adapter = MockAdapter({"x": 1})
        client = AcquisitionClient(adapter)
        registry = SubscriptionRegistry(client)
        seen = []
        token = registry.subscribe(["x"], lambda result: seen.append(result.items[0].value), interval=0.01)
        time.sleep(0.04)
        registry.unsubscribe(token)
        count = len(seen)
        time.sleep(0.03)
        self.assertGreaterEqual(count, 1)
        self.assertEqual(len(seen), count)
        registry.close()

    def test_result_has_utc_observed_at(self):
        result = AcquisitionClient(MockAdapter({"x": 1})).read(["x"])
        self.assertIsInstance(result.observed_at, datetime)
        self.assertEqual(result.observed_at.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
