"""Regression tests for endpoint-level independent cross-validation."""
import json
import unittest
from pathlib import Path
from topology100.cross_validate import build_report, parse_arc_dp, _compare_edges, _endpoint_validation, _cu_links


class CrossValidationTests(unittest.TestCase):
    root = Path(__file__).parents[1]

    def setUp(self):
        self.report = build_report(self.root)

    def test_arc_is_station_inventory_only(self):
        for machine, count in (("cnc135", 43), ("cnc152", 13)):
            data = self.report["machines"][machine]
            self.assertEqual(data["arc_dp"]["acx_unique_path_count"], count)
            self.assertTrue(data["checks"]["arc_station_set_matches_runtime"])
            self.assertEqual(data["arc_dp"]["component"], "unavailable")
            self.assertEqual(data["arc_dp"]["device_id"], "unavailable")
            self.assertEqual(data["arc_dp"]["port"], "unavailable")

    def test_actual_and_target_records_have_unique_canonical_keys(self):
        for data in self.report["machines"].values():
            for phase in ("actual", "target"):
                validation = data["endpoint_validation"][phase]
                self.assertTrue(validation["assertions"]["unique_component_keys"])
                self.assertTrue(validation["assertions"]["reciprocal_ports"])
                self.assertTrue(validation["assertions"]["selector_bounds"])
                self.assertEqual(len(validation["component_records"]), validation["counts"]["components"])
                self.assertTrue(all(len(c["machine_component_key"]) == 3 for c in validation["component_records"]))
                self.assertTrue(all("selector" in p for p in validation["port_records"]))

    def test_edge_comparison_is_endpoint_level_and_keeps_delta(self):
        for data in self.report["machines"].values():
            comparison = data["edge_endpoint_comparison"]
            self.assertIn(comparison["status"], {"exact", "mismatch", "unresolved"})
            self.assertEqual(comparison["actual_count"], data["endpoint_validation"]["actual"]["counts"]["edges"])
            self.assertEqual(comparison["target_count"], data["endpoint_validation"]["target"]["counts"]["edges"])
            self.assertIn(data["checks"]["actual_target_delta"]["has_delta"], {True, False})
            for row in comparison["records"]:
                self.assertIn(row["status"], {"exact", "mismatch", "unresolved"})

    def test_cu_link_pairing_is_independent_for_actual_and_target(self):
        for machine, expected in (("cnc135", 4), ("cnc152", 1)):
            links = self.report["machines"][machine]["cu_link_validation"]
            self.assertEqual(len(links["actual"]), expected)
            self.assertEqual(len(links["target"]), expected)
            self.assertTrue(links["assertions"]["actual_target_pairing"])
            for phase in ("actual", "target"):
                self.assertTrue(all(x["status"] == "exact" for x in links[phase]))
                self.assertTrue(all(len(x["representations"]) == 2 for x in links[phase]))

    def test_summary_preservation_and_runtime_policy(self):
        self.assertTrue(self.report["policy"]["runtime_graph_unchanged"])
        self.assertFalse(self.report["policy"]["arc_electrical_runtime_edges"])
        for data in self.report["machines"].values():
            self.assertTrue(all(v["equal"] for v in data["runtime_summary_comparison"].values()))
        self.assertEqual(len(self.report["conclusions"]), 5)

    def test_duplicate_edges_remain_in_inventory_and_mismatch(self):
        edge = {"from": {"cu": 1, "component": 2, "port_ordinal": 0}, "to": {"cu": 1, "component": 3, "port_ordinal": 1}}
        result = _compare_edges([edge, edge], [edge])
        self.assertEqual(result["actual_count"], 2)
        self.assertEqual(result["duplicate_endpoint_keys"], 1)
        self.assertEqual(result["status"], "mismatch")

    def test_selector_bounds_are_safe_for_missing_values(self):
        doc = {"topology_actual": {"1": {"components": [{"number": 1, "ports": {"x": {"peer_component": None, "peer_port": None}}}]}}, "topology_target": {"1": {"components": []}}, "cables_actual": {"edges": []}, "cables_target": {"edges": []}}
        validation = _endpoint_validation(doc)
        self.assertFalse(validation["actual"]["assertions"]["selector_bounds"])
        self.assertIn("assertions", validation["actual"])

    def test_reciprocal_ports_require_reverse_selector(self):
        doc = {"topology_actual": {"1": {"components": [{"number": 1, "ports": {"0": {"peer_component": 2, "peer_port": 0}}}, {"number": 2, "ports": {"0": {"peer_component": 1, "peer_port": 1}}}]}}, "topology_target": {"1": {"components": []}}, "cables_actual": {"edges": []}, "cables_target": {"edges": []}}
        self.assertFalse(_endpoint_validation(doc)["actual"]["assertions"]["reciprocal_ports"])

    def test_expected_cu_link_count_is_asserted(self):
        doc = {"topology_actual": {"1": {"components": [{"number": 1, "name": "CU_LINK_1", "device_id": "D", "ports": {}}]}}}
        self.assertFalse(_cu_links(doc, "actual", expected_pairs=2)["assertion"])

    def test_core_evidence_does_not_call_cross_validation_tools(self):
        import topology100.evidence as evidence
        import topology100.cross_validate as cross_validate
        original_arc = cross_validate.parse_arc_dp
        original_pdf = cross_validate.inspect_electrical
        try:
            cross_validate.parse_arc_dp = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('ARC called'))
            cross_validate.inspect_electrical = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('PDF called'))
            root = self.root / 'runs' / 'cnc152'
            doc = evidence.build_evidence(root / 'readvar' / 'reads.jsonl', root / 'sdb')
            self.assertEqual(doc['summary']['axes_verified'], 6)
        finally:
            cross_validate.parse_arc_dp = original_arc
            cross_validate.inspect_electrical = original_pdf


if __name__ == "__main__":
    unittest.main()
