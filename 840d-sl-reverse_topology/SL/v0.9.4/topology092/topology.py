"""Conservative decoder of SINAMICS r9901/p9903 TLV words.

A word starts a field: field_id = word >> 8, length = word & 255.
A component begins at field 0x07; group 0x01 is physical DRIVE-CLiQ.
Only reciprocal port references are accepted as physical cables.
"""
from __future__ import annotations
from collections import defaultdict
from .device_types import classify_device


def decode_text(words:list[int]) -> str:
    # First word contains the recorded string byte length.
    if not words:return ''
    bs=b''.join(x.to_bytes(2,'big') for x in words[1:])
    return bs[:min(words[0],len(bs))].decode('latin1',errors='replace').strip('\x00')


def decode_words(words:list[int|None], source:str) -> dict:
    fields=[];offset=0;failures=[]
    while offset<len(words):
        header=words[offset]
        if header is None:
            failures.append({'offset':offset,'error':'missing_field_header'})
            break
        fid,n=header>>8,header&255
        value=words[offset+1:offset+1+n]
        if len(value)!=n:
            failures.append({'offset':offset,'error':'truncated_field','field':fid});break
        fields.append({'id':fid,'values':value,'offset':offset,'valid':all(v is not None for v in value)})
        offset+=n+1
    # Group metadata into records, preserving unknown TLV fields and missing words.
    components=[];current=None;current_group=None;current_port=None
    for field in fields:
        fid=field['id'];v=field['values']
        if fid==7:
            current={'name':decode_text(v) if field['valid'] else '', 'number':None,
                     'type_code':None,'device_class':'UNKNOWN','device_id':'',
                     'ports':{},'groups':{},'source':source,'incomplete':False}
            components.append(current);current_group=None;current_port=None
        if current is None:continue
        if not field['valid']:current['incomplete']=True;continue
        if fid==8 and v:
            current['type_code']=v[0]
            current['device_class']=classify_device(v[0])
        if fid==16 and v:current['number']=v[0]
        elif fid==24 and v:current['device_id']=decode_text(v)
        elif fid==18 and v:current_group=v[0];current_port=None
        elif fid==19 and v:
            # Defines number of interfaces in the current group; paired 21/22 fields follow.
            current_port=-1
        elif fid==21 and v and current_group in (1,2,4,5,8):
            current_port = 0 if current_port is None else current_port+1
            group=current['ports'] if current_group==1 else current['groups'].setdefault(current_group,{})
            group.setdefault(current_port,{})['peer_component']=v[0]
        elif fid==22 and v and current_group in (1,2,4,5,8) and current_port is not None and current_port>=0:
            group=current['ports'] if current_group==1 else current['groups'].setdefault(current_group,{})
            group.setdefault(current_port,{})['peer_port']=v[0]
    return {'source':source,
            'complete_tlv':offset==len(words) and not failures and all(f['valid'] for f in fields),
            'tlv_consumed':offset,'tlv_words':len(words),'field_errors':failures,
            'components':components}


def cables(decoded:dict) -> dict:
    """Find 2-way physical group-1 component links; no invented cross-CU wires."""
    allnodes={}
    for cu,ds in decoded.items():
        for c in ds['components']:
            if c['number'] is not None:allnodes[(int(cu),c['number'])]=c
    edges=[];pending=[];seen=set();relations=[]
    relation_types={2:'OPTION_SLOT',4:'POWER',5:'ANALOG',8:'MECHANICAL'}
    for (cu,num),node in allnodes.items():
        for group,links in node.get('groups',{}).items():
            for ordinal,ref in links.items():
                if ref.get('peer_component') not in (None,0,65535):
                    relations.append({'cu':cu,'from':num,'to':ref['peer_component'],
                                      'group':group,'type':relation_types[group],
                                      'source_ordinal':ordinal,'peer_selector':ref.get('peer_port'),
                                      'status':'REFERENCE_ONLY'})
        for port,link in node['ports'].items():
            target_num=link.get('peer_component')
            if not target_num or target_num==65535:continue
            other=allnodes.get((cu,target_num))
            if other is None:
                pending.append({'cu':cu,'component':num,'port':port,'reason':'missing_peer_component','target':target_num});continue
            matching=[(k,v) for k,v in other['ports'].items() if v.get('peer_component')==num]
            if len(matching)!=1:
                pending.append({'cu':cu,'component':num,'port':port,'reason':'ambiguous_or_missing_reverse',
                                'target':target_num,'matching_count':len(matching)});continue
            other_port,other_link=matching[0]
            if node['incomplete'] or other['incomplete']:
                pending.append({'cu':cu,'component':num,'port':port,
                                'reason':'component_incomplete','target':target_num})
                continue
            if (link.get('peer_port')!=other_port+1 or
                    other_link.get('peer_port')!=port+1):
                pending.append({'cu':cu,'component':num,'port':port,
                                'reason':'selector_mismatch','target':target_num,
                                'peer_selector':link.get('peer_port'),
                                'reverse_selector':other_link.get('peer_port')})
                continue
            k=tuple(sorted(((cu,num,port),(cu,target_num,other_port))))
            if k not in seen:
                seen.add(k)
                edges.append({'cu':cu,'from':num,'from_group_port_ordinal':port,
                              'to':target_num,'to_group_port_ordinal':other_port,
                              'peer_interface_selector':link.get('peer_port'),
                              'reverse_selector':other_link.get('peer_port'),
                              'type':'DRIVE_CLIQ_CABLE','verified':'reciprocal_component_group1'})
    return {'edges':edges,'relations':relations,'unresolved_ports':pending,
            'component_count':len(allnodes)}
