"""Offline evidence fusion: NCK MD -> SDB HW slots -> CU p0978 -> topology.

Never infers CU from sorted addresses or assumes six slots / fixed stride.
Unmatched and conflicting records are explicitly unresolved.
"""
from __future__ import annotations
from collections import defaultdict,Counter
from pathlib import Path
import json,re,csv
from .sdb import read_sdb_dir
from .topology import decode_words,cables

def _same_index(left, right):
    """Compare source indices without Python's bool/int/float aliasing."""
    return type(left) is type(right) and left == right


class LiveIndex:
    def __init__(self, reads_path):
        self.events={};self.observations=defaultdict(list);self.malformed=defaultdict(list)
        self.duplicate_keys=set();self.conflict_keys=set();self.counts=Counter();self.reads_count=0
        self.invalid_arrays=set()
        with Path(reads_path).open(encoding='utf-8') as file:
            lines=file.readlines()
            for line_number,line in enumerate(lines):
                if not line.strip():continue
                try:
                    e=json.loads(line)
                except json.JSONDecodeError:
                    if line_number==len(lines)-1: break
                    raise
                if e.get('kind') in ('array_invalid','array_verified'):
                    cu,param=e['cu'],e['param']
                    if e['kind']=='array_invalid':
                        self.invalid_arrays.add((cu,param))
                        self.events={k:v for k,v in self.events.items() if k[:4]!=(5,128,cu,param)}
                    else:self.invalid_arrays.discard((cu,param))
                    continue
                self.reads_count+=1
                prefix=(e.get('area'),e.get('block'),e.get('unit'),e.get('param'))
                index=e.get('index')
                if e.get('status')=='ok':
                    valid_index=isinstance(index,int) and not isinstance(index,bool) and index >= 0
                    if not valid_index:
                        self.malformed[prefix].append(e)
                        self.counts['malformed_source_index'] += 1
                        continue
                    key=prefix + (index,)
                    self.observations[key].append(e)
                    if key in self.events:
                        self.duplicate_keys.add(key)
                        if self.events[key].get('value') != e.get('value'):
                            self.conflict_keys.add(key)
                    self.events[key]=e
                self.counts[str(e.get('status'))]+=1
    def indices(self, area, block, unit, param):
        return {key[4] for key in self.events if key[:4] == (area, block, unit, param)
                and isinstance(key[4], int) and key[4] >= 0}
    def read(self,area,block,unit,param,index=0):
        e=self.events.get((area,block,unit,param,index))
        return e.get('value') if e else None
    def cu(self,cu,param,index=0):return self.read(5,128,cu,param,index)
    def md(self,param,index=0,area=0,unit=1):return self.read(area,26,unit,param,index)
    def servo(self,unit,param,index=0):return self.read(5,130,unit,param,index)
    def candidates(self,area,block,unit,param,index):
        if not isinstance(index,int) or isinstance(index,bool) or index < 0:
            return [e for e in self.malformed_for(area,block,unit,param)
                    if _same_index(e.get('index'), index)]
        return list(self.observations.get((area,block,unit,param,index), ()))
    def malformed_for(self,area,block,unit,param):
        return list(self.malformed.get((area,block,unit,param), ()))


def words_from_log(r:LiveIndex,cu:int,param:int,count_param:int):
    if (cu,param) in r.invalid_arrays:
        return None
    n=r.cu(cu,count_param)
    if not isinstance(n,int) or not 0<n<65000:return None
    return [r.cu(cu,param,i) for i in range(n)]


def decode_name(raw):
    if not isinstance(raw,str):return None
    try:return bytes.fromhex(raw).split(b'\x00',1)[0].decode('latin1').strip() or None
    except ValueError:return None


def resolve_p978_slot(values, slot):
    """Keep array indices intact; p978 value 1 terminates the DO slot region."""
    if not isinstance(slot,int) or slot<0 or slot>=len(values):
        return None,'OUT_OF_RANGE'
    if any(v is None for v in values[:slot]):
        return None,'PREFIX_UNREADABLE'
    if 1 in values[:slot+1]:
        return None,'END_MARKER'
    number=values[slot]
    if number is None:return None,'UNREADABLE'
    if number in (0,255,65535):return None,'EMPTY_SLOT'
    return number,'OK'


def make_model(reads_path,sdb_path,arrays_path=None):
    r=LiveIndex(reads_path)
    hw=read_sdb_dir(sdb_path) if sdb_path and list(Path(sdb_path).glob('SDB*.full.bin')) else {
        'tables':[],'other_blocks':[],'slots':[],'service':[],'safety':[],
        'module_records':0,'unclassified':[]}

    arr=json.loads(Path(arrays_path).read_text(encoding='utf-8')) if arrays_path else {}
    cu={};act={};target={}
    for number in range(1,17):
        do_count=r.cu(number,102)
        if not isinstance(do_count,int) or not 1<=do_count<=128:continue
        module=[]
        for p in (101,107):
            vals=[r.cu(number,p,i) for i in range(do_count)]
            module.append(vals)
        p978=[r.cu(number,978,i) for i in range(128)]
        address=r.md(13120,number-1)
        # Unavailable values are not zero and are never assigned a guessed slot.
        cu[number]={'cu':number,'service_io':address,'do_count':do_count,
                    'do_numbers':module[0],'do_types':module[1],'p0978':p978}
        for which,container,param,length_param in (("actual",act,9901,9900),("target",target,9903,9902)):
            ref=arr.get(str(number),{}).get(which)
            w=([entry.get('value') for entry in ref['words']]
               if isinstance(ref,dict) and isinstance(ref.get('words'),list)
               else words_from_log(r,number,param,length_param))
            if w is not None:container[number]=decode_words(w,f'CU{number}.{param}')

    cables_actual=cables(act);cables_target=cables(target)
    def edge_ids(graph):
        return {(e['cu'],tuple(sorted(((e['from'],e['from_group_port_ordinal']),
                                      (e['to'],e['to_group_port_ordinal'])))))
                for e in graph['edges']}
    actual_ids=edge_ids(cables_actual)
    target_ids=edge_ids(cables_target)
    actual_complete=bool(cu) and len(act)==len(cu) and all(v['complete_tlv'] for v in act.values())
    target_complete=bool(cu) and len(target)==len(cu) and all(v['complete_tlv'] for v in target.values())
    comparable=(actual_complete and target_complete and
                not cables_actual['unresolved_ports'] and
                not cables_target['unresolved_ports'])

    service_lookup=defaultdict(set)
    for row in hw['service']:
        service_lookup[row['address']].add((row['bus_id'],row['slave']))
    stations={}; station_problems=[]
    for number,record in cu.items():
        candidates=sorted(service_lookup.get(record['service_io'],[]))
        if len(candidates)==1:
            record['bus_id'],record['slave']=candidates[0]
            record['hw_match']='EXACT_SERVICE_IO'
            stations[candidates[0]]=number
        else:
            record['hw_match']='AMBIGUOUS' if candidates else 'NOT_FOUND'
            record['service_candidates']=candidates
            station_problems.append({'cu':number,'service_io':record['service_io'],'candidates':candidates})
    slots_index=defaultdict(list)
    for slot in hw['slots']:slots_index[slot['address']].append(slot)
    axes=[]
    for axis in range(1,65):
        setpoint=r.md(30110,0,area=3,unit=axis)
        active=r.md(30130,0,area=3,unit=axis)
        if setpoint is None and active is None:continue
        name=decode_name(r.md(10000,axis-1))
        entry={'axis_unit':axis,'name':name,'md30130':active,'md30110':setpoint,
               'encoders':[]}
        for channel in (0,1):
            feedback=r.md(30220,channel,area=3,unit=axis)
            encoder=r.md(30230,channel,area=3,unit=axis)
            kind=r.md(30240,channel,area=3,unit=axis)
            if feedback is not None or encoder is not None or kind is not None:
                entry['encoders'].append({'channel':channel,'md30220':feedback,
                                          'md30230':encoder,'md30240':kind})
        if active!=1:
            entry['status']='INACTIVE_OR_UNKNOWN_SETPOINT';axes.append(entry);continue
        if not isinstance(setpoint,int) or setpoint<=0:
            entry['status']='NO_VALID_LOGICAL_DRIVE';axes.append(entry);continue
        io=r.md(13050,setpoint-1)
        telegram=r.md(13060,setpoint-1)
        entry.update({'io_address':io,'md13060':telegram})
        found=slots_index.get(io,[])
        if telegram is not None:found=[s for s in found if s['telegram_expected']==telegram]
        if len(found)!=1:
            entry['status']='NO_UNIQUE_HW_SLOT'
            entry['hw_candidates']=found
            axes.append(entry);continue
        s=found[0]
        entry.update({'bus_id':s['bus_id'],'slave':s['slave'],'slot':s['slot'],
                      'io_input_bytes':s['input_bytes'],'io_output_bytes':s['output_bytes']})
        number=stations.get((s['bus_id'],s['slave']))
        if number is None:
            entry['status']='HW_SLOT_NO_MATCHED_CU';axes.append(entry);continue
        entry['cu']=number
        row=cu[number]['p0978']
        if not s.get('slot_order_confident',True):
            entry['status']='HW_SLOT_ORDER_UNCERTAIN';axes.append(entry);continue
        do, slot_status=resolve_p978_slot(row,s['slot'])
        entry['p0978_status']=slot_status
        if slot_status!='OK':
            entry['status']='HW_SLOT_NO_DO_IN_P0978';axes.append(entry);continue
        entry['do']=do
        dos=cu[number]['do_numbers'];types=cu[number]['do_types']
        if dos.count(do)!=1:
            entry['status']='DO_NOT_UNIQUE_IN_P0101';axes.append(entry);continue
        dtype=types[dos.index(do)]
        entry['do_type']=dtype
        entry['status']='VERIFIED_BY_NCK_SDB_CU' if dtype==11 else 'NON_SERVO_DRIVE_OBJECT'
        axes.append(entry)

    # Servo component references can be assigned if the full readable OEM name
    # explicitly identifies Bus.Slave:DO, never merely by global ordinal.
    servos=[];identified=defaultdict(list)
    for unit in range(1,65):
        typ=r.servo(unit,107)
        if typ is None:continue
        vals=[r.servo(unit,199,i) for i in range(25)]
        text=''.join(chr(v&255) for v in vals if isinstance(v,int) and 0<v<256).split('\x00',1)[0]
        comps={str(p):[r.servo(unit,p,i) for i in range(4)] for p in (121,131,141,142)}
        motor_states=[r.servo(unit,125,i) for i in range(4)]
        sensor_states=[r.servo(unit,145,i) for i in range(4)]
        sensor_indices=[]
        for p in (141,142,145):
            for i in r.indices(5,130,unit,p):
                meaningful=any(r.read(5,130,unit,other,i) not in (None,0,255,65535)
                               for other in (141,142,145))
                if meaningful and i not in sensor_indices:
                    sensor_indices.append(i)
            for e in r.malformed_for(5,130,unit,p):
                i=e.get('index')
                if not any(_same_index(i, existing) for existing in sensor_indices):
                    sensor_indices.append(i)
        sensor_indices.sort(key=lambda value: (not isinstance(value, int), str(value)))
        sensor_refs=[]
        for i in sensor_indices:
            valid_index=isinstance(i, int) and not isinstance(i, bool) and i >= 0
            component=comps['141'][i] if valid_index and i < len(comps['141']) else None
            encoder=comps['142'][i] if valid_index and i < len(comps['142']) else None
            duplicate=any(valid_index and (5,130,unit,p,i) in r.duplicate_keys
                          for p in (141,142,145))
            conflict=any(valid_index and (5,130,unit,p,i) in r.conflict_keys
                         for p in (141,142,145))
            observations=[e for p in (141,142,145)
                          for e in r.candidates(5,130,unit,p,i)]
            if not valid_index:
                mapping_status='unresolved'
                mapping_reason='malformed_source_index'
            elif conflict or duplicate:
                mapping_status='ambiguous_mapping'
                mapping_reason='ambiguous_mapping'
            elif component in (None,0,255,65535):
                mapping_status='unresolved'
                mapping_reason='missing_sensor_reference'
            elif (i >= len(sensor_states) or sensor_states[i] is None or encoder is None):
                mapping_status='unresolved'
                mapping_reason='missing_encoder_or_state'
            else:
                mapping_status='resolved'
                mapping_reason=None
            sensor_refs.append({'component':component if component not in (0,255,65535) else None,
                                'state':sensor_states[i] if valid_index and i < len(sensor_states) else None,
                                'sm_number':i+1 if valid_index else None,'source_index':i,
                                'encoder':encoder if encoder not in (0,255,65535) else None,
                                'encoder_source_index':i,
                                'mapping_status':mapping_status,
                                'observations':observations,
                                **({'mapping_reason':mapping_reason} if mapping_reason else {})})
        motor_module_refs=[{'component':component,'state':motor_states[i],
                            'source_index':i}
                           for i,component in enumerate(comps['121'])
                           if component not in (None,0,255,65535)]
        record={'unit':unit,'type':typ,'name':text,'refs':comps,
                'do_state':r.servo(unit,105),'telegram':r.servo(unit,922),
                'p9489_raw_probe':r.servo(unit,9489),
                'motor_module_refs':motor_module_refs,
                'sensor_refs':sensor_refs}
        if len(motor_module_refs)==1:
            record['motor_module_ref']=motor_module_refs[0]['component']
            record['motor_module_state']=motor_module_refs[0]['state']
        m=re.search(r'(?:SERVO|INFEED)_(\d+)\.(\d+):(\d+)(?:\b|_)',text)
        if m:
            key=tuple(int(z) for z in m.groups())
            record['identity']={'bus_id':key[0],'slave':key[1],'do':key[2]}
            identified[key].append(record)
            record['identity_status']='unresolved'
            record['mapping_reason']='duplicate_identity'
        servos.append(record)
    for a in axes:
        if a.get('status')=='VERIFIED_BY_NCK_SDB_CU':
            matches=identified.get((a['bus_id'],a['slave'],a['do']),[])
            if len(matches)==1:
                ext=matches[0]
                a['servo_unit']=ext['unit'];a['servo_name']=ext['name'];a['component_refs']=ext['refs']
                ext['identity_status']='confirmed'
                ext.pop('mapping_reason',None)
            elif len(matches)>1:
                a['status']='AMBIGUOUS_SERVO_IDENTITY'
                a['mapping_reason']='duplicate_identity'

    # A shared unique CU_LINK identity means the same module is represented
    # in two CU contexts. It is *not* an additional physical cable.
    devices=defaultdict(list)
    for number,contents in act.items():
        for c in contents['components']:
            if c['name'].startswith('CU_LINK') and c['device_id']:
                devices[c['device_id']].append({'cu':number,'component':c['number']})
    cu_links=[{'device_id':name,'representations':locs,
               'verified':len(locs)==2 and len({v['cu'] for v in locs})==2}
              for name,locs in sorted(devices.items())]
    summary={'read_events':r.reads_count,'read_statuses':dict(r.counts),
             'cu_count':len(cu),'sdb_blocks':len(hw['tables'])+len(hw['other_blocks']),
             'hw_slot_count':len(hw['slots']),'hw_stations':[{'bus_id':b,'slave':s} for b,s in sorted(stations)],
             'axes_active':sum(a.get('md30130')==1 for a in axes),
             'axes_verified':sum(a['status']=='VERIFIED_BY_NCK_SDB_CU' for a in axes),
             'physical_actual_edges':len(cables_actual['edges']),
             'physical_target_edges':len(cables_target['edges']),
             'physical_edge_sets_equal':(actual_ids==target_ids) if comparable else None,
             'cu_link_pairs':sum(x['verified'] for x in cu_links),
             'topology_all_tlv_complete':actual_complete,
             'target_all_tlv_complete':target_complete,
             'unresolved_service_mappings':len(station_problems),
             'actual_cu_with_complete_tlv':sum(bool(v['complete_tlv']) for v in act.values()),
             'target_cu_with_complete_tlv':sum(bool(v['complete_tlv']) for v in target.values()),
             'hwdata_available':bool(hw['slots'])}
    return {'schema':'read-only-topology/v0.9.2','summary':summary,'control_units':cu,'axes':axes,
            'hwdata':hw,'topology_actual':act,'topology_target':target,
            'cables_actual':cables_actual,'cables_target':cables_target,
            'cu_links':cu_links,'mapping_problems':station_problems,
            'servo_objects':servos}


def write_results(doc,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    (out/'architecture.json').write_text(json.dumps(doc,indent=2,ensure_ascii=False),encoding='utf-8')
    (out/'summary.json').write_text(json.dumps(doc['summary'],indent=2,ensure_ascii=False),encoding='utf-8')
    with (out/'axis_map.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['axis_unit','name','md30130','md30110','io_address','md13060','bus_id','slave','slot','cu','do','do_type','status']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for a in doc['axes']:w.writerow({k:a.get(k) for k in cols})
    with (out/'physical_edges.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['cu','from','from_group_port_ordinal','to','to_group_port_ordinal','verified']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for e in doc['cables_actual']['edges']:w.writerow({k:e.get(k) for k in cols})
    with (out/'typed_relations.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['cu','from','to','group','type','source_ordinal','peer_selector','status']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for e in doc['cables_actual']['relations']:w.writerow({k:e.get(k) for k in cols})
    with (out/'components.csv').open('w',newline='',encoding='utf-8-sig') as f:
        cols=['cu','number','name','type_code','device_class','device_id','incomplete']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
        for cu,table in doc['topology_actual'].items():
            for c in table['components']:
                w.writerow({'cu':cu,**{k:c.get(k) for k in cols if k!='cu'}})
    write_graphml(doc,out)
    return out


def write_graphml(doc,output):
    """Physical graph only; CU_LINK is same device in two CU contexts, not a cable."""
    import xml.etree.ElementTree as ET
    NS='http://graphml.graphdrawing.org/xmlns'
    ET.register_namespace('',NS)
    root=ET.Element(f'{{{NS}}}graphml')
    for key,attr in [('name','name'),('component','component'),('cu','cu'),('device_id','device_id')]:
        ET.SubElement(root,f'{{{NS}}}key',id=key,attrib={'for':'node','attr.name':attr,'attr.type':'string'})
    graph=ET.SubElement(root,f'{{{NS}}}graph',id='DRIVE_CLIQ',edgedefault='undirected')
    joined={}
    for link in doc['cu_links']:
        if link['verified']:
            for ref in link['representations']:
                joined[(ref['cu'],ref['component'])]='DEVICE:'+link['device_id']
    def nodeid(cu,num):return joined.get((cu,num),f'CU{cu}:C{num}')
    nodes={}
    for cu,table in doc['topology_actual'].items():
        for c in table['components']:
            num=c['number']
            if num is None:continue
            id=nodeid(cu,num)
            if id not in nodes:nodes[id]=(cu,c)
    for id,(cu,c) in nodes.items():
        element=ET.SubElement(graph,f'{{{NS}}}node',id=id)
        for key,value in [('name',c['name']),('component',c['number']),('cu',cu),('device_id',c['device_id'])]:
            ET.SubElement(element,f'{{{NS}}}data',key=key).text=str(value)
    for ix,e in enumerate(doc['cables_actual']['edges']):
        ET.SubElement(graph,f'{{{NS}}}edge',id=f'cable{ix}',
                      source=nodeid(e['cu'],e['from']),target=nodeid(e['cu'],e['to']))
    dest=Path(output)/'DRIVE_CLIQ.graphml'
    ET.ElementTree(root).write(dest,encoding='utf-8',xml_declaration=True)
    return dest
