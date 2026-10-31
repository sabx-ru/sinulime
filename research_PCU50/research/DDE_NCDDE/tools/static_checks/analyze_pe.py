#!/usr/bin/env python3
"""Offline PE/x86 evidence extractor for PCU_old MCVar.dll and ncdde.exe.
Uses pefile for PE structure, Rizin/objdump as independent disassembly backends.
No execution of vendor binaries and no writes below the source tree.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, re, shutil, struct, subprocess
from pathlib import Path
import pefile

ROOT=Path('/root/PL')
MARKERS=[b'ACDbe', b'ncddeBINARY', b'NCDDE_STARTCMD', b'_FROM_NC_BINARY', b'_TO_NC_BINARY']
DDE_NAMES={'DdeInitialize','DdeCreateStringHandle','DdeConnect','DdeClientTransaction','DdeCreateDataHandle','DdeAccessData','DdeGetData','DdeAddData','DdePostAdvise','DdeEnableCallback','DdeQueryConvInfo','DdeGetLastError','DdeAbandonTransaction','DdeDisconnect','DdeFreeDataHandle','DdeUninitialize','DdeFreeStringHandle'}

def run(cmd):
    try:return subprocess.run(cmd,capture_output=True,text=True,timeout=180).stdout
    except Exception as e:return f'ERROR {e}'
def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def pe_info(p):
    pe=pefile.PE(str(p), fast_load=False); base=pe.OPTIONAL_HEADER.ImageBase
    secs=[]
    for s in pe.sections:
        secs.append({'name':s.Name.rstrip(b'\\0').decode('ascii','replace'),'rva':hex(s.VirtualAddress),'va':hex(base+s.VirtualAddress),'raw_offset':hex(s.PointerToRawData),'raw_size':s.SizeOfRawData,'virtual_size':s.Misc_VirtualSize,'characteristics':hex(s.Characteristics)})
    syms=[]
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
      for x in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        syms.append({'name':(x.name or b'').decode('ascii','replace'),'rva':hex(x.address),'va':hex(base+x.address)})
    imports=[]
    if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
      for d in pe.DIRECTORY_ENTRY_IMPORT:
       for x in d.imports:
        n=(x.name or b'').decode('ascii','replace'); imports.append({'dll':d.dll.decode('ascii','replace'),'name':n,'iat':hex(x.address),'is_dde':n in DDE_NAMES})
    return pe,{'path':str(p),'size':p.stat().st_size,'sha256':sha(p),'image_base':hex(base),'entrypoint_rva':hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'machine':hex(pe.FILE_HEADER.Machine),'sections':secs,'exports':syms,'imports':imports}
def marker_xrefs(p,pe,info):
    data=p.read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase; out=[]
    wanted=[]
    for m in MARKERS:
      start=0
      while (i:=data.find(m,start))>=0: wanted.append((i,m.decode('ascii','replace'))); start=i+1
    # Find raw bytes for each marker and all references to their VA in mapped bytes.
    for raw,name in wanted:
      rva=None
      for s in pe.sections:
       a=s.PointerToRawData;b=a+s.SizeOfRawData
       if a<=raw<b:rva=s.VirtualAddress+(raw-a);break
      rec={'marker':name,'raw_offset':hex(raw),'rva':hex(rva) if rva is not None else None,'va':hex(base+rva) if rva is not None else None,'references':[]}
      if rva is not None:
       for needle,label in [(struct.pack('<I',base+rva),'va'),(struct.pack('<I',rva),'rva')]:
        pos=0
        while (q:=data.find(needle,pos))>=0:
         if q!=raw: rec['references'].append({'raw_offset':hex(q),'kind':label})
         pos=q+1
      out.append(rec)
    return out
def disassembly(p):
    # objdump is independent from Rizin. Limit output to machine code sections via full binary.
    return {'objdump':run(['objdump','-d','-M','intel',str(p)]), 'rizin':run(['rizin','-q','-c','aaa; pdr 500 @ entry0',str(p)])}
def candidate_lines(obj):
    lines=obj['objdump'].splitlines(); hits=[]
    # Restrict to actual x86 memory operands whose displacement is exactly +0x06.
    ins=re.compile(r'^\s*([0-9a-f]+):\s+[0-9a-f ]+\s+(.+)$',re.I)
    for i,l in enumerate(lines):
      m=ins.match(l)
      if not m: continue
      asm=m.group(2).lower()
      # Destination operand is before the first comma; this identifies writes conservatively.
      dst=asm.split(',',1)[0]
      if re.search(r'\[[^]]+\+0x0?6\]',dst) or re.search(r'\[[^]]+\+6\]',dst):
       hits.append({'line':i+1,'va':'0x'+m.group(1),'asm':m.group(2),'kind':'write_destination','context':lines[max(0,i-3):i+4]})
    return hits
def call_edges(obj,base):
    edges=[]; pat=re.compile(r'^\s*([0-9a-f]+):.*\bcall\s+(?:[0-9a-f]+\s+)?0x?([0-9a-f]+)',re.I)
    for l in obj['objdump'].splitlines():
      m=pat.match(l)
      if m: edges.append({'caller_va':hex(int(m.group(1),16)),'target':hex(int(m.group(2),16)),'kind':'direct_call'})
    return edges
def captures():
    t=ROOT/'research/metadata/packet_evidence.tsv'; rows=[]
    if not t.exists(): return rows
    with t.open(errors='replace') as f:
      for r in csv.DictReader(f,delimiter='\t'):
       if r.get('marker')=='4143446265': rows.append({k:r.get(k) for k in ['path','size','f02','f04','f06','count','esize','marker','payload','dim_match']})
    return rows

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--root',default=str(ROOT)); a=ap.parse_args(); out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 bins=[ROOT/'PCU_old/H/mmc2/MCVar.dll',ROOT/'PCU_old/H/mmc2/ncdde.exe']; report={'tool_versions':{'rizin':run(['rizin','-v']).strip(),'objdump':run(['objdump','--version']).splitlines()[0]},'binaries':{},'capture_analysis':captures()}
 for p in bins:
  pe,info=pe_info(p); info['marker_xrefs']=marker_xrefs(p,pe,info); d=disassembly(p); info['candidate_plus_06']=candidate_lines(d); info['call_edges']=call_edges(d,pe.OPTIONAL_HEADER.ImageBase); info['rizin_strings']=run(['rz-bin','-z',str(p)]); info['rizin_imports']=run(['rz-bin','-i',str(p)]); report['binaries'][p.name]=info
  (out/(p.name+'.objdump.txt')).write_text(d['objdump']); (out/(p.name+'.rizin.txt')).write_text(d['rizin']); (out/(p.name+'.imports.txt')).write_text(info['rizin_imports']); (out/(p.name+'.strings.txt')).write_text(info['rizin_strings'])
 # DOT combines direct calls and evidence nodes; no claim that indirect edges are resolved.
 dot=['digraph offline_analysis {','  rankdir=LR;','  node [shape=box,fontname=" monospace"];']
 for n,bi in report['binaries'].items():
  root=n.replace('.','_'); dot.append(f'  {root} [label="{n}\\nbase {bi["image_base"]}",shape=folder];')
  for x in bi['imports']:
   if x['is_dde']:
    q=f'{root}_{x["name"]}'.replace('-','_');dot.append(f'  {q} [label="{x["name"]}\\nIAT {x["iat"]}",shape=ellipse];')
  for e in bi['call_edges'][:1000]: dot.append(f'  {root} -> {root}_call_{e["caller_va"]}_{e["target"]} [label="call {e["caller_va"]} -> {e["target"]}"];')
  for i,x in enumerate(bi['candidate_plus_06']): dot.append(f'  {root}_plus06_{i} [label="+0x06 candidate line {x["line"]}",color=red]; {root} -> {root}_plus06_{i};')
 dot.append('}')
 (out/'analysis.dot').write_text('\n'.join(dot)+'\n'); (out/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'out':str(out),'binaries':list(report['binaries']),'capture_rows':len(report['capture_analysis']),'dot':str(out/'analysis.dot'),'json':str(out/'analysis.json')},indent=2))
if __name__=='__main__':main()
