"""Regression tests for CU-overrun observed in CNC_135 / CNC_152 v0.9.2.

All checks run offline, never open a socket, and replay values from the
2026-10-26 captured journals. No actual CNC is contacted during tests.
"""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest

from topology092.collect import configured_cu_indices, collect_nck, Reader
from topology092.readvar import NckProtocolError, parse_s7


CNC_CASES = (
    ('CNC_135', [6500, 6560, 6550, 6540, 6530], [9, 7, 4, 7, 6]),
    ('CNC_152', [6500, 6530], [6, 3]),
)


def old_journal(services, counts):
    """Former v0.9.2 inventory plus the invalid overrun probes."""
    events = []
    for i in range(15):
        value = services[i] if i < len(services) else 0
        events.append({'kind':'read', 'area':0, 'block':26, 'unit':1,
                       'param':13120, 'index':i, 'dtype':'u32le',
                       'status':'ok', 'value':value, 'raw_hex':value.to_bytes(4,'little').hex()})
    events.append({'kind':'read', 'area':0, 'block':26, 'unit':1,
                   'param':13120, 'index':15, 'dtype':'u32le',
                   'status':'item_error', 'value':None, 'raw_hex':None})
    for i, value in enumerate(counts, 1):
        events.append({'kind':'read', 'area':5, 'block':128, 'unit':i,
                       'param':102, 'index':0, 'dtype':'u16be',
                       'status':'ok', 'value':value, 'raw_hex':value.to_bytes(2,'big').hex()})
    for i in range(len(counts)+1, len(counts)+4):
        for attempt in range(2):
            events.append({'kind':'read', 'area':5, 'block':128, 'unit':i,
                           'param':102, 'index':0, 'dtype':'u16be',
                           'status':'protocol_error', 'attempt':attempt+1,
                           'error':'NckProtocolError: Expected S7 AckData frame',
                           'raw_hex':None, 'value':None})
    return events


class ReplayClient:
    calls = []
    active_count = 0
    archived = {}
    def __init__(self, host, timeout=8):
        self.connected = False
    def connect(self):
        self.connected = True
    def close(self):
        self.connected = False
    def read(self, area, block, unit, column, index):
        key = (area, block, unit, column, index)
        type(self).calls.append(key)
        if area == 5 and block == 128 and unit > type(self).active_count:
            raise NckProtocolError('Expected S7 AckData frame', response=b'\x32\x02' + bytes(10))
        if key in type(self).archived:
            return dict(type(self).archived[key])
        return {'status':'item_error', 'code':'0x03', 'error':'Absent on this fixture'}


class HotfixTests(unittest.TestCase):
    def test_inventory_uses_configured_units_not_range_16(self):
        for name, services, counts in CNC_CASES:
            with self.subTest(name=name):
                values = services+[0]*(15-len(services))+[None]
                self.assertEqual(configured_cu_indices(values),
                                 list(enumerate(services, start=1)))

    def test_inventory_fails_closed_when_middle_value_unknown(self):
        values = [6500, None, 6550]+[0]*13
        with self.assertRaisesRegex(RuntimeError, 'missing at index'):
            configured_cu_indices(values)

    def test_inventory_preserves_explicit_slot_indices_across_zero_gaps(self):
        self.assertEqual(configured_cu_indices([6500,0,6550]+[0]*12+[None]),
                         [(1,6500), (3,6550)])

    def test_inventory_rejects_zero_units(self):
        with self.assertRaisesRegex(RuntimeError, 'No CU configured'):
            configured_cu_indices([0]*15+[None])

    def test_resume_from_092_captures_135_and_152(self):
        for name, services, counts in CNC_CASES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as td:
                path = Path(td)/'reads.jsonl'
                events = old_journal(services, counts)
                path.write_text(''.join(json.dumps(e)+'\n' for e in events), encoding='utf8')
                ReplayClient.active_count = len(services)
                ReplayClient.calls = []
                ReplayClient.archived = {
                    (e['area'],e['block'],e['unit'],e['param'],e['index']):
                        {'status':'ok','raw_hex':e['raw_hex']}
                    for e in events if e['status']=='ok'
                }
                # Last index is rejected by NCK; return an explicit item-level refusal.
                ReplayClient.archived[(0,26,1,13120,15)] = {'status':'item_error','code':'0x03'}
                result = collect_nck(
                    'fixture', td, interval_ms=0, target=False, retries=0,
                    reconnect_pause=0, p978_cap=16, resume=True,
                    client_factory=ReplayClient,
                )
                self.assertEqual(result['status'], 'incomplete')
                self.assertTrue(any('length' in x for x in result['incomplete_reasons']))
                self.assertEqual(result['cu'], list(enumerate(counts,1)))
                self.assertFalse(any(area==5 and block==128 and unit>len(counts)
                                     for area,block,unit,param,index in ReplayClient.calls),
                                 'Unexpected CU number probed during resume')
                with path.open(encoding='utf8') as f:
                    journal = [json.loads(line) for line in f if line.strip()]
                self.assertEqual(len([e for e in journal if e.get('kind')=='read'
                                      and e.get('area')==5 and e.get('block')==128
                                      and e.get('unit')==len(counts)+1]), 2)
                # Same two prior unsuccessful probes, none newly appended.

    def test_unexpected_ack_keeps_bounded_raw_diagnostic(self):
        frame = b'\x32\x02' + bytes(600)
        with self.assertRaises(NckProtocolError) as caught:
            parse_s7(frame, expected_ref=1, expected_function=4)
        error = caught.exception
        self.assertEqual(error.response_length, len(frame))
        self.assertEqual(error.response_hex, frame[:256].hex())
        self.assertIn('ROSCTR=0x02', str(error))

    def test_reader_logs_protocol_failure_raw_without_forcing_item_error(self):
        class Rejecting:
            def __init__(self,host,timeout=8):pass
            def connect(self):pass
            def close(self):pass
            def read(self,**kwargs):
                raise NckProtocolError('Unexpected S7 ROSCTR', response=b'\x32\x02'+bytes(10))
        with tempfile.TemporaryDirectory() as td:
            reader=Reader('fixture',td,interval_ms=0,retries=0,client_factory=Rejecting)
            self.assertIsNone(reader.cu(1,102))
            reader.close()
            data=json.loads((Path(td)/'reads.jsonl').read_text())
            self.assertEqual(data['status'],'protocol_error')
            self.assertEqual(data['response_length'],12)
            self.assertTrue(data['response_hex'].startswith('3202'))

if __name__=='__main__': unittest.main()
