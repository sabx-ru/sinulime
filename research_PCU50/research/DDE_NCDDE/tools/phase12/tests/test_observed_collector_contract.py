"""Offline tests for the observed collector contract.

This harness models only contract boundaries from preserved captures: ordered
positions, duplicates, max batch size, separate outer/item status, and partial
results. It does not model DDE framing, freshness, atomicity, or device values.
"""
import unittest


class ContractError(ValueError):
    pass


def validate_request(items):
    if not items or len(items) > 20:
        raise ContractError("request must contain 1..20 items")
    return list(items)


def normalize_response(request, outer_status, item_results):
    request = validate_request(request)
    if len(item_results) != len(request):
        raise ContractError("one result is required per input position")
    return {
        "outer_status": outer_status,
        "snapshot_consistent": False,
        "freshness": "unknown",
        "items": [
            {"ordinal": i, "requested": key, **result}
            for i, (key, result) in enumerate(zip(request, item_results))
        ],
    }


class CollectorContractTests(unittest.TestCase):
    def test_order_and_duplicates_are_preserved(self):
        response = normalize_response(
            ["A", "B", "A"],
            "partial",
            [{"status": "ok", "value": 1},
             {"status": "item_error", "code": "bad"},
             {"status": "ok", "value": 2}],
        )
        self.assertEqual([x["requested"] for x in response["items"]], ["A", "B", "A"])
        self.assertEqual([x["ordinal"] for x in response["items"]], [0, 1, 2])
        self.assertEqual(response["items"][1]["status"], "item_error")

    def test_outer_status_is_separate_from_item_status(self):
        response = normalize_response(
            ["A"], "api_negative", [{"status": "quality_bad", "quality": 3}]
        )
        self.assertEqual(response["outer_status"], "api_negative")
        self.assertEqual(response["items"][0]["status"], "quality_bad")

    def test_batch_limit_is_20(self):
        self.assertEqual(len(validate_request([str(i) for i in range(20)])), 20)
        with self.assertRaises(ContractError):
            validate_request([str(i) for i in range(21)])

    def test_freshness_and_atomicity_are_not_claimed(self):
        response = normalize_response(["A"], "ok", [{"status": "ok"}])
        self.assertFalse(response["snapshot_consistent"])
        self.assertEqual(response["freshness"], "unknown")

    def test_missing_per_position_result_is_rejected(self):
        with self.assertRaises(ContractError):
            normalize_response(["A", "A"], "ok", [{"status": "ok"}])


if __name__ == "__main__":
    unittest.main()
