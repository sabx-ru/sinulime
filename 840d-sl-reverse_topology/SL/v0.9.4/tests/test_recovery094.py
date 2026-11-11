"""No-socket test fixtures for bounded retry, recovery and incomplete status."""
import json
from pathlib import Path
import tempfile
import unittest
from topology092.collect import Reader, ConnectionLost, upload_sdb
from topology092.readvar import NckProtocolError

BASE=(0,26,1,13120,0)

class Replay:
    attempts={}
    stable=b'\x64\x19\x00\x00'
    down=False
    fail_once=set()
    def __init__(self,*a,**kw):pass
    def connect(self):pass
    def close(self):pass
    def read(self,area,block,unit,column,index):
        key=(area,block,unit,column,index)
        type(self).attempts[key]=type(self).attempts.get(key,0)+1
        n=type(self).attempts[key]
        if key == BASE:
            if type(self).down and n>1:
                raise TimeoutError('timed out')
            return {'status':'ok','raw_hex':type(self).stable.hex()}
        if key in type(self).fail_once and n==1:
            raise TimeoutError('timed out')
        if key in type(self).fail_once:
            return {'status':'ok','raw_hex':'0005'}
        if column==7777:
            return {'status':'ok','raw_hex':'0009'}
        raise NckProtocolError('Unexpected S7 frame',response=b'\x32\x02'+bytes(10))

class HealthTests(unittest.TestCase):
    def setUp(self):
        Replay.attempts={}; Replay.down=False;Replay.fail_once=set(); Replay.stable=b'\x64\x19\x00\x00'

    def test_transient_item_recovers_on_second_attempt(self):
        Replay.fail_once.add((5,128,1,7777,0))
        with tempfile.TemporaryDirectory() as d:
            r=Reader('fixture',d,interval_ms=0,retries=2,
                     reconnect_pause=0,client_factory=Replay)
            self.assertEqual(r.md(13120,0),6500)
            self.assertEqual(r.cu(1,7777),5)
            self.assertFalse(r.failed_keys)
            self.assertEqual(Replay.attempts[(5,128,1,7777,0)],2)
            r.close()

    def test_health_recovers_after_two_exhausted_addresses(self):
        with tempfile.TemporaryDirectory() as d:
            r=Reader('fixture',d,interval_ms=0,retries=1,
                     max_consecutive_errors=2,reconnect_pause=0,
                     health_retries=2,client_factory=Replay)
            self.assertEqual(r.md(13120,0),6500)
            self.assertIsNone(r.cu(1,9910))
            self.assertIsNone(r.cu(1,9911))
            self.assertEqual(r.health_checks,1)
            self.assertEqual(r.health_recoveries,1)
            self.assertEqual(r.cu(1,7777),9)
            self.assertEqual(len(r.failed_keys),2)
            r.close()
            lines=[json.loads(line) for line in (Path(d)/'reads.jsonl').read_text().splitlines()]
            self.assertTrue(any(e.get('kind')=='health_probe' and e.get('status')=='ok'
                                for e in lines))
            self.assertTrue(any(e.get('response_hex')=='3202'+bytes(10).hex()
                                for e in lines if e.get('kind')=='read'))

    def test_persistent_outage_aborts_only_after_health_retry(self):
        with tempfile.TemporaryDirectory() as d:
            r=Reader('fixture',d,interval_ms=0,retries=1,
                     max_consecutive_errors=2,reconnect_pause=0,
                     health_retries=2,client_factory=Replay)
            self.assertEqual(r.md(13120,0),6500)
            Replay.down=True
            self.assertIsNone(r.cu(1,9910))
            with self.assertRaises(ConnectionLost):r.cu(1,9911)
            self.assertEqual(Replay.attempts[BASE],4)
            r.close()

    def test_health_detects_changed_controller(self):
        with tempfile.TemporaryDirectory() as d:
            r=Reader('fixture',d,interval_ms=0,retries=0,
                     max_consecutive_errors=2,reconnect_pause=0,
                     client_factory=Replay)
            self.assertEqual(r.md(13120,0),6500)
            Replay.stable=b'\x65\x19\x00\x00'
            self.assertIsNone(r.cu(1,9910))
            with self.assertRaisesRegex(RuntimeError,'changed'):r.cu(1,9911)
            r.close()

class FlakySDB:
    enumeration_failures=1
    upload_failures=1
    def connect(self,*a): pass
    def disconnect(self): pass
    def list_blocks_of_type(self,*a):
        if type(self).enumeration_failures:
            type(self).enumeration_failures-=1
            raise TimeoutError('timeout listing')
        return [22]
    def full_upload(self,*a):
        if type(self).upload_failures:
            type(self).upload_failures-=1
            raise TimeoutError('timeout uploading')
        return b'SDB-fixed'

class SDBRecoveryTests(unittest.TestCase):
    def test_reconnect_retries_sdb_listing_and_upload(self):
        FlakySDB.enumeration_failures=1;FlakySDB.upload_failures=1
        with tempfile.TemporaryDirectory() as d:
            res=upload_sdb('fixture',d,delay_s=0,client_factory=FlakySDB)
            self.assertTrue(res['resume_validated'])
            self.assertEqual(res['success'],[22])
            self.assertEqual((Path(d)/'SDB00022.full.bin').read_bytes(),b'SDB-fixed')
            events=[json.loads(line) for line in (Path(d)/'sdb_reads.jsonl').read_text().splitlines()]
            self.assertEqual(len(events),3)
            self.assertEqual(events[-1]['status'],'ok')

if __name__ == '__main__':unittest.main()

class FlakyResumeIdentity:
    attempts=0
    def __init__(self,*a,**kw):pass
    def connect(self):pass
    def close(self):pass
    def read(self,area,block,unit,column,index):
        type(self).attempts+=1
        if type(self).attempts==1:
            raise TimeoutError('timeout once')
        return {'status':'ok','raw_hex':'64190000'}

class ResumeIdentityRetryTests(unittest.TestCase):
    def test_transient_timeout_does_not_abort_resume(self):
        from topology092.collect import check_resume_identity
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'reads.jsonl').write_text(json.dumps({
                'kind':'read','area':0,'block':26,'unit':1,'param':13120,
                'index':0,'dtype':'u32le','status':'ok','value':6500,
                'raw_hex':'64190000'})+'\n')
            FlakyResumeIdentity.attempts=0
            r=Reader('fixture',d,interval_ms=0,retries=0,
                     reconnect_pause=0,client_factory=FlakyResumeIdentity)
            self.assertEqual(check_resume_identity(r),1)
            self.assertEqual(FlakyResumeIdentity.attempts,2)
            r.close()
