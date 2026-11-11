#!/usr/bin/env python3
"""Statically verify selected PE32 callsites, import thunks and exports.
No Windows program execution or hardware communication. Python standard library.
"""
import argparse, hashlib, struct, json
from pathlib import Path

class PE:
    def __init__(self, f):
        self.path = Path(f)
        self.b = self.path.read_bytes()
        assert self.b[:2] == b'MZ'
        e = struct.unpack_from('<I',self.b,0x3c)[0]
        assert self.b[e:e+4] == b'PE\0\0'
        n = struct.unpack_from('<H',self.b,e+6)[0]
        op = e+24
        assert struct.unpack_from('<H',self.b,op)[0] == 0x10b
        self.base = struct.unpack_from('<I',self.b,op+28)[0]
        self.dd = [(struct.unpack_from('<II',self.b,op+96+8*i)) for i in range(16)]
        sec = op+struct.unpack_from('<H',self.b,e+20)[0]
        self.sections = []
        for i in range(n):
            p = sec+40*i
            vs,va,rawsize,off = struct.unpack_from('<IIII',self.b,p+8)
            self.sections.append((va,max(vs,rawsize),rawsize,off))
    def offset_rva(self, rva):
        for va,vs,rawsize,off in self.sections:
            if va <= rva < va+rawsize:
                return off+rva-va
        if rva<4096:return rva
        raise ValueError(f'RVA outside raw sections: {rva:#x} in {self.path.name}')
    def read_rva(self, rva,n):
        off=self.offset_rva(rva)
        return self.b[off:off+n]
    def read(self, va,n): return self.read_rva(va-self.base,n)
    def u32_rva(self,rva):return struct.unpack('<I',self.read_rva(rva,4))[0]
    def cstr_rva(self,rva):
        off=self.offset_rva(rva)
        return self.b[off:self.b.index(b'\0',off)].decode('cp1252','replace')
    def imports(self):
        rva,size=self.dd[1]
        if not rva:return {}
        m={}
        for i in range(200):
            oft,td,fc,name,ft=struct.unpack('<IIIII',self.read_rva(rva+i*20,20))
            if not (oft or td or fc or name or ft):break
            dll=self.cstr_rva(name)
            for j in range(5000):
                v=self.u32_rva((oft or ft)+j*4)
                if not v:break
                sym = f'ord{v&0xffff}' if v&0x80000000 else self.cstr_rva(v+2)
                m[self.base+ft+j*4]=(dll,sym)
        return m
    def exports(self):
        rva,size=self.dd[0]
        if not rva:return {}
        x=struct.unpack('<IIHHIIIIIII',self.read_rva(rva,40))
        _,_,_,_,name,ordbase,nfunc,nnames,funcs,names,ords=x
        result={}
        for i in range(nnames):
            nm=self.cstr_rva(self.u32_rva(names+4*i))
            oi=struct.unpack('<H',self.read_rva(ords+2*i,2))[0]
            result[nm]=self.base+self.u32_rva(funcs+4*oi)
        return result
    def sha(self):return hashlib.sha256(self.b).hexdigest()


def direct_call(pe,addr,expected):
    op=pe.read(addr,5)
    target=addr+5+struct.unpack_from('<i',op,1)[0]
    assert op[0]==0xe8 and target==expected, (hex(addr),op.hex(),hex(target),hex(expected))
    return f'{addr:#010x} E8 rel32 -> {target:#010x}'

def import_call(pe,addr,dll,sym):
    op=pe.read(addr,6)
    assert op[:2]==b'\xff\x15', (hex(addr),op.hex())
    iat=struct.unpack_from('<I',op,2)[0]
    m=pe.imports()[iat]
    assert m[0].lower()==dll.lower() and m[1]==sym, (hex(addr),hex(iat),m)
    return f'{addr:#010x} FF 15 [{iat:#010x}] => {m[0]}!{m[1]}'

def import_thunk(pe,addr,dll,sym):
    op=pe.read(addr,6)
    assert op[:2]==b'\xff\x25', (hex(addr),op.hex())
    iat=struct.unpack_from('<I',op,2)[0]
    m=pe.imports()[iat]
    assert m[0].lower()==dll.lower() and m[1]==sym, (hex(addr),hex(iat),m)
    return f'{addr:#010x} FF 25 [{iat:#010x}] => {m[0]}!{m[1]}'

def run(bindir):
    p={f: PE(bindir/f) for f in ('ibdrv.exe','sllist.dll','slacx.dll','dctl.ocx')}
    ib,sl,ac,dc=(p[x] for x in p)
    results=[]
    results.append(import_call(ib,0x005f2845,'sllist.dll','sllist_CreateViewVB'))
    results.append(import_call(ib,0x005f2884,'sllist.dll','sllist_Cmd'))
    results.append(direct_call(sl,0x1000f642,0x10019080))
    # Siemens DLL exports C++ decorated names; look up the raw import names and verify semantic suffix.
    for addr,expected_label in ((0x10019080,'GetMapInfo'),(0x10019086,'CreateNskFile')):
        ins=sl.read(addr,6)
        assert ins[:2]==b'\xff\x25'
        iat=struct.unpack_from('<I',ins,2)[0]
        dll,sym=sl.imports()[iat]
        assert dll.lower()=='slacx.dll' and expected_label in sym,(hex(addr),dll,sym)
        results.append(f'{addr:#010x} JMP [{iat:#010x}] => {dll}!{sym}')
    results.append(direct_call(sl,0x1000fd87,0x10019086))
    results.append(direct_call(ac,0x10003359,0x10003517))
    exp=ac.exports()
    for label,expected in (('GetMapInfo',0x10003517),('CreateNskFile',0x1000333c),('ConvAcxDataTyp2Ncdde',0x1000322f)):
        hit=[(n,v) for n,v in exp.items() if label in n]
        assert any(v==expected for n,v in hit),(label,hit)
        results.append(f'{ac.path.name} export {label} -> {expected:#010x}')
    results.append(import_call(dc,0x10009dd1,'USER32.dll','PostMessageA'))
    results.append(import_call(dc,0x10009c3e,'USER32.dll','SendMessageA'))
    results.append(direct_call(dc,0x100060d6,0x10009d95))
    results.append(direct_call(dc,0x100061fc,0x10009d95))
    results.append(direct_call(dc,0x10008349,0x1003ad9c))
    results.append(import_thunk(dc,0x1003ad9c,'USER32.dll','UnpackDDElParam'))
    results.append(import_thunk(dc,0x1003add8,'USER32.dll','PackDDElParam'))
    for address in (0x100060b7,0x100060ce,0x100061dd,0x100061f4):
        op=dc.read(address,5)
        assert op==b'\x68\xe6\x03\x00\x00', (hex(address),op.hex())
        results.append(f'{address:#010x} push 0x3e6 (WM_DDE_REQUEST)')
    assert dc.read(0x10007777,7)==b'\x81\xbd\x30\xff\xff\xff\xe5' # compare WM_DDE_DATA at address 10007777
    return {'sha256':{f:o.sha() for f,o in p.items()},'verified':results}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--bin-dir',type=Path,required=True)
    a.add_argument('--out',type=Path)
    x=a.parse_args()
    r=run(x.bin_dir)
    if x.out: x.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(r,ensure_ascii=False,indent=2))
