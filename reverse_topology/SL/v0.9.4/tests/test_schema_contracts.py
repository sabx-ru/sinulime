import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
API = ROOT / "docs/schema/api-v1.schema.json"
TOPOLOGY = ROOT / "docs/schema/topology-v1.schema.json"


class SchemaContractStructureTests(unittest.TestCase):
    def test_resync_data_is_a_disjoint_error_data_branch(self):
        api = json.loads(API.read_text())
        error_data = api["$defs"]["errorData"]["oneOf"]
        self.assertEqual(error_data[0]["$ref"], "#/$defs/resyncData")
        generic = error_data[1]
        self.assertEqual(generic["$ref"], "#/$defs/jsonObject")
        self.assertEqual(
            generic["not"]["required"],
            api["$defs"]["resyncData"]["required"],
        )

    def test_closed_result_envelopes_declare_all_of_properties(self):
        api = json.loads(API.read_text())
        defs = api["$defs"]
        self.assertFalse(defs["resultEnvelope"]["additionalProperties"])
        self.assertFalse(defs["pageMeta"]["additionalProperties"])
        for name in (
            "capabilitiesResult", "healthResult", "snapshotListResult",
            "snapshotGetResult", "topologyQueryResult", "reconcileResult",
            "evidenceGetResult", "eventListResult",
        ):
            self.assertFalse(defs[name]["additionalProperties"])
            self.assertFalse(defs[name]["allOf"][1]["additionalProperties"])

    def test_exact_evidence_observation_one_of_remains(self):
        topology = json.loads(TOPOLOGY.read_text())
        evidence = topology["$defs"]["evidence"]
        self.assertEqual(len(evidence["oneOf"]), 2)
        self.assertEqual(evidence["oneOf"][0]["required"], ["observed_value"])
        self.assertEqual(evidence["oneOf"][1]["required"], ["observed_absent"])
        self.assertEqual(
            evidence["oneOf"][1]["properties"]["observed_absent"]["const"],
            True,
        )


if __name__ == "__main__":
    unittest.main()
