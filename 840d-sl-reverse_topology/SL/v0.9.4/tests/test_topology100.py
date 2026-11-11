"""v1.0.0 offline regression tests."""
import json
import tempfile
import unittest
from pathlib import Path

from topology100.evidence import build_evidence, compare_summaries


class EvidenceTests(unittest.TestCase):
    def test_md30110_evidence_uses_area_three(self):
        root = Path(__file__).parents[1] / "runs" / "cnc152"
        doc = build_evidence(root / "readvar" / "reads.jsonl", root / "sdb")
        refs=[a['evidence']['md30110'] for a in doc['axes']]
        self.assertTrue(refs)
        self.assertTrue(all(ref['area']==3 for ref in refs))

    def test_core_evidence_does_not_require_external_cross_validation_tools(self):
        root = Path(__file__).parents[1] / "runs" / "cnc152"
        doc = build_evidence(root / "readvar" / "reads.jsonl", root / "sdb")
        self.assertEqual(doc['summary']['axes_verified'], 6)
    def test_existing_capture_is_normalized(self):
        root = Path(__file__).parents[1] / "runs" / "cnc152"
        doc = build_evidence(root / "readvar" / "reads.jsonl", root / "sdb")
        self.assertEqual(doc["schema"], "read-only-topology/v1.0.0")
        self.assertEqual(doc["summary"]["cu_count"], 2)
        self.assertEqual(doc["summary"]["axes_verified"], 6)
        self.assertEqual(doc["summary"]["connection_records"], 29 + 6 * 5)
        self.assertEqual(doc["summary"]["drive_records"], 6)
        self.assertEqual(doc["summary"]["equipment_relation_records"], 30)
        self.assertEqual(sum(d["status"] == "confirmed" for d in doc["drives"]), 6)
        kinds = {r["kind"] for r in doc["connections"]}
        self.assertTrue({"AXIS_TO_DRIVE", "DRIVE_TO_MOTOR_MODULE", "DRIVE_TO_SENSOR_MODULE"} <= kinds)

    def test_old_and_new_summary_comparison_is_explicit(self):
        old = {"cu_count": 2, "axes_active": 6, "axes_verified": 6,
               "hw_slot_count": 9, "physical_actual_edges": 13,
               "cu_link_pairs": 1, "topology_all_tlv_complete": True}
        result = compare_summaries(old, old)
        self.assertTrue(all(item["equal"] for item in result.values()))

    def test_output_is_json_and_provenance_is_preserved(self):
        root = Path(__file__).parents[1] / "runs" / "cnc135"
        doc = build_evidence(root / "readvar" / "reads.jsonl", root / "sdb")
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "evidence.json").write_text(json.dumps(doc), encoding="utf-8")
            loaded = json.loads((out / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded["provenance"]["sdb"], str(root / "sdb"))
        self.assertEqual(loaded["summary"]["axes_verified"], 19)
        self.assertIn("drives", loaded)
        self.assertEqual(loaded["summary"]["drive_records"], 19)


if __name__ == "__main__":
    unittest.main()

    def test_equipment_chain_fails_closed_for_duplicate_identity_and_missing_module(self):
        from topology100.evidence import _equipment_chain
        axis1 = {"status": "confirmed", "axis_unit": 1, "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 4}}
        axis2 = {"status": "confirmed", "axis_unit": 2, "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 4}}
        servo = {"unit": 10, "identity": {"bus_id": 1, "slave": 2, "do": 3}, "refs": {}, "motor_module_refs": [], "motor_module_ref": 0}
        drives, relations = _equipment_chain({"topology_actual": {}, "servo_objects": [servo]}, [axis1, axis2])
        self.assertEqual(drives[0]["mapping_status"], "ambiguous_mapping")
        self.assertEqual(len(drives[0]["axis_candidates"]), 2)
        axis_rel = [r for r in relations if r["kind"] == "AXIS_TO_DRIVE"]
        self.assertEqual(len(axis_rel), 1)
        self.assertEqual(axis_rel[0]["reason"], "ambiguous_mapping")
        self.assertFalse(any(r["status"] == "confirmed" for r in relations))

        solo, missing_relations = _equipment_chain({"topology_actual": {}, "servo_objects": [servo]}, [axis1])
        missing = [r for r in missing_relations if r["kind"] == "DRIVE_TO_MOTOR_MODULE"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["status"], "unresolved")
        self.assertEqual(missing[0]["reason"], "missing_motor_module_reference")


class EquipmentReferenceSentinelTests(unittest.TestCase):
    def test_missing_module_sentinels_survive_ambiguous_axis_mapping(self):
        from topology100.evidence import _equipment_chain
        axis1 = {"status": "confirmed", "axis_unit": 1, "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 4}}
        axis2 = {"status": "confirmed", "axis_unit": 2, "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 4}}
        for sentinel in (None, 0, 255, 65535):
            servo = {"unit": 10, "identity": {"bus_id": 1, "slave": 2, "do": 3}, "refs": {"121": [sentinel]}, "motor_module_refs": [{"component": sentinel}]}
            with self.subTest(sentinel=sentinel):
                _, relations = _equipment_chain({"topology_actual": {}, "servo_objects": [servo]}, [axis1, axis2])
                axis = next(r for r in relations if r["kind"] == "AXIS_TO_DRIVE")
                module = next(r for r in relations if r["kind"] == "DRIVE_TO_MOTOR_MODULE")
                self.assertEqual(axis["reason"], "ambiguous_mapping")
                self.assertEqual(len(axis["from"]["axis_candidates"]), 2)
                self.assertEqual(module["reason"], "missing_motor_module_reference")
                self.assertEqual(module["status"], "unresolved")
                self.assertFalse(any(r["status"] == "confirmed" for r in relations))

    def test_unique_mapping_retains_missing_module_relation(self):
        from topology100.evidence import _equipment_chain
        axis = {"status": "confirmed", "axis_unit": 1, "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 4}}
        servo = {"unit": 10, "identity": {"bus_id": 1, "slave": 2, "do": 3}, "refs": {}, "motor_module_refs": []}
        _, relations = _equipment_chain({"topology_actual": {}, "servo_objects": [servo]}, [axis])
        self.assertTrue(any(r["kind"] == "AXIS_TO_DRIVE" and r["status"] == "confirmed" for r in relations))
        module = next(r for r in relations if r["kind"] == "DRIVE_TO_MOTOR_MODULE")
        self.assertEqual(module["reason"], "missing_motor_module_reference")
