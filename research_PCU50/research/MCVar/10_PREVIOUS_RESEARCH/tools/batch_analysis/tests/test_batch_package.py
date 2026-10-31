import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from mcvar_batch_planner import plan_batch
from benchmark_schema import Metric, unavailable_result
from analyze_batch_evidence import analyze


class PlannerTests(unittest.TestCase):
    def test_one_call_sizes_through_20(self):
        self.assertEqual(plan_batch(20, "one_call").calls, (20,))

    def test_one_call_rejects_40_bound(self):
        with self.assertRaises(ValueError):
            plan_batch(40, "one_call")

    def test_chunk_40_is_two_bounded_calls(self):
        p = plan_batch(40, "chunks")
        self.assertEqual(p.calls, (20, 20))
        self.assertTrue(p.bounded)

    def test_singles_preserve_count(self):
        self.assertEqual(plan_batch(5, "singles").calls, (1, 1, 1, 1, 1))


class SchemaTests(unittest.TestCase):
    def test_unavailable_is_explicit(self):
        r = unavailable_result(40, "chunks", (20, 20), evidence="offline")
        d = r.to_dict()
        self.assertEqual(d["invocation_latency_ms"]["status"], "unavailable")
        self.assertIsNone(d["per_item_latency_ms"]["value"])
        self.assertFalse(d["observed"])
        self.assertEqual(d["backend_transaction_count"]["status"], "unavailable")

    def test_metric_rejects_fake_unmeasured_value(self):
        with self.assertRaises(ValueError):
            Metric(1.0, "ms", "unavailable", "bad")


class EvidenceTests(unittest.TestCase):
    def test_saved_coverage_and_40_gap(self):
        result = analyze()
        self.assertEqual(result["sizes"]["1"]["invocations"], 18)
        self.assertEqual(result["sizes"]["2"]["invocations"], 1)
        self.assertEqual(result["sizes"]["5"]["invocations"], 17)
        self.assertEqual(result["sizes"]["10"]["invocations"], 1)
        self.assertEqual(result["sizes"]["20"]["invocations"], 23)
        self.assertEqual(result["sizes"]["40"]["invocations"], 0)
        self.assertFalse(result["backend_transaction_counts_claimed"])


if __name__ == "__main__":
    unittest.main()
