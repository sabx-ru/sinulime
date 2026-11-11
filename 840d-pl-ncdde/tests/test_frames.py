"""Offline checks; run with python3 -m unittest discover -s tests -v."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_frames import check_fixture, decode_frame


class ObservedFrameTests(unittest.TestCase):
    def test_all_observed_frames(self):
        cases = check_fixture(Path(__file__).resolve().parents[1] / 'fixtures' / 'observed_frames.json')
        self.assertEqual(len(cases), 8)

    def test_reject_truncated(self):
        with self.assertRaises(ValueError):
            decode_frame(b'\x14\x00')

    def test_reject_wrong_marker(self):
        with self.assertRaises(ValueError):
            decode_frame(bytes.fromhex('140001000100020001000000040000000000000002000000'))

    def test_reject_bad_length(self):
        with self.assertRaises(ValueError):
            decode_frame(bytes.fromhex('14000100010002000100000010000000F9F8F7F602000000'))


if __name__ == '__main__':
    unittest.main()
