#!/usr/bin/env python3
"""Validate Stage 16.7 final contract package without touching source evidence."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path('/root/PL')
FINAL=ROOT/'stages/stage16_7_final'
SOURCE_ABI=ROOT/'stages/stage16_5/abi/typelib_abi_records.json'
REQUIRED=[FINAL/'MCVAR_CLIENT_CONTRACT.md',FINAL/'MCVAR_COM_ABI.json',FINAL/'CALLBACK_AND_LIFECYCLE.md',FINAL/'CALLBACK_AND_LIFECYCLE.evidence.json',FINAL/'COLLECTOR_INTEGRATION.md',FINAL/'RUNTIME_UNKNOWNS.md',FINAL/'EVIDENCE_LEDGER.json']
BIN={
 'old':(ROOT/'PCU_old/H/mmc2/MCVar.dll','43a5c1991d98b6b6e155233a0114d7ff72bf4dec7edf58d0607da501e7d98712'),
 'new':(ROOT/'PCU_new/C/RECYCLER/S-1-5-21-4025392478-4199590385-3038547483-1005/Dc28/files/F/mmc2/MCVar.dll','5e7d955ebe7cfd52424b04e91471b7408f42bf6cc427e3d94c50bc7f4428c24a')}
def _no_duplicate_pairs(pairs):
 d={}
 for k,v in pairs:
  if k in d: raise ValueError(f'duplicate JSON key: {k}')
  d[k]=v
 return d

def main():
 missing=[str(p) for p in REQUIRED if not p.is_file()]
 assert not missing, f'missing deliverables: {missing}'
 for p in REQUIRED:
  assert p.stat().st_size>0, f'empty deliverable: {p}'
 docs='\n'.join(p.read_text(errors='replace') for p in REQUIRED if p.suffix=='.md').lower()
 for token in ('pcb','pdisp','safearray','ondatachanged','reqid','readvarcyclic','removecyclicvariables','collector','unknown'):
  assert token in docs, f'missing required topic {token}'
 abi=json.loads((FINAL/'MCVAR_COM_ABI.json').read_text(),object_pairs_hook=_no_duplicate_pairs)
 ledger=json.loads((FINAL/'EVIDENCE_LEDGER.json').read_text(),object_pairs_hook=_no_duplicate_pairs)
 ev=json.loads((FINAL/'CALLBACK_AND_LIFECYCLE.evidence.json').read_text(),object_pairs_hook=_no_duplicate_pairs)
 source=json.loads(SOURCE_ABI.read_text(),object_pairs_hook=_no_duplicate_pairs)
 def sigs(record):
  def p_sig(p):
   typ=p.get('type') or p.get('tdesc',{}).get('str')
   return (p['name'],typ,tuple(p['flags']))
  return [(f['name'],f['memid'],f['callconv'],[p_sig(p) for p in f['params']]) for f in record.get('functions',[]) if f['name'] in {'ReadVarAsync','ReadVarCyclic','RemoveCyclicVariables','OnDataChanged'}]
 for key,record in abi['interface_records'].items():
  rev,iface=key.split('.',1)
  assert sigs(record)==sigs(source['records'][rev][iface]), f'TypeLib mismatch: {key}'
 canonical=json.loads((ROOT/'stages/stage16_7/entrypoints/iter2/VTABLE_MAP.json').read_text(),object_pairs_hook=_no_duplicate_pairs)
 canonical_targets={(x['interface'].split('.')[0],x['interface'].split('.')[1],x['method'],x['target_va']) for x in canonical['targets']}
 abi_targets=[]
 for revision,interface_record in abi['interface_records'].items():
  version,iface=revision.split('.',1)
  for fn in interface_record['functions']:
   if 'slot' in fn:
    abi_targets.append((version,iface,fn['name'],fn['target_va']))
 assert abi_targets and all(t in canonical_targets for t in abi_targets), 'ABI/vtable target mismatch'
 assert abi['sources']['binaries']['old']['sha256']==BIN['old'][1]
 assert abi['sources']['binaries']['new']['sha256']==BIN['new'][1]
 for ver,(path,want) in BIN.items():
  got=hashlib.sha256(path.read_bytes()).hexdigest(); assert got==want,(ver,got)
 # Run the source-byte vtable verifier; it prints a 12-check JSON result.
 run=subprocess.run([sys.executable,str(ROOT/'stages/stage16_7/entrypoints/iter2/verify_vtables.py')],capture_output=True,text=True,check=True)
 vr=json.loads(run.stdout); assert vr['status']=='PASS' and len(vr['checks'])==12
 result={'status':'PASS_OFFLINE_CONTRACT_PACKAGE_RUNTIME_OPEN','deliverables':[str(p.relative_to(ROOT)) for p in REQUIRED],'valid_json':[str((FINAL/'MCVAR_COM_ABI.json').relative_to(ROOT)),str((FINAL/'EVIDENCE_LEDGER.json').relative_to(ROOT)),str((FINAL/'CALLBACK_AND_LIFECYCLE.evidence.json').relative_to(ROOT))],'input_hashes':{k:v[1] for k,v in BIN.items()},'vtable_checks':len(vr['checks']),'ledger_claims':len(ledger['claims']),'callback_evidence_keys':len(ev)}
 out=FINAL/'verification'/'test_results.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__': main()
