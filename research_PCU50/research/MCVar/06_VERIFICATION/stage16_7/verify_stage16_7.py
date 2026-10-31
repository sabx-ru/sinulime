#!/usr/bin/env python3
"""Evidence verifier for Stage 16.7. No runtime or symbolic claims are made."""
from __future__ import annotations
import argparse
import hashlib, json, struct
from pathlib import Path

ROOT = Path('/root/PL')
STAGE = ROOT / 'stages/stage16_7'
BIN = {
 'old': ROOT/'PCU_old/H/mmc2/MCVar.dll',
 'new': ROOT/'PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll',
}
EXPECTED = {
 'old':'43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712',
 'new':'5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a',
}
ENTRY = {
 'old': (0x1000d28a, '85c059744f8b4df08bd3c1e204f7d98d941588b1ffff8d75b41bc923ca51'),
 'new': (0x1000d39c, '85c059744f8b4df08bd3c1e204f7d98d941588b1ffff8d75b41bc923ca51'),
}
CALLS = {
 'old': [(0x1000d2d5, 0x1000d7a4), (0x100134ab, None)],
 'new': [(0x1000d3e7, 0x1000d8b6), (0x100134ab, 0x100139c2)],
}

def u32(b, off): return struct.unpack_from('<I', b, off)[0]
def i32(b, off): return struct.unpack_from('<i', b, off)[0]

def pe_layout(data):
    assert data[:2] == b'MZ'
    pe = u32(data, 0x3c); assert data[pe:pe+4] == b'PE\0\0'
    fh = pe + 4; n = struct.unpack_from('<H', data, fh+2)[0]
    opt = fh + 20; magic = struct.unpack_from('<H', data, opt)[0]
    image = u32(data, opt+28)
    sec = opt + (224 if magic == 0x10b else 240)
    sections=[]
    for i in range(n):
        o=sec+i*40; name=data[o:o+8].rstrip(b'\0').decode('ascii','replace')
        vs, va, rawsz, raw = struct.unpack_from('<IIII', data, o+8)
        sections.append((name,va,max(vs,rawsz),raw,rawsz))
    return image, sections

def va_off(data, va):
    image, sections=pe_layout(data); rva=va-image
    for _,va0,size,raw,rawsz in sections:
        if va0 <= rva < va0+size:
            off=raw+(rva-va0)
            if off < len(data): return off
    raise ValueError(f'VA {va:#x} does not map to a section')

def direct_target(data, callva):
    off=va_off(data,callva)
    if data[off] != 0xE8: raise ValueError(f'{callva:#x}: expected E8, got {data[off]:02x}')
    return callva+5+i32(data,off+1)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, help='optional path for machine-readable results; default is stdout only')
    args=parser.parse_args()
    result={'status':'PASS','checks':[]}
    for ver,p in BIN.items():
        data=p.read_bytes(); digest=hashlib.sha256(data).hexdigest()
        assert digest == EXPECTED[ver], (ver,digest)
        result['checks'].append({'check':'sha256','version':ver,'status':'PASS','sha256':digest})
        image, sections=pe_layout(data); assert image == 0x10000000
        result['checks'].append({'check':'image_base','version':ver,'status':'PASS','value':hex(image)})
        va, hx=ENTRY[ver]; got=data[va_off(data,va):va_off(data,va)+len(bytes.fromhex(hx))].hex()
        assert got == hx, (ver,va,got,hx)
        result['checks'].append({'check':'entry_bytes','version':ver,'status':'PASS','va':hex(va),'bytes':got})
        for callva,want in CALLS[ver]:
            if want is None: continue
            got=direct_target(data,callva); assert got==want,(ver,hex(callva),hex(got),hex(want))
            result['checks'].append({'check':'direct_call','version':ver,'call_va':hex(callva),'target_va':hex(got),'status':'PASS'})
    graph=json.loads((STAGE/'callbacks/CALLBACK_DISPATCH_GRAPH.json').read_text())
    ids={n['id'] for n in graph['nodes']}; assert len(ids)==len(graph['nodes'])
    bad=[e['id'] for e in graph['edges'] if e.get('from') not in ids or e.get('to') not in ids]
    assert not bad, bad
    result['checks'].append({'check':'callback_graph_closure','status':'PASS','nodes':len(ids),'edges':len(graph['edges'])})
    result['status']='PASS'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == '__main__': main()
