"""Behavioral regressions for the independent v0.9.2 offline decoder."""
import tempfile
import unittest
import json
from pathlib import Path

from topology092.topology import decode_words, cables
from topology092.sdb import read_sdb_dir


def field(tag, *values):
    return [(tag << 8) | len(values), *values]


def text(value):
    raw = value.encode('latin1')
    return [len(raw), *[int.from_bytes(raw[i:i + 2].ljust(2, b'\0'), 'big')
                         for i in range(0, len(raw), 2)]]


def component(number, kind, links=()):
    data = field(7, *text(f'C{number}')) + field(8, kind) + field(16, number)
    for group, pairs in links:
        data += field(18, group) + field(19, len(pairs))
        for peer, selector in pairs:
            data += field(21, peer) + field(22, selector)
    return data


class TypedRelations(unittest.TestCase):
    def test_non_cliq_groups_are_preserved_separately(self):
        words = component(1, 31, [(1, [(2, 1)]), (5, [(3, 1)])])
        words += component(2, 256, [(1, [(1, 1)])])
        words += component(3, 3800)
        decoded = decode_words(words, 'test')
        self.assertEqual(decoded['components'][0]['groups'][5][0]['peer_component'], 3)
        graph = cables({1: decoded})
        self.assertEqual(len(graph['edges']), 1)
        self.assertEqual(len(graph['relations']), 1)
        self.assertEqual(graph['relations'][0]['type'], 'ANALOG')

    def test_typed_relations_and_classes_export_as_separate_tables(self):
        from topology092.model import write_results
        words=component(1,31,[(5,[(2,1)])])+component(2,3800)
        decoded=decode_words(words,'test')
        graph=cables({1:decoded})
        doc={'summary':{},'axes':[],'topology_actual':{1:decoded},
             'cables_actual':graph,'cu_links':[]}
        with tempfile.TemporaryDirectory() as folder:
            write_results(doc,folder)
            relations=Path(folder,'typed_relations.csv').read_text(encoding='utf-8-sig')
            devices=Path(folder,'components.csv').read_text(encoding='utf-8-sig')
        self.assertIn('ANALOG',relations)
        self.assertIn('NCU',devices)

    def test_mismatched_port_selectors_do_not_verify_cable(self):
        words = component(1, 31, [(1, [(2, 9)])])
        words += component(2, 256, [(1, [(1, 1)])])
        graph = cables({1: decode_words(words, 'test')})
        self.assertEqual(graph['edges'], [])
        self.assertTrue(any(x['reason']=='selector_mismatch' for x in graph['unresolved_ports']))

    def test_unresolved_ports_prevent_false_equal_topology(self):
        from topology092.model import make_model
        words=component(1,31,[(1,[(2,9)])])+component(2,256,[(1,[(1,1)])])
        records=[(102,0,1),(9900,0,len(words)),(9902,0,len(words))]
        records += [(p,i,w) for p in (9901,9903) for i,w in enumerate(words)]
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder,'reads.jsonl')
            with log.open('w') as output:
                for p,i,v in records:
                    output.write(json.dumps({'area':5,'block':128,'unit':1,'param':p,
                                             'index':i,'status':'ok','value':v})+'\n')
            result=make_model(log,None)
        self.assertIsNone(result['summary']['physical_edge_sets_equal'])

    def test_missing_word_at_tlv_end_is_not_complete(self):
        words = component(1, 31) + field(24, None)
        decoded = decode_words(words, 'test')
        self.assertFalse(decoded['complete_tlv'])
        self.assertTrue(decoded['components'][0]['incomplete'])

    def test_incomplete_component_does_not_verify_cable(self):
        words=component(1,31,[(1,[(2,1)])])+field(24,None)
        words+=component(2,256,[(1,[(1,1)])])
        graph=cables({1:decode_words(words,'test')})
        self.assertEqual(graph['edges'],[])
        self.assertTrue(any(x['reason']=='component_incomplete' for x in graph['unresolved_ports']))

    def test_component_type_is_classified_without_guessing_unknowns(self):
        words = (component(1, 31) + component(2, 264) +
                 component(3, 3830) + component(4, 65500))
        items = decode_words(words, 'test')['components']
        self.assertEqual([c['device_class'] for c in items],
                         ['NCU', 'HF_MOTOR_MODULE', 'TERMINAL_BOARD', 'UNKNOWN'])


class SlotEvidence(unittest.TestCase):
    def test_p978_end_marker_bounds_logical_slots(self):
        from topology092.model import resolve_p978_slot
        self.assertEqual(resolve_p978_slot([3,255,1,4],0),(3,'OK'))
        self.assertEqual(resolve_p978_slot([3,255,1,4],1),(None,'EMPTY_SLOT'))
        self.assertEqual(resolve_p978_slot([3,255,1,4],3),(None,'END_MARKER'))
        self.assertEqual(resolve_p978_slot([None,4,1],1),(None,'PREFIX_UNREADABLE'))

    def test_unknown_io_pair_before_known_telegram_marks_slot_uncertain(self):
        header=bytearray(50);header[:2]=b'pp';header[36]=3
        def record(addr, output, size):
            code=addr | (0x8000 if output else 0)
            return code.to_bytes(2,'big')+bytes([0x28,12,1,0,size,7,0x83,0x40,0xfe,0,3,0])
        raw=bytes(header)+record(100,False,20)+record(100,True,12)
        raw+=record(200,False,38)+record(200,True,30)
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'SDB00023.full.bin').write_bytes(raw)
            hw=read_sdb_dir(folder)
        self.assertEqual(hw['slots'][0]['address'],200)
        self.assertFalse(hw['slots'][0]['slot_order_confident'])


class DriveObjectEvidence(unittest.TestCase):
    def test_sparse_sensor_refs_preserve_source_index(self):
        from topology092.model import make_model
        rows=[(5,130,1,107,0,11), (5,130,1,141,0,0),
              (5,130,1,141,1,24), (5,130,1,141,2,0),
              (5,130,1,141,3,26), (5,130,1,145,1,7),
              (5,130,1,145,3,9), (5,130,1,142,1,44),
              (5,130,1,142,3,46)]
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder,'reads.jsonl')
            with log.open('w') as output:
                for a,b,u,p,i,v in rows:
                    output.write(json.dumps({'area':a,'block':b,'unit':u,'param':p,
                                             'index':i,'status':'ok','value':v})+'\n')
            result=make_model(log,None)
        refs=result['servo_objects'][0]['sensor_refs']
        self.assertEqual([x['source_index'] for x in refs],[1,3])
        self.assertEqual([x['state'] for x in refs],[7,9])
        self.assertEqual([x['encoder_source_index'] for x in refs],[1,3])

    def test_missing_sensor_reference_preserves_union_source_index(self):
        from topology092.model import make_model
        rows=[(5,130,1,107,0,11), (5,130,1,142,2,44),
              (5,130,1,145,2,7)]
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder,'reads.jsonl')
            with log.open('w') as output:
                for a,b,u,p,i,v in rows:
                    output.write(json.dumps({'area':a,'block':b,'unit':u,'param':p,
                                             'index':i,'status':'ok','value':v})+'\n')
            result=make_model(log,None)
        refs=result['servo_objects'][0]['sensor_refs']
        self.assertEqual([x['source_index'] for x in refs],[2])
        self.assertIsNone(refs[0]['component'])
        self.assertEqual(refs[0]['encoder'],44)
        self.assertEqual(refs[0]['mapping_status'],'unresolved')
        self.assertEqual(refs[0]['mapping_reason'],'missing_sensor_reference')

        from topology092.model import make_model
        def servo(unit,name):
            rows=[(5,130,unit,107,0,11)] + [(5,130,unit,199,i,ord(ch))
                  for i,ch in enumerate(name)]
            return rows
        rows=servo(1,'SERVO_3.12:3')+servo(2,'SERVO_3.12:3')
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder,'reads.jsonl')
            with log.open('w') as output:
                for a,b,u,p,i,v in rows:
                    output.write(json.dumps({'area':a,'block':b,'unit':u,'param':p,
                                             'index':i,'status':'ok','value':v})+'\n')
            result=make_model(log,None)
        self.assertEqual(len(result['servo_objects']),2)
        self.assertTrue(all(x['identity_status']=='unresolved' for x in result['servo_objects']))
        self.assertTrue(all(x['mapping_reason']=='duplicate_identity' for x in result['servo_objects']))

    def test_cli_identifies_new_release(self):
        from topology092.__main__ import VERSION
        from topology092 import __version__
        self.assertEqual(VERSION,'0.9.4')
        self.assertEqual(__version__,'0.9.4')

    def test_extended_do_collection_uses_only_bounded_readvar_calls(self):
        from topology092.collect import collect_servo_properties
        class Reader:
            def __init__(self): self.calls=[]
            def servo(self, unit, param, index=0, dtype='u16be'):
                self.calls.append((unit,param,index,dtype))
                return {(121,0):12,(141,0):24,(141,1):26}.get((param,index))
        reader=Reader()
        collect_servo_properties(reader,7)
        self.assertIn((7,105,0,'u16be'),reader.calls)
        self.assertIn((7,922,0,'u16be'),reader.calls)
        self.assertIn((7,125,0,'u16be'),reader.calls)
        self.assertIn((7,9489,0,'raw'),reader.calls)
        self.assertEqual([i for u,p,i,t in reader.calls if p==145],[0,1])
        self.assertLessEqual(len(reader.calls),14)

    def test_existing_read_only_do_parameters_enrich_unassigned_servo(self):
        from topology092.model import make_model
        name='SERVO_3.12:3'
        rows=[(5,128,1,102,0,2), (5,128,1,101,0,1),
              (5,128,1,101,1,3), (5,128,1,107,0,1),
              (5,128,1,107,1,11), (5,130,1,107,0,11),
              (5,130,1,121,0,12), (5,130,1,141,0,24),
              (5,130,1,105,0,1), (5,130,1,125,0,1),
              (5,130,1,145,0,2), (5,130,1,922,0,136)]
        rows += [(5,130,1,199,i,ord(ch)) for i,ch in enumerate(name)]
        with tempfile.TemporaryDirectory() as folder:
            log=Path(folder,'reads.jsonl')
            with log.open('w') as output:
                for a,b,u,p,i,v in rows:
                    output.write(json.dumps({'area':a,'block':b,'unit':u,'param':p,
                                             'index':i,'status':'ok','value':v})+'\n')
                output.write(json.dumps({'area':5,'block':130,'unit':1,'param':9489,
                                         'index':0,'status':'ok','value':'4142'})+'\n')
            result=make_model(log,None)
        servo=result['servo_objects'][0]
        self.assertEqual(servo['do_state'],1)
        self.assertEqual(servo['telegram'],136)
        self.assertEqual(servo['p9489_raw_probe'],'4142')
        self.assertEqual(servo['motor_module_ref'],12)
        self.assertEqual(servo['sensor_refs'][0]['component'],24)
        self.assertEqual(servo['sensor_refs'][0]['state'],2)
        self.assertEqual(servo['sensor_refs'][0]['source_index'],0)


if __name__ == '__main__':
    unittest.main()
