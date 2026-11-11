import unittest

from topology100.identity_context import (
    CaptureHostIdentity,
    InstallationIdentity,
    identity_from_legacy,
    resolve_installation_identity,
)
from topology100.adapter_legacy import project_legacy


class InstallationCaptureIdentityTests(unittest.TestCase):
    def trusted(self, identifier, field="plant_code", ref="config:plant"):
        return {"identifier": identifier, "source_kind": "trusted_configuration",
                "source_field": field, "scope": "plant", "stability": "deployment",
                "confidence": "high",
                "evidence_ref": ref}

    def test_trusted_metadata_independent_of_capture_host(self):
        a = resolve_installation_identity([self.trusted("plant-7")])
        b = resolve_installation_identity([self.trusted("plant-7")])
        host_a = CaptureHostIdentity("host-a", adapter="replay")
        host_b = CaptureHostIdentity("host-b", adapter="replay")
        self.assertEqual(a, b)
        self.assertNotEqual(host_a, host_b)

    def test_missing_source_is_unknown_even_with_host_context(self):
        self.assertEqual(resolve_installation_identity(), InstallationIdentity.unknown())

    def test_multiple_installations_on_one_host_remain_distinct(self):
        one = resolve_installation_identity([self.trusted("plant-1")])
        two = resolve_installation_identity([self.trusted("plant-2")])
        self.assertNotEqual(one.identifier, two.identifier)

    def test_display_names_are_not_installation_sources(self):
        result = resolve_installation_identity([{"identifier": "Mill A", "source_kind": "display_name"}])
        self.assertEqual(result.status, "unknown")

    def test_partial_trusted_configuration_is_ignored(self):
        source = self.trusted("plant-7")
        for field in ("source_field", "scope", "evidence_ref"):
            partial = {key: value for key, value in source.items() if key != field}
            with self.subTest(field=field):
                self.assertEqual(resolve_installation_identity([partial]), InstallationIdentity.unknown())

    def test_missing_evidence_ref_is_ignored_without_raising(self):
        source = self.trusted("plant-7")
        source.pop("evidence_ref")
        self.assertEqual(resolve_installation_identity([source]).status, "unknown")

    def test_conflict_preserves_source_references(self):
        result = resolve_installation_identity([
            self.trusted("plant-1", ref="deployment:a"),
            self.trusted("plant-2", ref="deployment:b"),
        ])
        self.assertEqual(result.status, "conflict")
        self.assertEqual(result.evidence_ref, "deployment:a,deployment:b")

    def test_legacy_envelope_round_trips_without_reinterpretation(self):
        doc = {"axes": [], "components": [], "drives": [], "connections": [], "summary": {}}
        old = project_legacy(doc, installation_id="legacy-site").to_dict()
        self.assertEqual(old["installation_id"], "legacy-site")
        self.assertNotIn("installation_identity", old)

    def test_legacy_identity_is_provisional_not_confirmed(self):
        value = identity_from_legacy({"installation_id": "legacy-site"})
        self.assertEqual(value.status, "provisional")
        with self.assertRaises(ValueError):
            InstallationIdentity("legacy-site", "legacy_field", "installation_id",
                                 "legacy", "low", None, "confirmed")

    def test_identity_contract_fields_are_additive_and_distinct(self):
        self.assertNotEqual(InstallationIdentity, CaptureHostIdentity)
        self.assertIn("host_id", CaptureHostIdentity("h").to_dict())
        self.assertIsNone(InstallationIdentity.unknown().identifier)


if __name__ == "__main__":
    unittest.main()
