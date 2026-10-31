import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research/phase12/scripts"))
import ncdde_capture_parser as parser

CORPUS = ROOT / "research/phase11/REAL_INPUT_CORPUS"


class CaptureParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = parser.corpus_report(CORPUS)
        cls.decoded = json.loads((CORPUS / "decoded_binary.json").read_text())

    def test_complete_preserved_capture_replay(self):
        self.assertEqual(self.report["binary_count"], 198)
        self.assertEqual(self.report["text_count"], 69)
        self.assertEqual(len(self.report["binary"]), len(self.decoded))
        for actual, expected in zip(self.report["binary"], self.decoded):
            self.assertEqual(actual["payload_hex"], expected["payload_hex"])
            self.assertEqual(actual["sequence"], expected["sequence"])
            self.assertEqual(actual["kind"], expected["kind"])

    def test_binary_offsets_and_payload_stride(self):
        captures = self.report["binary"]
        self.assertTrue(all(x["header_size"] == 20 for x in captures))
        self.assertTrue(all(x["version"] == 1 for x in captures))
        self.assertTrue(all(x["marker"] == "f9f8f7f6" for x in captures))
        self.assertTrue(all(x["payload_size"] == len(bytes.fromhex(x["payload_hex"])) for x in captures))
        self.assertEqual({x["kind"] for x in captures}, {"integer", "double", "string", "BCD_clock"})
        self.assertTrue(all(x["all_nibbles_decimal"] for x in captures if x["kind"] == "BCD_clock"))

    def test_string_payload_uses_nul_terminator(self):
        data = bytearray(20)
        data[0:2] = (20).to_bytes(2, "little")
        data[2:4] = (1).to_bytes(2, "little")
        data[4] = 100
        data[6] = 6
        payload = b"AB\x00CD"
        data[12:16] = len(payload).to_bytes(4, "little")
        data[16:20] = bytes.fromhex("f9 f8 f7 f6")
        data.extend(payload)
        parsed = parser.parse_binary(bytes(data))
        self.assertEqual(parsed["kind"], "string")
        self.assertEqual(parsed["text"], "AB")

    def test_text_is_not_binary_header_format(self):
        text = self.report["text"]
        self.assertEqual(len(text), 69)
        self.assertTrue(all(x["format"] == "CF_TEXT" for x in text))
        self.assertTrue(all(not (len(x["raw_hex"]) >= 40 and x["raw_hex"][32:40] == "f9f8f7f6") for x in text))
        self.assertTrue(any(x["text"] == "5" for x in text))

    def test_corruption_is_rejected_at_exact_header_checks(self):
        valid = bytes.fromhex("14000100010002660100000004000000f9f8f7f602000000")
        self.assertEqual(parser.parse_binary(valid)["value"], 2)
        for changed in (b"\x13" + valid[1:], valid[:2] + b"\x02" + valid[3:], valid[:16] + b"BAD!" + valid[20:]):
            with self.assertRaises(ValueError):
                parser.parse_binary(changed)

    def test_payload_length_mismatch_rejected(self):
        valid = bytes.fromhex("14000100010002660100000008000000f9f8f7f602000000")
        with self.assertRaisesRegex(ValueError, "payload size"):
            parser.parse_binary(valid)


if __name__ == "__main__":
    unittest.main()
