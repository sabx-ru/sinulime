#!/usr/bin/env python3
"""Portable offline integrity/ABI checks. Does not assert Siemens runtime behavior."""
import argparse,csv,hashlib,json,subprocess,sys,os
from pathlib import Path
BASE=Path(__file__).resolve().parents[3]  # research/MCVar -> project root
MCVAR=BASE/'research'/'MCVar'

def sha(data): return hashlib.sha256(data).hexdigest()
def check(flag,msg):
    if not flag: raise AssertionError(msg)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--old-dll',type=Path);ap.add_argument('--new-dll',type=Path);ap.add_argument('--skip-unit-tests',action='store_true');args=ap.parse_args()
    p=MCVAR/'00_OVERVIEW'/'FILE_MAP.csv'
    rows=list(csv.DictReader(p.open(encoding='utf-8',newline='')))
    check(rows,'empty provenance manifest')
    for row in rows:
        rel=Path(row['location']);check(not rel.is_absolute() and '..' not in rel.parts,'unsafe manifest path: '+str(rel))
        b=(BASE/rel).read_bytes()
        check(len(b)==int(row['size']),'size mismatch: '+str(rel))
        check(sha(b)==row['sha256'],'SHA mismatch: '+str(rel))
    valid_json=0
    for f in MCVAR.rglob('*.json'):
        if f.name=='VERIFICATION_RESULT.json': continue
        json.loads(f.read_text(encoding='utf-8'));valid_json+=1
    expected={'old':'0653a34a342fc6b80e9f675ff9754173b878a353744098e6eb0c9fa429c77bb3','new':'a7d9968596b9e9a17dff6fc2fcf4a2e2ddc65cedd28dba76eb77791b49dadfd1'}
    for version,digest in expected.items():
        f=MCVAR/'02_TYPELIB'/'resources'/f'{version}_TYPELIB_1_1033.bin'
        b=f.read_bytes();check(len(b)==19732 and sha(b)==digest,'TypeLib resource mismatch: '+version)
    decoded=json.loads((MCVAR/'02_TYPELIB'/'decoded'/'typelib_decode.json').read_text())
    for version in ('old','new'):
        infos=decoded[version]['library']['typeinfos']
        check(len(infos)==28,'TypeInfo count mismatch '+version)
        check(sum(len(x['funcs']) for x in infos)==92,'TypeInfo direct function count mismatch '+version)
    recs=json.loads((MCVAR/'02_TYPELIB'/'abi'/'typelib_abi_records.json').read_text())['records']
    abi=json.loads((MCVAR/'01_CLIENT_CONTRACT'/'MCVAR_COM_ABI.json').read_text())
    target_names={'ReadVarAsync','ReadVarCyclic','RemoveCyclicVariables','OnDataChanged'}
    for rev in ('old','new'):
        check(sum(len(v['functions']) for v in recs[rev].values())==32,'target method count '+rev)
        for iface in ('IVar','IVar2','IReadVarAsyncCallback','IReadVarAsyncCallback2'):
            a=abi['interface_records'][rev+'.'+iface]['functions']; b=recs[rev][iface]['functions']
            b=[f for f in b if f['name'] in target_names]
            check(len(a)==len(b),'signature count mismatch '+rev+iface)
            for fa,fb in zip(a,b):
                check((fa['name'],fa['memid'],fa['callconv'])==(fb['name'],fb['memid'],fb['callconv']),'method mismatch '+rev+iface)
                asig=[(p['name'],p.get('type'),p['flags']) for p in fa['params']]
                bsig=[(p['name'],p['tdesc']['str'],p['flags']) for p in fb['params']]
                check(asig==bsig,'parameter mismatch '+rev+iface+'.'+fa['name'])
    vt=json.loads((MCVAR/'03_REVERSE_ENGINEERING'/'entrypoints'/'iter2'/'VTABLE_MAP.json').read_text())
    vchecks=json.loads((MCVAR/'03_REVERSE_ENGINEERING'/'entrypoints'/'iter2'/'vtable_verification.json').read_text())
    check(vchecks['status']=='PASS' and len(vchecks['checks'])==12,'recorded vtable verification not 12 pass')
    check(len(vt['targets'])==12,'canonical vtable target number mismatch')
    for ent in vchecks['checks']:
        check(any(t['interface']==ent['version']+'.'+ent['interface'] and t['target_va']==ent['target_va'] and t['slot']==ent['slot'] for t in vt['targets']),'vtable mapping contradicts saved checks')
    examined={}
    for version,requested,expected_hash in (('old',args.old_dll,'43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712'),('new',args.new_dll,'5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a')):
        if requested is not None:
            check(sha(requested.read_bytes())==expected_hash,version+' Siemens DLL hash mismatch')
            examined[version]='SHA_MATCH (vtable byte check requires original pefile verifier)'
        else:examined[version]='NOT_SUPPLIED'
    unit='SKIPPED'
    if not args.skip_unit_tests:
        proto=MCVAR/'05_COLLECTOR_FOUNDATION'
        env=os.environ.copy();env['PYTHONPATH']=str(proto/'prototype')
        proc=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=proto,env=env,text=True,capture_output=True)
        check(proc.returncode==0,'collector offline unit tests failed: '+proc.stdout+proc.stderr)
        check('Ran 9 tests' in proc.stderr,'not all 9 offline collector tests executed')
        unit='9/9 PASS (mock-only)'
    print(json.dumps({'status':'PASS_OFFLINE_ARCHIVE_INTEGRITY','files_with_provenance':len(rows),'json_parsed':valid_json,'typelib_resources':'old+new exact SHA','decoded_typeinfo_per_version':28,'direct_functions_per_version':92,'target_typeinfo_direct_functions_per_version':32,'saved_vtable_checks':'12 recorded PASS; original binaries not embedded','collector_unit_tests':unit,'original_dll_sha256':examined,'runtime_PCUs_tested_in_this_archive':False},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
