"""Exercise copied real inputs, including failing events and sequence wrap."""
import json
from pathlib import Path
import unittest
import revalidate_latest_runtime as v

ROOT=Path(__file__).resolve().parents[3]
FIXTURES=ROOT/'research/phase11/REAL_INPUT_CORPUS'

class RealFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=v.validate(FIXTURES,FIXTURES/'real_tests/logs/RUN_ALL_21704_14346.txt')
        cls.slots=cls.result['mc']['slots_detail']
        cls.rounds=cls.result['mc']['rounds_detail']
        cls.transitions=cls.result['observed_word_header']['transitions_detail']

    def test_complete_fixture_replay(self):
        self.assertEqual(self.result['strict_valid_responses'],198)
        self.assertEqual(len(self.transitions),197)
        self.assertEqual(self.result['structural_mismatches'],[])
        self.assertEqual(self.result['observed_word_header']['counter_mismatches'],[])
        self.assertEqual(self.result['unexpected_runner_outcomes'],[])
        original=json.loads((FIXTURES/'latest_runtime_validation.json').read_text())
        for k in ('mc','dde_formats','reads_detail','steps_detail','observed_word_header'):
            self.assertEqual(self.result[k],original[k])

    def test_error_scope_and_order(self):
        r100=[x for x in self.slots if x['step']==27 and x['item'].endswith('/R[u1,100]')]
        self.assertEqual(len(r100),1)
        self.assertEqual(r100[0]['error'],'0x85000903')
        r10=[x for x in self.slots if x['step']==27 and x['item'].endswith('/R[u1,10]')]
        self.assertEqual(r10[0]['value'],'0')
        self.assertEqual(r10[0]['error'],'0x00000000')
        self.assertEqual(sum(x['error']=='0x81000303' for x in self.slots),23)
        self.assertEqual(len(self.result['mc']['partial_error_rounds']),7)
        self.assertTrue(all(x['hresult']=='0x00000000' for x in self.result['mc']['partial_error_rounds']))
        for step in (17,18):
            ss=[x for x in self.slots if x['step']==step]
            self.assertTrue(len({x['item'] for x in ss})<len(ss))
        repeat=[x for x in self.rounds if x['step']==90]
        self.assertEqual([x['processed'] for x in repeat],[20,20])

    def test_counter_shape_and_all_bad_bridge(self):
        bridge=lambda a,b: next(t for t in self.transitions if t['from_step']==a and t['to_step']==b)
        self.assertEqual(bridge(79,81)['mc_elements'],5)
        self.assertEqual(bridge(81,83)['mc_elements'],3)
        self.assertEqual(bridge(83,85)['mc_elements'],0)
        self.assertEqual(bridge(89,91)['actual'],41)
        assoc=json.loads((FIXTURES/'provenance.json').read_text())['associations']
        seq={Path(x['capture']).name:(FIXTURES/x['capture']).read_bytes()[7] for x in assoc if x['format']=='binary'}
        self.assertTrue(any(seq[t['to_capture']]<seq[t['from_capture']] for t in self.transitions))

    def test_timestamp_errors_are_not_clock_values(self):
        accepted=[x for x in self.rounds if x['processed']]
        self.assertEqual(len(accepted),63)
        self.assertTrue(all(x['timestamp_scode']==['0x80020004'] for x in accepted))
        for mode in (0,1,2):
            clocks=[x for x in self.slots if x['cache']==mode and x['value_type']=='0x0007']
            self.assertTrue(clocks)
            self.assertTrue(all(x['value'] is not None for x in clocks))
        differences=json.loads((FIXTURES/'clock_value_differences.json').read_text())
        self.assertEqual(len(differences),206)
        self.assertTrue(any(x['ole_date_delta']!=0 for x in differences))

    def test_differential_and_failed_formats(self):
        diff=json.loads((FIXTURES/'static_differential.json').read_text())
        self.assertEqual(len(diff),119)
        self.assertTrue(all(x['match'] for x in diff))
        self.assertEqual(self.result['dde_formats']['binary']['FAILED'],11)
        self.assertEqual(self.result['dde_formats']['text']['FAILED'],7)
        self.assertEqual(self.result['dde_formats']['oem'],{'FAILED':23})
        decoded=json.loads((FIXTURES/'decoded_binary.json').read_text())
        self.assertEqual({x['kind'] for x in decoded},{'integer','double','string','BCD_clock'})
        self.assertTrue(all(x['value']['all_nibbles_decimal'] for x in decoded if x['kind']=='BCD_clock'))

if __name__=='__main__':
    unittest.main()
