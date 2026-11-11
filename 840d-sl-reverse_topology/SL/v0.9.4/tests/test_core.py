"""Self-contained tests of the decoders; no connection to CNC required."""
import unittest, tempfile
from pathlib import Path
from topology092.sdb import decode_module_table,read_sdb_dir
from topology092.topology import decode_words,cables

class Tests(unittest.TestCase):
    def test_sdb_real_style_records(self):
        header=bytearray(50);header[0:2]=b'pp';header[36]=3
        def rec(addr,output,size):
            code=addr|(0x8000 if output else 0)
            return code.to_bytes(2,'big')+bytes([0x28,12,1,0,size,7,0x83,0x40,0xfe,0,3,0])
        data=bytes(header)+rec(5060,False,38)+rec(5060,True,30)+rec(6560,False,4)+rec(6560,True,4)
        with tempfile.TemporaryDirectory() as d:
            Path(d,'SDB00023.full.bin').write_bytes(data)
            got=read_sdb_dir(d)
        self.assertEqual(len(got['slots']),1)
        self.assertEqual(got['slots'][0]['address'],5060)
        self.assertEqual(got['slots'][0]['telegram_expected'],136)
        self.assertEqual(len(got['service']),1)
        self.assertEqual(got['service'][0]['slave'],12)
    def test_tlv_recursion(self):
        # Two synthetic components with reciprocal interface-group-1 refs.
        def f(i,*values):return [(i<<8)|len(values),*values]
        def comp(n,t):
            return f(7,1,ord('A')*256)+f(16,n)+f(18,1)+f(19,1)+f(21,t)+f(22,1)
        decoded=decode_words(comp(1,2)+comp(2,1),'synthetic')
        self.assertTrue(decoded['complete_tlv'])
        g=cables({1:decoded})
        self.assertEqual(len(g['edges']),1)
        self.assertEqual(len(g['unresolved_ports']),0)
    def test_bad_topo_header(self):
        d=decode_words([None,5],'incomplete')
        self.assertFalse(d['complete_tlv'])

if __name__=='__main__':unittest.main()
