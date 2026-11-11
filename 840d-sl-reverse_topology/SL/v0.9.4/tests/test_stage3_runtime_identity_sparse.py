"""B2-PJCS-1 vectors and sparse production-path safety regressions.
"""
import json
import tempfile
import unittest
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from topology092.model import make_model
from topology100.identity import canonical_json, identity_id, published_identity_id, provisional_identity_id, NAMESPACE
from topology100.evidence import _equipment_chain
from topology100.adapter_legacy import project_legacy, _endpoint


class RuntimeIdentityTests(unittest.TestCase):
    def test_legacy_projection_uses_snapshot_scoped_b2_provisional_ids(self):
        legacy = {"axes": [{"axis_unit": 4, "name": "X", "status": "confirmed",
                            "evidence": {"md30110": {"area": 3, "block": 26, "unit": 4, "param": 30110, "index": 0}}}],
                  "summary": {"read_statuses": {"ok": 1}}}
        first = project_legacy(legacy, installation_id="plant-a", snapshot_id="snap-a").to_dict()
        again = project_legacy(legacy, installation_id="plant-a", snapshot_id="snap-a").to_dict()
        other = project_legacy(legacy, installation_id="plant-a", snapshot_id="snap-b").to_dict()
        identity = first["actual"]["objects"][0]["identity"]
        self.assertEqual(identity["identity_status"], "provisional")
        self.assertEqual(identity["id"], again["actual"]["objects"][0]["identity"]["id"])
        self.assertNotEqual(identity["id"], other["actual"]["objects"][0]["identity"]["id"])
        self.assertEqual(first["actual"]["objects"], first["target"]["objects"])
        self.assertNotEqual(id(first["actual"]), id(first["target"]))
        self.assertNotEqual(identity["id"], identity_id("logical_object", {"logical_key": "axis:4"})[0])
        self.assertTrue(all(r["status"] != "confirmed" for r in first["actual"]["connections"]))

    def test_adapter_uses_published_identity_only_for_explicit_source_contract(self):
        expected = published_identity_id("v1", "plant-a", "logical_object", {"axis": 4})
        endpoint = _endpoint("logical_object", "axis:4", installation_id="plant-a",
                             snapshot_id="snap-a", source_identity={"axis": 4})
        self.assertEqual((endpoint["object_id"], endpoint["identity_status"]), (expected, "stable"))
        self.assertNotEqual(endpoint["object_id"], identity_id("logical_object", {"logical_key": "axis:4"})[0])

    def test_legacy_projection_retains_envelope_shape(self):
        document = project_legacy({"axes": [], "components": [], "drives": [], "connections": [],
                                   "summary": {"read_statuses": {"ok": 1}}}).to_dict()
        self.assertEqual(set(document), {"schema", "snapshot_id", "revision", "captured_at", "mode",
                                         "installation_id", "completeness", "actual", "target",
                                         "reconciliation", "evidence", "unresolved", "extensions"})
        self.assertEqual(set(document["actual"]), {"objects", "channels", "ports", "connections", "relations", "extensions"})
        self.assertEqual(set(document["target"]), set(document["actual"]))

    def test_published_identity_uses_approved_name_and_namespace(self):
        value = published_identity_id("v1", "plant-a", "axis", {"do": 2, "cu": 1})
        expected_name = 'v1|plant-a|axis|{"cu":1,"do":2}'
        self.assertEqual(value, str(uuid5(uuid5(NAMESPACE_URL, "sinumerik-core"), expected_name)))

    def test_published_identity_is_order_independent_and_requires_context(self):
        self.assertEqual(
            published_identity_id("v1", "plant-a", "axis", {"b": 2, "a": 1}),
            published_identity_id("v1", "plant-a", "axis", {"a": 1, "b": 2}),
        )
        with self.assertRaises(ValueError):
            published_identity_id("v1", "", "axis", {"a": 1})

    def test_b2_canonical_vectors_and_rejections(self):
        vectors = [
            ({"z": 0, "a": [True, None, "é", "\\n", {"β": 2}]}, '{"a":[true,null,"é","\\\\n",{"β":2}],"z":0}'),
            ([1, 1.0], "[1,1]"),
            (10**20, "100000000000000000000"),
            (1e20, "100000000000000000000"),
            (1e-07, "1e-7"),
            (-0.0, "0"),
        ]
        for value, expected in vectors:
            with self.subTest(value=value):
                self.assertEqual(canonical_json(value), expected)
        for invalid in ({1: "x"}, (1, 2), float("nan"), float("inf")):
            with self.subTest(invalid=invalid), self.assertRaises((TypeError, ValueError)):
                canonical_json(invalid)
        from decimal import Decimal
        from fractions import Fraction
        for invalid in (Decimal("1"), Fraction(1, 2), object()):
            with self.subTest(invalid=type(invalid)), self.assertRaises(TypeError):
                canonical_json(invalid)
        self.assertEqual(NAMESPACE, uuid5(NAMESPACE_URL, "sinumerik-core"))
        self.assertEqual(str(NAMESPACE), "fc2d957d-05df-5b99-a0b5-ef2d938a962e")
        for version in ("v2", "1", "v1.0.0"):
            with self.assertRaises(ValueError):
                published_identity_id(version, "plant-a", "axis", {"x": 1})
        for args in (("v1", "", "axis", {"x": 1}), ("v1", "plant-a", "", {"x": 1})):
            with self.assertRaises(ValueError):
                published_identity_id(*args)

    def test_b2_identity_context_changes_id_and_legacy_remains_explicit(self):
        base = published_identity_id("v1", "plant-a", "axis", {"x": 1})
        self.assertNotEqual(base, published_identity_id("v1", "plant-b", "axis", {"x": 1}))
        self.assertNotEqual(base, published_identity_id("v1", "plant-a", "drive", {"x": 1}))
        self.assertTrue(identity_id.legacy)
        self.assertEqual(identity_id("axis", {})[1], "stable")

    def test_sparse_production_evidence_uses_original_indices_and_never_confirms_bad_mapping(self):
        doc = {"topology_actual": {"1": {"components": [
                    {"number": 24}, {"number": 44}] }},
               "servo_objects": [{"unit": 1, "identity": {"bus_id": 1, "slave": 2, "do": 3},
                    "sensor_refs": [
                        {"source_index": 7, "encoder_source_index": 9, "component": 24,
                         "encoder": 44, "mapping_status": "resolved"},
                        {"source_index": True, "encoder_source_index": 2, "component": 24,
                         "encoder": 44, "mapping_status": "resolved"},
                        {"source_index": 8, "encoder_source_index": None, "component": 24,
                         "encoder": 44, "mapping_status": "ambiguous_mapping"}]}]}
        axes = [{"status": "confirmed", "chain": {"bus_id": 1, "slave": 2, "do": 3, "cu": 1}, "axis_unit": 2}]
        _, relations = _equipment_chain(doc, axes)
        sensor = [r for r in relations if r["kind"] == "DRIVE_TO_SENSOR_MODULE"]
        encoder = [r for r in relations if r["kind"] == "SENSOR_TO_ENCODER"]
        self.assertEqual(sensor[0]["evidence"]["reference"]["index"], 7)
        self.assertEqual(encoder[0]["evidence"]["reference"]["index"], 9)
        self.assertTrue(all(r["status"] == "unresolved" for r in sensor[1:] + encoder[1:]))
        self.assertIsNone(sensor[1]["evidence"]["reference"])
        self.assertIsNone(encoder[2]["evidence"]["reference"])

    def test_provisional_identity_is_snapshot_scoped_and_distinct(self):
        value = provisional_identity_id("v1", "plant-a", "snap-1", "axis", {"index": 4})
        expected_name = 'v1|plant-a|snap-1|provisional|axis|{"index":4}'
        self.assertEqual(value, str(uuid5(uuid5(NAMESPACE_URL, "sinumerik-core"), expected_name)))
        self.assertNotEqual(value, published_identity_id("v1", "plant-a", "axis", {"index": 4}))
        with self.assertRaises(ValueError):
            provisional_identity_id("v1", "plant-a", "", "axis", {"index": 4})

    def test_sparse_union_preserves_unresolved_index_and_evidence_source(self):
        rows = [(5, 130, 1, 107, 0, 11), (5, 130, 1, 142, 7, 44),
                (5, 130, 1, 145, 7, 9)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reads.jsonl"
            path.write_text("".join(json.dumps({"area": a, "block": b, "unit": u,
                "param": p, "index": i, "status": "ok", "value": v}) + "\n"
                for a, b, u, p, i, v in rows), encoding="utf-8")
            doc = make_model(path, None)
        ref = doc["servo_objects"][0]["sensor_refs"][0]
        self.assertEqual(ref["source_index"], 7)
        self.assertEqual(ref["encoder_source_index"], 7)
        self.assertEqual(ref["mapping_status"], "unresolved")
        self.assertEqual(ref["mapping_reason"], "missing_sensor_reference")

    def test_conflicting_duplicate_index_is_ambiguous(self):
        rows = [(5, 130, 1, 107, 0, 11), (5, 130, 1, 141, 2, 24),
                (5, 130, 1, 141, 2, 26)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reads.jsonl"
            path.write_text("".join(json.dumps({"area": a, "block": b, "unit": u,
                "param": p, "index": i, "status": "ok", "value": v}) + "\n"
                for a, b, u, p, i, v in rows), encoding="utf-8")
            doc = make_model(path, None)
        ref = doc["servo_objects"][0]["sensor_refs"][0]
        self.assertEqual(ref["mapping_status"], "ambiguous_mapping")
        self.assertEqual(ref["mapping_reason"], "ambiguous_mapping")
        self.assertEqual([x["value"] for x in ref["observations"]], [24, 26])

    def test_malformed_numeric_indices_do_not_collide_with_valid_integer_index(self):
        rows = [(5, 130, 1, 107, 0, 11),
                (5, 130, 1, 141, 1, 24),
                (5, 130, 1, 142, 1, 44),
                (5, 130, 1, 145, 1, 9),
                (5, 130, 1, 141, 1.0, 25),
                (5, 130, 1, 141, True, 26)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reads.jsonl"
            path.write_text("".join(json.dumps({"area": a, "block": b, "unit": u,
                "param": p, "index": i, "status": "ok", "value": v}) + "\n"
                for a, b, u, p, i, v in rows), encoding="utf-8")
            doc = make_model(path, None)
        refs = doc["servo_objects"][0]["sensor_refs"]
        by_type = {(type(ref["source_index"]), ref["source_index"]): ref for ref in refs}
        valid = by_type[(int, 1)]
        self.assertEqual(valid["mapping_status"], "resolved")
        self.assertEqual(valid["component"], 24)
        self.assertEqual(valid["encoder"], 44)
        self.assertEqual(valid["state"], 9)
        for malformed in (1.0, True):
            ref = by_type[(type(malformed), malformed)]
            self.assertEqual(ref["mapping_status"], "unresolved")
            self.assertEqual(ref["mapping_reason"], "malformed_source_index")
            self.assertIsNone(ref["sm_number"])
            self.assertIsNone(ref["component"])
            self.assertIsNone(ref["encoder"])
            self.assertEqual(len(ref["observations"]), 1)

        self.assertEqual(canonical_json({"a": 1}), canonical_json({"a": 1.0}))
        self.assertEqual(canonical_json({"a": 10**20}), canonical_json({"a": 1e20}))
        self.assertEqual(canonical_json([1, 1.0]), "[1,1]")

    def test_malformed_sparse_indices_are_preserved_with_reason(self):
        malformed = [(["list"], 24), ({"dict": 1}, 25), (None, 26),
                     (1.5, 27), (True, 28), (-1, 29)]
        rows = [(5, 130, 1, 107, 0, 11)] + [
            (5, 130, 1, 141, index, value)
            for index, value in malformed
        ]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reads.jsonl"
            path.write_text("".join(json.dumps({"area": a, "block": b, "unit": u,
                "param": p, "index": i, "status": "ok", "value": v}) + "\n"
                for a, b, u, p, i, v in rows), encoding="utf-8")
            doc = make_model(path, None)
        refs = doc["servo_objects"][0]["sensor_refs"]
        sources = [r["source_index"] for r in refs]
        self.assertEqual(len(sources), len(malformed))
        self.assertTrue(all(any(source == index for source in sources)
                            for index, _ in malformed))
        self.assertTrue(all(r["mapping_status"] == "unresolved" for r in refs))
        self.assertTrue(all(r["mapping_reason"] == "malformed_source_index" for r in refs))
        self.assertTrue(all(r["sm_number"] is None for r in refs))
        self.assertTrue(all(r["component"] is None for r in refs))



if __name__ == "__main__":
    unittest.main()
