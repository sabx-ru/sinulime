#!/usr/bin/env python3
"""Stage16.6 evidence checks against the preserved PE and TypeLib JSON."""
import hashlib, json
from pathlib import Path
import pefile

ROOT=Path('/root/PL')
OLD=ROOT/'PCU_old/H/mmc2/MCVar.dll'
NEW=ROOT/'PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll'
TYPELIB=ROOT/'stages/stage16/reports/typelib_decode.json'
TARGETS=('IVar','IVar2','IReadVarAsyncCallback','IReadVarAsyncCallback2','IWriteVarAsyncCallback','IWriteVarAsyncCallback2','IMCCommand','IMCCommandAsyncCallback')
EXPECTED={
 'old':'43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712',
 'new':'5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a'}
ENTRY={'old':(OLD,0xd28a),'new':(NEW,0xd39c)}
EXPECTED_ENTRY=bytes.fromhex('85c059744f8b4df08bd3c1e204f7d98d941588b1ffff8d75b41bc923ca51')

def run():
    results={}
    for tag,path in [('old',OLD),('new',NEW)]:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==EXPECTED[tag], (tag,digest)
        pe=pefile.PE(str(path))
        rva=ENTRY[tag][1]
        off=pe.get_offset_from_rva(rva)
        got=pe.__data__[off:off+len(EXPECTED_ENTRY)]
        assert got==EXPECTED_ENTRY, (tag,got.hex())
        results[tag]={'sha256':digest,'image_base':hex(pe.OPTIONAL_HEADER.ImageBase),'entry_rva':hex(rva),'entry_file_offset':hex(off),'entry_bytes':got.hex()}
    decoded=json.loads(TYPELIB.read_text())
    per_side={}
    for side in ('old','new'):
        infos={t['name']:t for t in decoded[side]['library']['typeinfos']}
        per_side[side]={n:len(infos[n]['funcs']) for n in TARGETS}
    assert per_side['old']==per_side['new']
    assert sum(per_side['old'].values())==32
    all_direct={s:sum(len(t['funcs']) for t in decoded[s]['library']['typeinfos']) for s in ('old','new')}
    assert all_direct=={'old':92,'new':92}
    results['typelib']={'target_direct_function_records':per_side,'target_total_direct_records':32,'all_typeinfo_direct_function_records':all_direct,'inheritance_expansion':False}
    return results

if __name__=='__main__':
    print(json.dumps(run(),indent=2,sort_keys=True))
