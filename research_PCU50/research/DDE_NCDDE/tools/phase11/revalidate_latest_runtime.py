#!/usr/bin/env python3
"""Offline, stdlib-only validation of the latest preserved runtime corpus.

Run: python3 research/phase11/SCRIPTS/revalidate_latest_runtime.py
The schema is WORD header length 20, WORD version 1, marker at offset 16.
The superseded DWORD predicate remains an explicit negative control.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import re

MARKER = bytes.fromhex('F9 F8 F7 F6')

def valid_binary(data):
    return len(data) >= 20 and data[:4] == bytes.fromhex('14 00 01 00') and data[16:20] == MARKER

def rejected_dword_predicate(data):
    return len(data) >= 20 and int.from_bytes(data[:4], 'little') == 20 and data[16:20] == MARKER

def observed_word_header(data):
    return len(data) >= 20 and int.from_bytes(data[:2], 'little') == 20 and data[16:20] == MARKER

def stamp(text):
    return datetime.strptime(text[:23], '%Y-%m-%d %H:%M:%S.%f')

def validate(root, runner):
    logs = root / 'real_tests/bin/logs'
    steps = []
    for line_no, line in enumerate(runner.read_text().splitlines(), 1):
        m = re.match(r'START (\d+) (\S+) (\S+) (\d+/\d+/\d+ \S+)', line)
        if m:
            n, kind, name, when = m.groups()
            steps.append(dict(number=int(n), kind=kind, name=name, start=datetime.strptime(when, '%d/%m/%Y %H:%M:%S.%f'), runner_line=line_no))
        m = re.match(r'END (\d+) .* RC=(\d+) status=(\S+) expect=(\S+) (\d+/\d+/\d+ \S+)', line)
        if m:
            n, rc, status, expect, when = m.groups()
            step = next(x for x in steps if x['number'] == int(n))
            step.update(rc=int(rc), status=status, expect=expect, end=datetime.strptime(when, '%d/%m/%Y %H:%M:%S.%f'))
    issues = []
    # Log BEGIN order and runner invocation order are independent matching evidence.
    files = sorted(logs.glob('*.log'), key=lambda p: stamp(p.read_text(errors='replace').splitlines()[0]))
    if len(files) != len(steps):
        issues.append(dict(type='log_step_count', logs=len(files), steps=len(steps)))
    responses, strict, reads, mc_rounds, slots = [], [], [], [], []
    used = set()
    for step, file in zip(steps, files):
        text = file.read_text(errors='replace')
        lines = text.splitlines()
        begin = stamp(lines[0])
        # Runner END has centisecond resolution; allow that final centisecond.
        from datetime import timedelta
        if not step['start'] <= begin <= step['end'] + timedelta(milliseconds=10):
            issues.append(dict(type='log_runner_time', step=step['number'], log=file.name))
        step['log'] = file.name
        step['error_evidence'] = [dict(line=n, text=s) for n,s in enumerate(lines,1) if '[ERROR]' in s or 'DDE_ERROR' in s or ('EXCEPINFO.scode=' in s and 'scode=0x00000000' not in s)]
        if (step['kind'] == 'MC') != file.name.startswith('mcvar_') and step['kind'] != 'META':
            issues.append(dict(type='log_runner_kind', step=step['number']))
        if step['kind'] == 'DDE':
            current = None
            for line_no, line in enumerate(lines, 1):
                m = re.search(r'READ round=(\d+) index=(\d+) format=(\S+) item=(.*?) elapsed_ms=\d+ result=(\S+)', line)
                if m:
                    rnd, index, fmt, item, result = m.groups()
                    current = dict(step=step['number'], name=step['name'], log=file.name, line=line_no, round=int(rnd), index=int(index), format=fmt, item=item, result=result)
                    reads.append(current)
                m = re.search(r'Raw response: .*\\([^\\]+\.bin) \((\d+) bytes\)', line)
                if m:
                    if current is None:
                        issues.append(dict(type='raw_without_read', log=file.name, line=line_no)); continue
                    capture = logs / m[1]
                    data = capture.read_bytes()
                    suffix = f"_r{current['round']:02d}_i{current['index']:02d}_{current['format']}.bin"
                    if not capture.name.endswith(suffix) or current['result'] != 'DATA_HANDLE':
                        issues.append(dict(type='read_capture_association', capture=capture.name, read=current))
                    if capture.name in used:
                        issues.append(dict(type='duplicate_capture', capture=capture.name))
                    used.add(capture.name)
                    current['capture'] = capture.name
                    if len(data) != int(m[2]):
                        issues.append(dict(type='capture_length', capture=capture.name))
                    if current['format'] == 'binary':
                        r = dict(current, sequence=data[7] if len(data)>7 else None, bytes=len(data), first_dword=int.from_bytes(data[:4], 'little'))
                        if valid_binary(data): strict.append(r)
                        if valid_binary(data): responses.append(r)
                        else: issues.append(dict(type='invalid_observed_binary', capture=capture.name))
            for r in [x for x in reads if x['step'] == step['number']]:
                if r['result'] == 'DATA_HANDLE' and 'capture' not in r:
                    issues.append(dict(type='missing_capture', read=r))
        elif step['kind'] == 'MC':
            config = dict(re.findall(r'(\w+)=([^\s]+)', next(x for x in lines if 'EXPERIMENT ' in x)))
            requests = {int(n): item for n, item in re.findall(r'REQUEST_INDEX ordinal=(\d+) input_array_index=-?\d+ item=(.*)', text)}
            round_parts = re.split(r'(?m)^.*BEGIN ReadVar invocation round=(\d+) count=(\d+)\n', text)
            for i in range(1, len(round_parts), 3):
                rnd, count, body = int(round_parts[i]), int(round_parts[i+1]), round_parts[i+2]
                hr = re.search(r'invoke_hresult=(0x[0-9A-Fa-f]+)', body)
                errors = {int(n): int(v) for n,v in re.findall(r'slot\[(\d+)\]\.error (?:VT=0x\w+ )?I4=(-?\d+)', body)}
                accepted = 0 if config['shape'] == 'array-variant' else count
                rec = dict(step=step['number'], name=step['name'], log=file.name, round=rnd, requested=count, processed=accepted, shape=config['shape'], cache=int(config['cacheDevice']), hresult=hr[1] if hr else None, errors={str(n): f'0x{v & 0xffffffff:08X}' for n,v in errors.items() if v}, timestamp_scode=re.findall(r'pTimeStamps SCODE=(0x\w+)', body), server_info_scode=re.findall(r'pServerInfos SCODE=(0x\w+)',body))
                mc_rounds.append(rec)
                if len(requests) != count or len(errors) != count:
                    issues.append(dict(type='mc_element_coverage', step=step['number'], round=rnd, count=count, requests=len(requests), errors=len(errors)))
                for n in range(count):
                    prefix = r'slot\['+str(n)+r'\]'
                    vt = re.search(prefix+r'\.value VT=(0x\w+)', body)
                    val = re.search(prefix+r'\.value (I4|R8|OLE_DATE)=([^\r\n]+)', body)
                    string_val = re.search(prefix+r'\.value=(.*?) \(chars=(\d+)\)', body)
                    quality = re.search(prefix+r'\.quality (?:VT=0x\w+ )?I2=(-?\d+)', body)
                    slots.append(dict(step=step['number'], log=file.name, round=rnd, ordinal=n, item=requests.get(n), error=f'0x{errors[n] & 0xffffffff:08X}' if n in errors else None, quality=int(quality[1]) if quality else None, value_type=vt[1] if vt else None, value=val[2] if val else ('' if string_val and string_val[2]=='0' else string_val[1] if string_val else None), cache=int(config['cacheDevice'])))
    def transitions(rr):
        out=[]
        for a,b in zip(rr,rr[1:]):
            bridge=[x for x in mc_rounds if a['step'] < x['step'] < b['step']]
            elements=sum(x['processed'] for x in bridge)
            actual=(b['sequence']-a['sequence'])%256
            expected=(1+elements)%256
            out.append(dict(from_capture=a['capture'], to_capture=b['capture'], from_step=a['step'], to_step=b['step'], actual=actual, expected=expected, mc_elements=elements, match=actual==expected))
        return out
    trans=transitions(responses)
    strict_trans=transitions(strict)
    fmt=defaultdict(Counter)
    for x in reads: fmt[x['format']][x['result']]+=1
    cache={}
    for mode in sorted({x['cache'] for x in mc_rounds}):
        rr=[x for x in mc_rounds if x['cache']==mode and x['shape']!='array-variant']
        cache[str(mode)]=dict(rounds=len(rr), elements=sum(x['processed'] for x in rr), timestamp_variants=dict(Counter(v for x in rr for v in x['timestamp_scode'])), clock_values=[x for x in slots if x['cache']==mode and x['item'] and 'SysTimeBCD' in x['item']])
    partial=[x for x in mc_rounds if x['errors'] and len(x['errors']) < x['requested']]
    error_quality_mismatches=[x for x in slots if x['quality'] is not None and x['error'] is not None and x['quality'] != (192 if x['error']=='0x00000000' else 0)]
    unexpected=[{k:x[k] for k in ('number','name','rc','status','expect')} for x in steps if (x['expect']=='OK' and x['status'] not in ('OK','RESPONDED')) or (x['expect']=='NEG' and x['status'] not in ('API_NEGATIVE','ITEM_FAILURE'))]
    issues.extend(dict(type='error_quality',slot=x) for x in error_quality_mismatches)
    binary_files={p.name for p in logs.glob('*_binary.bin')}
    unreferenced=sorted(binary_files-used)
    if unreferenced: issues.append(dict(type='unreferenced_binary',files=unreferenced))
    result=dict(runner=str(runner.relative_to(root)), source='Only real_tests/bin/logs; console duplicates excluded', steps=len(steps), logs=len(files), step_status=dict(Counter(x['status'] for x in steps)), strict_predicate='len >= 20; uint16_le(0) == 20; uint16_le(2) == 1; bytes[16:20] == F9F8F7F6', strict_valid_responses=len(strict), strict_transitions=len(strict_trans), requested_count_mismatches=dict(responses=dict(expected=198,actual=len(strict)),transitions=dict(expected=197,actual=len(strict_trans))), observed_word_header=dict(predicate='len >= 20; uint16_le(0) == 20; uint16_le(2) == 1; bytes[16:20] == F9F8F7F6', responses=len(responses), transitions=len(trans), first_dwords=dict(Counter(str(x['first_dword']) for x in responses)), counter_mismatches=[x for x in trans if not x['match']], transitions_detail=trans), dde_formats={k:dict(v) for k,v in fmt.items()}, mc=dict(rounds=len(mc_rounds), requested_elements=sum(x['requested'] for x in mc_rounds), processed_elements=sum(x['processed'] for x in mc_rounds), rejected_shape_rounds=sum(x['shape']=='array-variant' for x in mc_rounds), slot_error_counts=dict(Counter(x['error'] for x in slots)), partial_error_rounds=partial, rounds_detail=mc_rounds), cache=cache, timestamp_interpretation='pTimeStamps VARIANT_ERROR 0x80020004 is missing optional output, not a source timestamp. SysTimeBCD OLE_DATE is a dynamic value; changes do not establish source freshness.', unexpected_runner_outcomes=unexpected, structural_mismatches=issues, failures=[x for x in reads if x['result']!='DATA_HANDLE'], steps_detail=[{k:v.isoformat() if isinstance(v,datetime) else v for k,v in x.items()} for x in steps])
    result['superseded_dword_negative_control'] = dict(accepted=sum(rejected_dword_predicate((logs/x['capture']).read_bytes()) for x in responses), predicate='uint32_le(offset 0) == 20; rejected hypothesis')
    result['strict_predicate'] = 'len >= 20; uint16_le(0) == 20; uint16_le(2) == 1; bytes[16:20] == F9F8F7F6'
    result['observed_word_header']['predicate'] = result['strict_predicate']
    result['requested_count_mismatches'] = {k:v for k,v in result['requested_count_mismatches'].items() if v['actual'] != v['expected']}
    result['mc']['slots_detail'] = slots
    result['reads_detail'] = reads
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[3])
    parser.add_argument('--runner',default='real_tests/logs/RUN_ALL_21704_14346.txt')
    parser.add_argument('--output',default='research/phase11/REAL_INPUT_CORPUS/latest_runtime_validation.json')
    args=parser.parse_args()
    r=validate(args.root,args.root/args.runner)
    out=args.root/args.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(r,indent=2)+'\n')
    summary={k:r[k] for k in ('steps','logs','step_status','strict_valid_responses','strict_transitions','dde_formats','unexpected_runner_outcomes','structural_mismatches')}
    summary['observed_word_header']={k:v for k,v in r['observed_word_header'].items() if k!='transitions_detail'}
    summary['mc']={k:v for k,v in r['mc'].items() if k not in ('rounds_detail','partial_error_rounds','slots_detail')}
    print(json.dumps(summary,indent=2))
    # The explicit WORD schema is authoritative; retain the old DWORD rejection.
    return int(r['strict_valid_responses']!=198 or r['strict_transitions']!=197 or bool(r['structural_mismatches']) or bool(r['observed_word_header']['counter_mismatches']) or bool(r['unexpected_runner_outcomes']))

if __name__=='__main__':
    raise SystemExit(main())
