import json
import tempfile
import unittest
from pathlib import Path
from topology092.collect import (Journal,Reader,ConnectionLost,upload_sdb,
                                 check_resume_identity)
from topology092.model import make_model


class MockClient:
    calls=[]
    failures=0
    replies={}
    def __init__(self,host,timeout=8):self.host=host;self.is_connected=False
    def connect(self):self.is_connected=True
    def close(self):self.is_connected=False
    def read(self,area,block,unit,column,index):
        key=(area,block,unit,column,index)
        self.calls.append(key)
        if type(self).failures>0:
            type(self).failures-=1
            raise TimeoutError('timed out')
        return self.replies.get(key,{'status':'item_error','code':0x0a})


class FakeSDB:
    blob=b'pp'+bytes(70)
    mismatch=False
    def connect(self,*args):pass
    def disconnect(self):pass
    def list_blocks_of_type(self,*args):return [22,23,2000]
    def full_upload(self,kind,n):
        return self.blob+(b'changed' if self.mismatch and n==22 else b'')


class ResumeTests(unittest.TestCase):
    def setUp(self):
        MockClient.calls=[]
        MockClient.failures=0
        MockClient.replies={}
        FakeSDB.mismatch=False

    def test_cached_ok_avoids_network_and_errors_remain_retryable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'reads.jsonl')
            def write(status,pid,val=None,dtype='u16be'):
                return {'area':5,'block':128,'unit':1,'param':pid,'index':0,
                        'status':status,'dtype':dtype,'value':val,'raw_hex':'0007' if val==7 else None}
            p.write_text('\n'.join(json.dumps(e) for e in [write('ok',102,7),
                            write('protocol_error',107)])+'\n')
            MockClient.replies[(5,128,1,107,0)]={'status':'ok','raw_hex':'000b'}
            reader=Reader('test',d,interval_ms=0,retries=0,client_factory=MockClient)
            self.assertEqual(reader.cu(1,102),7)
            self.assertEqual(MockClient.calls,[])
            self.assertEqual(reader.cu(1,107),11)
            self.assertEqual(len(MockClient.calls),1)
            reader.close()
            reader2=Reader('test',d,interval_ms=0,retries=0,client_factory=MockClient)
            self.assertEqual(reader2.cu(1,107),11)
            self.assertEqual(len(MockClient.calls),1)
            reader2.close()

    def test_torn_line_recovery_and_valid_unterminated_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'reads.jsonl')
            e={'area':5,'block':128,'unit':1,'param':102,'index':0,
               'status':'ok','value':7,'dtype':'u16be'}
            p.write_text(json.dumps(e)+'\n'+ '{"status":')
            j=Journal(d)
            self.assertTrue(j.truncated_tail)
            self.assertEqual(len(j.good),1)
            self.assertTrue((Path(d)/'truncated_last_line.bin').exists())
            j.append({**e,'param':107,'value':11})
            j.close()
            self.assertEqual(len(p.read_text().splitlines()),2)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'reads.jsonl')
            p.write_text(json.dumps(e))
            j=Journal(d)
            j.append({**e,'param':107})
            j.close()
            self.assertEqual(len(p.read_text().splitlines()),2)

    def test_bounded_transport_errors_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            MockClient.failures=20
            r=Reader('test',d,interval_ms=0,retries=1,
                     max_consecutive_errors=2,reconnect_pause=0,
                     client_factory=MockClient)
            self.assertIsNone(r.cu(1,102))
            with self.assertRaises(ConnectionLost):r.cu(1,107)
            self.assertEqual(len(MockClient.calls),4)
            r.close()
            r=Reader('test',d,interval_ms=0,retries=0,client_factory=MockClient)
            MockClient.failures=0
            MockClient.replies[(5,128,1,102,0)]={'status':'ok','raw_hex':'0003'}
            self.assertEqual(r.cu(1,102),3)
            r.close()

    def test_sdb_resume_checks_hash_before_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            upload_sdb('test',d,resume=False,client_factory=FakeSDB,delay_s=0)
            original=(Path(d)/'SDB00022.full.bin').read_bytes()
            self.assertTrue(upload_sdb('test',d,resume=True,client_factory=FakeSDB,
                                       delay_s=0)['resume_validated'])
            FakeSDB.mismatch=True
            with self.assertRaisesRegex(RuntimeError,'changed'):
                upload_sdb('test',d,resume=True,client_factory=FakeSDB,delay_s=0)
            self.assertEqual((Path(d)/'SDB00022.full.bin').read_bytes(),original)

    def test_resume_detects_changed_machine_address(self):
        with tempfile.TemporaryDirectory() as d:
            e={'area':0,'block':26,'unit':1,'param':13120,'index':0,
               'status':'ok','value':6500,'dtype':'u32le'}
            (Path(d)/'reads.jsonl').write_text(json.dumps(e)+'\n')
            MockClient.replies[(0,26,1,13120,0)]={'status':'ok','raw_hex':'65190000'}
            r=Reader('test',d,interval_ms=0,client_factory=MockClient)
            with self.assertRaisesRegex(RuntimeError,'changed'):
                check_resume_identity(r)
            r.close()

    def test_partial_topology_no_sdb(self):
        with tempfile.TemporaryDirectory() as d:
            reads=Path(d)/'reads.jsonl'
            reads.write_text(json.dumps({'area':5,'block':128,'unit':1,'param':102,
                                         'index':0,'status':'ok','value':2})+'\n')
            doc=make_model(reads,None)
            self.assertEqual(doc['summary']['cu_count'],1)
            self.assertFalse(doc['summary']['hwdata_available'])
            self.assertFalse(doc['summary']['topology_all_tlv_complete'])

if __name__=='__main__':unittest.main()

class ArrayIntegrityTests(unittest.TestCase):
    def test_invalidated_array_not_reused_or_inferred_as_full(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'reads.jsonl')
            entries=[
                {'kind':'read','area':5,'block':128,'unit':1,'param':102,'index':0,
                 'dtype':'u16be','status':'ok','value':1},
                {'kind':'read','area':5,'block':128,'unit':1,'param':9900,'index':0,
                 'dtype':'u16be','status':'ok','value':2},
                {'kind':'read','area':5,'block':128,'unit':1,'param':9901,'index':0,
                 'dtype':'u16be','status':'ok','value':0x0701},
                {'kind':'read','area':5,'block':128,'unit':1,'param':9901,'index':1,
                 'dtype':'u16be','status':'ok','value':1},
                {'kind':'array_invalid','cu':1,'param':9901},
            ]
            p.write_text(''.join(json.dumps(e)+'\n' for e in entries))
            doc=make_model(p,None)
            self.assertFalse(doc['summary']['topology_all_tlv_complete'])
            self.assertEqual(doc['summary']['physical_actual_edges'],0)
            j=Journal(d)
            self.assertIn((1,9901),j.invalid_arrays)
            self.assertNotIn((5,128,1,9901,0),j.good)
            j.close()
