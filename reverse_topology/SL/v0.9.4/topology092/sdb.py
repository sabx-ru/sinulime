"""Decode S7-uploaded HW system data; only module tables, no PLC logic.

SDB2x module descriptor: 14 byte records. Structural markers validated,
never guess a telegram number solely from a size outside known profiles.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import re,hashlib

TELEGRAM_SIZES={(30,38):136,(22,38):116,(10,18):3}


def decode_module_table(raw: bytes, filename: str) -> dict:
    if len(raw)<48 or raw[:2]!=b'pp':
        raise ValueError(f'{filename}: not an S7 SDB module table')
    group=raw[36]
    rows=[]
    for off in range(40,len(raw)-11):
        c=raw[off:off+14]
        # Robust marker checks to avoid interpreting random payload bytes as entries.
        if not (c[0]==0x28 and c[5] in (2,7) and c[6] in (0x83,0x93,0xa3)
                and c[7]==0x40 and c[8] in (0,0xfe) and c[4]<=240):
            continue
        encoded=int.from_bytes(raw[off-2:off],'big')
        rows.append({'offset':off,'bus_id':group,'slave':c[1],
                     'module_index':c[9]*256+c[10],
                     'length':c[4], 'direction':'output' if encoded&0x8000 else 'input',
                     'address':encoded&0x7fff,'raw':(raw[off-2:off]+c[:12]).hex()})
    # Avoid counting coincidental overlap: all selected row ranges must be disjoint.
    prev_end=-1
    for r in rows:
        if r['offset']<prev_end:raise ValueError(f'{filename}: overlapping module records')
        prev_end=r['offset']+14
    return {'name':filename,'bus_id':group,'sha256':hashlib.sha256(raw).hexdigest(),
            'records':rows,'records_count':len(rows)}


def read_sdb_dir(path: str|Path) -> dict:
    root=Path(path)
    files=sorted(root.glob('SDB*.full.bin'))
    if not files:raise ValueError(f'No SDB*.full.bin files in {root}')
    tables=[]; other=[]
    for f in files:
        number=int(re.search(r'SDB(\d+)',f.name).group(1))
        if 20<=number<60:
            try:tables.append(decode_module_table(f.read_bytes(),f.name))
            except ValueError as e:other.append({'file':f.name,'reason':str(e)})
        else:other.append({'file':f.name,'bytes':f.stat().st_size})
    allrows=[r for table in tables for r in table['records']]
    pairs={}
    by_addr=defaultdict(lambda:defaultdict(list))
    for r in allrows:by_addr[(r['bus_id'],r['slave'],r['address'])][r['direction']].append(r)
    for key,dirs in by_addr.items():
        if len(dirs['output'])==1 and len(dirs['input'])==1:
            o=dirs['output'][0];i=dirs['input'][0]
            pairs[key]={'bus_id':key[0],'slave':key[1],'address':key[2],
                        'output_bytes':o['length'],'input_bytes':i['length'],
                        'offset':min(o['offset'],i['offset']),
                        'modules':{'output':o['module_index'],'input':i['module_index']}}
    stations=defaultdict(list)
    for key,p in pairs.items():stations[(p['bus_id'],p['slave'])].append(p)
    slots=[]; service=[]; safety=[]; unclassified=[]
    for st,ps in sorted(stations.items()):
        ordinal=0
        uncertain=False
        for p in sorted(ps,key=lambda x:x['offset']):
            sizes=(p['output_bytes'],p['input_bytes'])
            if sizes in TELEGRAM_SIZES:
                slots.append({**p,'slot':ordinal,'telegram_expected':TELEGRAM_SIZES[sizes],
                              'slot_order_confident':not uncertain})
                ordinal+=1
            elif sizes==(24,24): safety.append(p)
            elif sizes in ((6,14),(4,4),(2,2)):service.append(p)
            else:
                unclassified.append(p)
                uncertain=True
    return {'tables':[{'name':t['name'],'bus_id':t['bus_id'],'sha256':t['sha256'],
                        'records_count':t['records_count']} for t in tables],
            'module_records':len(allrows),'slots':slots,'service':service,
            'safety':safety,'unclassified':unclassified,'other_blocks':other}
