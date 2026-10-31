import json
import unittest
from pathlib import Path

from topology100.adapter_legacy import project_legacy
from topology100.contracts import EndpointIdentity, validate_confirmation, validate_envelope
from topology100.identity import canonical_json, endpoint_identity, identity_id
from topology100.reconcile import reconcile, unavailable
from topology100.evidence import build_evidence, write_evidence


class Stage2ContractsTests(unittest.TestCase):
    def _envelope(self, evidence):
        return {"schema": "sinumerik-core/read-only-topology/v1", "snapshot_id": "s", "revision": 0,
                "captured_at": "2026-01-01T00:00:00Z", "mode": "replay", "installation_id": "i",
                "completeness": "partial", "actual": {"availability": "unavailable", "reason": "x"},
                "target": {"availability": "unavailable", "reason": "x"},
                "reconciliation": {"actual_snapshot_id": None, "target_snapshot_id": None,
                                    "status": "not_comparable", "reason": "x", "items": [], "extensions": {}},
                "evidence": evidence, "unresolved": [], "extensions": {}}

    def _evidence(self, evidence_id, artifact_id="a", ref_artifact_id=None):
        ref = {"source_ref": {"index": 0}}
        if ref_artifact_id is not None:
            ref["artifact_id"] = ref_artifact_id
        return {"evidence_id": evidence_id, "artifact_id": artifact_id, "artifact_ref": ref,
                "endpoint_identity": {"object_id": "o", "kind": "object", "selector": {"object_key": "o"}, "identity_status": "stable"},
                "observed_at": "2026-01-01T00:00:00Z", "quality": "ok", "rule_id": "r",
                "rule_version": "1", "extensions": {}}

    def test_identity_extensions_are_validated(self):
        envelope = self._envelope([])
        envelope["installation_identity"] = {
            "identifier": "plant-7", "source_kind": "trusted_configuration",
            "source_field": "plant_code", "scope": "plant", "confidence": "high",
            "stability": "deployment", "evidence_ref": "config:plant", "status": "confirmed"}
        envelope["capture_host_identity"] = {"host_id": "host-a", "process_id": "42"}
        validate_envelope(envelope)
        for bad in ({**envelope, "installation_identity": {**envelope["installation_identity"], "status": "garbage"}},
                    {**envelope, "capture_host_identity": {"host_id": 42}}):
            with self.assertRaises(ValueError):
                validate_envelope(bad)

    def test_installation_identity_rejects_untrusted_confirmed_source(self):
        envelope = self._envelope([])
        identity = {"identifier": "mill-a", "source_kind": "display_name",
                    "source_field": "name", "scope": "host", "confidence": "high",
                    "stability": "snapshot", "evidence_ref": "host:name", "status": "confirmed"}
        with self.assertRaisesRegex(ValueError, "trusted source"):
            validate_envelope({**envelope, "installation_identity": identity})

    def test_installation_identity_statuses_keep_consistent_value_object_invariants(self):
        envelope = self._envelope([])
        confirmed = {"identifier": "plant-7", "source_kind": "trusted_configuration",
                     "source_field": "plant_code", "scope": "plant", "confidence": "high",
                     "stability": "deployment", "evidence_ref": "config:plant", "status": "confirmed"}
        cases = [
            {**confirmed, "status": "unknown", "identifier": None, "source_kind": None,
             "source_field": None, "scope": None, "stability": None, "evidence_ref": None,
             "confidence": "unknown"},
            {**confirmed, "status": "conflict", "identifier": "plant-7"},
            {**confirmed, "status": "conflict", "identifier": None, "source_kind": "conflict",
             "source_field": "installation_id", "scope": "conflict", "stability": None,
             "confidence": "unknown", "evidence_ref": "config:a,config:b"},
            {**confirmed, "status": "provisional", "confidence": "confirmed"},
            {**confirmed, "status": "provisional", "identifier": None},
        ]
        validate_envelope({**envelope, "installation_identity": cases[0]})
        for identity in cases[1:2] + cases[3:]:
            with self.subTest(identity=identity):
                with self.assertRaises(ValueError):
                    validate_envelope({**envelope, "installation_identity": identity})
        validate_envelope({**envelope, "installation_identity": cases[2]})

    def test_identity_serialization_preserves_stability(self):
        from topology100.identity_context import InstallationIdentity
        identity = InstallationIdentity("plant-7", "plant_id", "plant_code", "plant",
                                        "deployment", "high", "config:plant", "confirmed")
        self.assertEqual(identity.to_dict()["stability"], "deployment")

    def test_legacy_envelope_without_identity_extensions_remains_valid(self):
        validate_envelope(self._envelope([]))

    def test_artifact_identity_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "artifact_id"):
            validate_envelope(self._envelope([self._evidence("e1", "a", "different")]))

    def test_duplicate_evidence_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "evidence_id"):
            validate_envelope(self._envelope([self._evidence("e1"), self._evidence("e1")]))

    def test_relation_duplicate_evidence_ids_are_rejected(self):
        relation = {"id": "r1", "kind": "representation", "status": "unresolved",
                    "from": {"object_id": "a", "kind": "object", "selector": {"object_key": "a"}, "identity_status": "unknown"},
                    "to": {"object_id": "b", "kind": "object", "selector": {"object_key": "b"}, "identity_status": "unknown"},
                    "rule_id": "r", "rule_version": "1", "checks": ["c"],
                    "evidence_ids": ["e1", "e1"], "extensions": {}}
        with self.assertRaisesRegex(ValueError, "evidence_ids"):
            validate_confirmation(relation, {"e1"})

    def test_legacy_connection_does_not_reuse_unrelated_axis_evidence(self):
        envelope = project_legacy({"axes": [{"axis_unit": 1, "name": "X", "status": "confirmed"}],
                                   "connections": [{"from": {"cu": 1, "component": 2},
                                                    "to": {"cu": 1, "component": 3},
                                                    "status": "confirmed", "confidence": "confirmed"}],
                                   "summary": {"read_statuses": {}}})
        connection = envelope.actual["connections"][0]
        self.assertNotEqual(connection["evidence_ids"][0], envelope.evidence[0].evidence_id)
        self.assertEqual(connection["status"], "reference_only")
    def test_confirmed_relation_requires_stable_endpoints_and_resolvable_evidence(self):
        relation = {"id": "r1", "kind": "representation", "status": "confirmed", "from": {"object_id": "a", "kind": "object", "selector": {"object_key": "a"}, "identity_status": "stable"},
                    "to": {"object_id": "b", "kind": "object", "selector": {"object_key": "b"}, "identity_status": "stable"}, "rule_id": "r",
                    "rule_version": "1", "checks": ["reciprocal"], "evidence_ids": ["e1"], "extensions": {}}
        validate_confirmation(relation, {"e1"})
        with self.assertRaises(ValueError):
            validate_confirmation({**relation, "evidence_ids": []}, {"e1"})
        with self.assertRaisesRegex(ValueError, "resolvable evidence"):
            validate_confirmation(relation)
        with self.assertRaises(ValueError):
            validate_confirmation({**relation, "from": {"object_id": "a", "identity_status": "provisional"}}, {"e1"})

    def test_confirmed_relation_cannot_bypass_evidence_gate_with_empty_index(self):
        relation = {"id": "r1", "kind": "representation", "status": "confirmed",
                    "from": {"object_id": "a", "kind": "object", "selector": {"object_key": "a"}, "identity_status": "stable"},
                    "to": {"object_id": "b", "kind": "object", "selector": {"object_key": "b"}, "identity_status": "stable"},
                    "rule_id": "r", "rule_version": "1", "checks": ["reciprocal"],
                    "evidence_ids": ["e1"], "extensions": {}}
        for evidence_index in (None, set(), {"other"}):
            with self.subTest(evidence_index=evidence_index):
                with self.assertRaisesRegex(ValueError, "resolvable evidence|unresolved evidence"):
                    validate_confirmation(relation, evidence_index)
        with self.assertRaisesRegex(ValueError, "non-empty evidence_ids|resolvable evidence"):
            validate_confirmation({**relation, "evidence_ids": []}, {"e1"})
        validate_confirmation(relation, {"e1"})

    def test_confirmed_relation_requires_valid_stable_endpoint_shapes(self):
        relation = {"id": "r1", "kind": "representation", "status": "confirmed",
                    "from": {"object_id": "a", "kind": "object", "selector": {"object_key": "a"}, "identity_status": "stable"},
                    "to": {"object_id": "b", "kind": "object", "selector": {"object_key": "b"}, "identity_status": "stable"},
                    "rule_id": "r", "rule_version": "1", "checks": ["reciprocal"],
                    "evidence_ids": ["e1"], "extensions": {}}
        validate_confirmation(relation, {"e1"})
        for endpoint in ({**relation["from"], "identity_status": "unknown"},
                         {**relation["from"], "selector": {}},
                         {"object_id": "a", "kind": "unknown", "selector": {}, "identity_status": "stable"}):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    validate_confirmation({**relation, "from": endpoint}, {"e1"})

    def test_endpoint_identity_status_round_trips_without_implicit_promotion(self):
        provisional = EndpointIdentity("a", "object", {"object_key": "a"}, "provisional")
        serialized = provisional.to_dict()
        self.assertEqual(serialized["identity_status"], "provisional")
        relation = {"id": "r1", "kind": "representation", "status": "confirmed",
                    "from": serialized,
                    "to": {"object_id": "b", "kind": "object", "selector": {"object_key": "b"}, "identity_status": "stable"},
                    "rule_id": "r", "rule_version": "1", "checks": ["reciprocal"],
                    "evidence_ids": ["e1"], "extensions": {}}
        with self.assertRaisesRegex(ValueError, "stable endpoint identities"):
            validate_confirmation(relation, {"e1"})
        self.assertFalse(hasattr(EndpointIdentity, "promote"))
        self.assertEqual(EndpointIdentity("x").identity_status, "unknown")
        for status in ("stable", "provisional", "unknown"):
            value = EndpointIdentity("x", "object", {"object_key": "x"}, status)
            self.assertEqual(value.to_dict()["identity_status"], status)
        for invalid in (None, "", "invalid"):
            bad = {**serialized, "identity_status": invalid}
            with self.assertRaisesRegex(ValueError, "identity_status"):
                validate_confirmation({**relation, "from": bad}, {"e1"})
        for missing in ({k: v for k, v in serialized.items() if k != "identity_status"},):
            with self.assertRaisesRegex(ValueError, "identity_status"):
                validate_confirmation({**relation, "from": missing}, {"e1"})

    def test_legacy_axis_evidence_preserves_exact_source_ref(self):
        source_ref = {"area": 3, "block": 26, "unit": 7, "param": 30110, "index": 2}
        envelope = project_legacy({"axes": [{"axis_unit": 7, "name": "X", "status": "confirmed",
                                               "evidence": {"md30110": source_ref}}],
                                   "summary": {"read_statuses": {}}})
        axis_evidence = envelope.evidence[0].to_dict()
        self.assertEqual(axis_evidence["artifact_ref"]["source_ref"],
                         {**source_ref, "source": "NCK.ReadVar+SDB"})

    def test_legacy_axis_without_source_is_reference_only(self):
        envelope = project_legacy({"axes": [{"axis_unit": 7, "name": "X", "status": "confirmed"}],
                                   "summary": {"read_statuses": {}}})
        self.assertEqual(envelope.actual["objects"][0]["status"], "reference_only")
        self.assertNotIn("source", envelope.evidence[0].to_dict()["artifact_ref"]["source_ref"])

    def test_legacy_projection_is_additive(self):
        root = Path(__file__).parents[1] / "runs" / "cnc152"
        legacy = build_evidence(root / "readvar" / "reads.jsonl", root / "sdb")
        envelope = project_legacy(legacy)
        self.assertEqual(envelope.to_dict()["mode"], "replay")
        self.assertGreaterEqual(len(envelope.evidence), len(legacy["axes"]))
        self.assertEqual(len(envelope.evidence), len(legacy["axes"]) + len(legacy["connections"]))
        with self.subTest("write"):
            import tempfile
            with tempfile.TemporaryDirectory() as d:
                write_evidence(legacy, d)
                self.assertTrue(Path(d, "evidence.json").exists())
                self.assertTrue(Path(d, "evidence.v1.json").exists())
                self.assertEqual(json.loads(Path(d, "evidence.json").read_text())["schema"], "read-only-topology/v1.0.0")

    def test_evidence_record_is_schema_conformant(self):
        root = Path(__file__).parents[1] / "runs" / "cnc152"
        envelope = project_legacy(build_evidence(root / "readvar" / "reads.jsonl", root / "sdb"))
        self.assertTrue(envelope.to_dict()["evidence"])
        for record in envelope.to_dict()["evidence"]:
            self.assertIn("artifact_id", record)
            self.assertIn("extensions", record)
            self.assertEqual(record["endpoint_identity"]["kind"], "logical_object")

    def test_confirmed_connections_and_relations_are_validated(self):
        bad = {"status": "confirmed", "confidence": "confirmed", "from": {}, "to": {},
               "rule_id": "r", "rule_version": "1", "checks": ["c"], "evidence_ids": ["e"]}
        with self.assertRaises(ValueError):
            from topology100.contracts import validate_envelope
            validate_envelope(type("E", (), {"evidence": (), "actual": {"connections": [bad]},
                                             "target": {},})())


class Stage2IdentityTests(unittest.TestCase):
    def test_uuid5_is_order_independent_and_provisional_is_distinct(self):
        a = identity_id("axis", {"cu": 1, "do": 2})
        b = identity_id("axis", {"do": 2, "cu": 1})
        self.assertEqual(a, b)
        self.assertNotEqual(a[0], identity_id("axis", provisional_key="axis:1")[0])
        self.assertEqual(canonical_json({"b": 2, "a": 1}), '{"a":1,"b":2}')
        self.assertEqual(endpoint_identity("axis", provisional_key="x")["identity_status"], "provisional")


class Stage2ReconciliationTests(unittest.TestCase):
    def test_bidirectional_statuses_and_unavailable_contract(self):
        result = reconcile({"items": [{"id": "same", "v": 1}, {"id": "removed"}]},
                           {"items": [{"id": "same", "v": 1}, {"id": "changed", "v": 2}]})
        self.assertEqual({i["change"] for i in result["items"]}, {"same", "removed", "added"})
        self.assertEqual(unavailable("timeout"), {"availability": "unavailable", "reason": "timeout"})
        self.assertEqual(reconcile(unavailable("timeout"), {"items": []})["status"], "not_comparable")

    def test_reconciliation_uses_refs_extensions_and_top_level_reason(self):
        result = reconcile({"items": [{"id": "a", "selector": {"x": 1}}]},
                           {"items": [{"id": "a", "selector": {"x": 2}}]})
        self.assertEqual(result["status"], "not_comparable")
        self.assertEqual(result["reason"], "selector_mismatch")
        self.assertIn("actual_ref", result["items"][0])
        self.assertIn("target_ref", result["items"][0])
        self.assertIn("extensions", result["items"][0])

    def test_duplicate_identity_is_preserved_as_ambiguous(self):
        result = reconcile({"items": [{"id": "a"}, {"id": "a"}]}, {"items": [{"id": "a"}]})
        self.assertEqual(len(result["items"]), 2)
        self.assertTrue(all(i["change"] == "unresolved" for i in result["items"]))
        self.assertTrue(all(i["reason"] == "ambiguous_mapping" for i in result["items"]))


if __name__ == "__main__":
    unittest.main()
