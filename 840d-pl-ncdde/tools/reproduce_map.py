#!/usr/bin/env python3
"""Offline reconstruction of Siemens slacx NcMap table and archived NSK descriptors.
No Siemens binaries are executed; no communication with NCU/PLC/drive occurs.
Python 3 stdlib only.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, json, re, struct

class PE:
    def __init__(self,path):
        self.path=Path(path)
        self.raw=self.path.read_bytes()
        if self.raw[:2]!=b'MZ': raise ValueError(f'Not PE: {path}')
        pe=struct.unpack_from('<I',self.raw,0x3c)[0]
        if self.raw[pe:pe+4]!=b'PE\0\0': raise ValueError(f'Not PE signature: {path}')
        ns=struct.unpack_from('<H',self.raw,pe+6)[0]
        opt_size=struct.unpack_from('<H',self.raw,pe+20)[0]
        opt=pe+24
        if struct.unpack_from('<H',self.raw,opt)[0]!=0x10b:raise ValueError('PE32 required')
        self.imagebase=struct.unpack_from('<I',self.raw,opt+28)[0]
        self.sections=[]
        sec=opt+opt_size
        for i in range(ns):
            o=sec+40*i
            name=self.raw[o:o+8].split(b'\0')[0].decode('ascii','replace')
            vs,va,sz,rawptr=struct.unpack_from('<IIII',self.raw,o+8)
            self.sections.append((name,va,max(vs,sz),rawptr,sz))
    def offset(self,va):
        rva=va-self.imagebase
        for name,srva,ssize,raw,rawsize in self.sections:
            if srva<=rva<srva+min(ssize,rawsize):return raw+rva-srva
        raise ValueError(f'No raw section for {va:#x}')
    def read(self,va,n):
        o=self.offset(va)
        return self.raw[o:o+n]
    def u32(self,va):return struct.unpack('<I',self.read(va,4))[0]
    def cstr(self,va):
        o=self.offset(va)
        return self.raw[o:self.raw.index(b'\0',o)].decode('cp1252','replace')
    @property
    def sha(self):return hashlib.sha256(self.raw).hexdigest()

PAT=re.compile(r'^LINK\((/acc/(nc|ch|ax)_tea/[^,]+),200,"([0-9]+) 1 ([0-9]+) 1 ([0-9A-F]+)# /NC (-?[0-9]+) ([0-9]+) 11",([0-9]+)\)$')

def save_tsv(path,header,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f,delimiter='\t'); w.writerow(header);w.writerows(rows)

def run(a):
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pe=PE(a.slacx)
    items=[]
    # The 22 static entries span 0x10030500..0x1003065F. Next entry is vtable.
    for i in range(22):
        va=0x10030500+16*i
        view,area,fmtid,s=struct.unpack('<IIII',pe.read(va,16))
        items.append((i,hex(va),view,area,fmtid,pe.cstr(s)))
    save_tsv(out/'slacx_ncmap_table.tsv',('row','VA','sllist_view','slacx_area','descriptor_hex_id','link_prefix'),items)
    mapdict={(v,a):(f,p) for _,_,v,a,f,p in items}
    expect={'nc':(1,0),'ch':(1,2),'ax':(1,3)}
    nsk=Path(a.nsk_dir)
    records=[]; errors=[]; keys={}; totals={}
    for group,(view,area) in expect.items():
        path=nsk/f'{group}_tea.nsk'
        if not path.exists(): errors.append(f'File not found: {path}');continue
        lines=path.read_text('cp1252',errors='replace').splitlines()
        fmt,pre=mapdict[(view,area)]
        n=0
        for lineno,line in enumerate(lines,1):
            m=PAT.fullmatch(line)
            if not m:
                errors.append(f'{path.name}:{lineno} unmatched syntax: {line[:120]}');continue
            link,grp,storedarea,md,storedfmt,mdtype,index,ret=m.groups()
            okay=(grp==group and link.startswith(pre) and int(storedarea)==area and int(storedfmt,16)==fmt and int(index)==0 and int(ret)==10)
            if not okay:errors.append(f'{path.name}:{lineno} mismatch in map fields: {line}')
            records.append((path.name,lineno,link,md,mdtype,storedarea,storedfmt,index,ret,'OK' if okay else 'MISMATCH'))
            keys[link.lower()]=(path.name,lineno,line)
            n+=1
        totals[path.name]={'lines':len(lines),'parsed':n,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    save_tsv(out/'mapped_nsk_entries.tsv',('file','line','item','md_number','type','area','format_hex','index','last_arg','map_validation'),records)
    testrows=[]
    if a.sets_dir:
        for file in sorted(Path(a.sets_dir).glob('MD_*.txt')):
            for line in file.read_text('utf-8',errors='replace').splitlines():
                if '|' not in line or line.lstrip().startswith('#'):continue
                label,item=line.strip().split('|',1)
                hit=keys.get(item.lower())
                testrows.append((file.name,label,item,'YES' if hit else 'NO',hit[0] if hit else '',hit[1] if hit else ''))
    save_tsv(out/'test_selectors_vs_generated_nsk.tsv',('set','label','selector','exact_match','nsk_file','nsk_line'),testrows)
    for e in errors:print('ERROR:',e)
    hashes={'slacx.dll':pe.sha}
    for name,p in (('sllist.dll',a.sllist),('ibdrv.exe',a.ibdrv)):
        if p:hashes[name]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
    summary={'binary_hashes':hashes,'static_table_count':len(items),'generated_nsk':totals,'matched_test_selectors':sum(r[3]=='YES' for r in testrows),'total_test_selectors':len(testrows),'errors':errors,'map_prefixes':{f'{v}/{ar}':p for _,_,v,ar,f,p in items}}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    if errors:raise SystemExit(2)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--slacx',required=True)
    p.add_argument('--sllist')
    p.add_argument('--ibdrv')
    p.add_argument('--nsk-dir',required=True)
    p.add_argument('--sets-dir')
    p.add_argument('--out',required=True)
    run(p.parse_args())
