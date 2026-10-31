import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research/phase12/SCRIPTS/CAPTURE_VALIDATOR.py"
spec = importlib.util.spec_from_file_location("capture_validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
CORPUS = ROOT / "research/phase11/REAL_INPUT_CORPUS"


class CaptureValidatorTests(unittest.TestCase):
    def test_saved_corpus_is_valid(self):
        result = validator.validate(CORPUS)
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["binary_count"], 198)
        self.assertEqual(result["text_count"], 69)
        self.assertEqual(result["association_count"], 267)

    def test_binary_parser_rejects_corruption(self):
        good = bytes.fromhex("14000100010002660100000004000000f9f8f7f602000000")
        self.assertEqual(validator.capture_parser.parse_binary(good)["value"], 2)
        with self.assertRaises(ValueError):
            validator.capture_parser.parse_binary(good[:16] + b"BAD!" + good[20:])


if __name__ == "__main__":
    unittest.main()
