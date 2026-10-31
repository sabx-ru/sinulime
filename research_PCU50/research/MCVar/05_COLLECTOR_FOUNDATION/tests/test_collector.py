import threading
import unittest

from collector import Collector, ItemResult, ItemSpec, Quality, normalize_name


class FakeAdapter:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.closed = False

    def read(self, specs):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def close(self):
        self.closed = True


class Clock:
    def __init__(self):
        self.value = 100

    def __call__(self):
        self.value += 10
        return self.value


class CollectorTests(unittest.TestCase):
    def test_duplicates_remain_aligned_by_position(self):
        c = Collector(FakeAdapter([1, 2, 3]))
        result = c.collect(["x", "x", "y"])
        self.assertEqual([i.spec.name for i in result.items], ["x", "x", "y"])
        self.assertEqual([i.value for i in result.items], [1, 2, 3])

    def test_item_failure_retains_last_good_value(self):
        c = Collector(FakeAdapter([7], [ValueError("offline")]))
        self.assertEqual(c.collect(["x"]).items[0].value, 7)
        item = c.collect(["x"]).items[0]
        self.assertEqual(item.value, 7)
        self.assertEqual(item.quality, Quality.BAD)
        self.assertIn("offline", item.error)
        self.assertIsNotNone(item.updated_at_ns)

    def test_duplicate_keys_are_distinct_positions_and_missing_is_reported(self):
        c = Collector(FakeAdapter(["a", "b"], ["new"]))
        c.collect([ItemSpec("dup", "left"), ItemSpec("dup", "right")])
        result = c.collect([ItemSpec("dup", "left"), ItemSpec("dup", "right")])
        self.assertEqual([(i.value, i.quality) for i in result.items], [("new", Quality.GOOD), ("b", Quality.MISSING)])

    def test_batch_failure_and_stale_snapshot(self):
        clock = Clock()
        c = Collector(FakeAdapter(["ok"], RuntimeError("transport")), clock_ns=clock)
        first = c.collect(["x"])
        second = c.collect(["x"])
        self.assertEqual(second.items[0].value, "ok")
        self.assertEqual(second.items[0].quality, Quality.BAD)
        snapshot = c.snapshot(first, max_age_ns=0)
        self.assertEqual(snapshot.items[0].quality, Quality.STALE)
        self.assertGreaterEqual(first.duration_ns, 0)

    def test_non_good_item_result_retains_last_good_value(self):
        c = Collector(FakeAdapter(["good"], [ItemResult(ItemSpec("x"), "bad-payload", Quality.BAD, "bad quality")]))
        c.collect(["x"])
        item = c.collect(["x"]).items[0]
        self.assertEqual(item.value, "good")
        self.assertEqual(item.quality, Quality.BAD)
        self.assertEqual(item.error, "bad quality")

    def test_mismatched_item_result_is_rejected(self):
        c = Collector(FakeAdapter([ItemResult(ItemSpec("other"), 99, Quality.GOOD)]))
        item = c.collect(["x"]).items[0]
        self.assertEqual(item.quality, Quality.BAD)
        self.assertIsNone(item.value)
        self.assertIn("does not match", item.error)

    def test_shutdown_closes_adapter_and_rejects_collect(self):
        adapter = FakeAdapter([])
        c = Collector(adapter)
        c.shutdown()
        self.assertTrue(adapter.closed)
        with self.assertRaisesRegex(RuntimeError, "shut down"):
            c.collect([])

    def test_owner_thread_is_enforced(self):
        c = Collector(FakeAdapter([]))
        c.collect([])
        errors = []
        thread = threading.Thread(target=lambda: self._capture(errors, c))
        thread.start()
        thread.join()
        self.assertEqual(len(errors), 1)
        self.assertIn("owner thread", str(errors[0]))

    @staticmethod
    def _capture(errors, collector):
        try:
            collector.collect([])
        except Exception as exc:
            errors.append(exc)

    def test_name_normalization(self):
        self.assertEqual(normalize_name("  Item A "), "Item A")
        with self.assertRaises(ValueError):
            normalize_name("  ")


if __name__ == "__main__":
    unittest.main()
