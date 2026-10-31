"""Regression tests use copied fixtures; preserved corpus remains immutable."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('validator', Path(__file__).with_name('revalidate_latest_runtime.py'))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
ROOT = Path(__file__).resolve().parents[3]

class RuntimeValidationTests(unittest.TestCase):
    def test_exact_dword_predicate_and_word_distinction(self):
        raw = bytes.fromhex('14 00 00 00') + bytes(12) + v.MARKER
        self.assertTrue(v.rejected_dword_predicate(raw))
        self.assertFalse(v.valid_binary(raw))
        self.assertFalse(v.valid_binary(raw[:19]))
        self.assertFalse(v.valid_binary(raw[:16] + bytes(4)))
        observed = bytes.fromhex('14 00 01 00') + raw[4:]
        self.assertTrue(v.valid_binary(observed))
        self.assertFalse(v.rejected_dword_predicate(observed))
        self.assertFalse(v.valid_binary(observed[:19]))
        self.assertFalse(v.valid_binary(observed[:16] + bytes(4)))
        self.assertFalse(v.valid_binary(observed[:2] + bytes.fromhex('02 00') + observed[4:]))
        self.assertTrue(v.observed_word_header(observed))

    def test_corpus_and_counter_mutation(self):
        baseline = v.validate(ROOT, ROOT/'real_tests/logs/RUN_ALL_21704_14346.txt')
        self.assertEqual(baseline['steps'], 104)
        self.assertEqual(baseline['strict_valid_responses'], 198)
        self.assertEqual(baseline['strict_transitions'], 197)
        self.assertEqual(baseline['superseded_dword_negative_control']['accepted'], 0)
        self.assertEqual(baseline['observed_word_header']['responses'], 198)
        self.assertEqual(baseline['observed_word_header']['transitions'], 197)
        self.assertEqual(baseline['observed_word_header']['counter_mismatches'], [])
        self.assertEqual(baseline['structural_mismatches'], [])
        self.assertEqual(baseline['mc']['requested_elements'], 606)
        self.assertEqual(baseline['mc']['processed_elements'], 604)
        self.assertEqual(baseline['mc']['rejected_shape_rounds'], 2)
        self.assertEqual(baseline['dde_formats']['oem'], {'FAILED':23})
        # In-memory byte fault tests failure detection without editing originals.
        target = baseline['observed_word_header']['transitions_detail'][5]['to_capture']
        original = Path.read_bytes
        def altered(path):
            data = original(path)
            if path.name == target:
                data = data[:7] + bytes([(data[7]+1)%256]) + data[8:]
            return data
        with patch.object(Path, 'read_bytes', altered):
            changed = v.validate(ROOT, ROOT/'real_tests/logs/RUN_ALL_21704_14346.txt')
        self.assertEqual(len(changed['observed_word_header']['counter_mismatches']), 2)

if __name__ == '__main__':
    unittest.main()
