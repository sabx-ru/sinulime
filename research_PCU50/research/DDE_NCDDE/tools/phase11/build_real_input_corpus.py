#!/usr/bin/env python3
"""Extract exact preserved PCU inputs and perform offline differential checks.
No vendor execution. All copied bytes originate in real_tests; no generated wire data.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shutil
import struct
import revalidate_latest_runtime as validator

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT/'research/phase11/REAL_INPUT_CORPUS'
RUNNER = Path('real_tests/logs/RUN_ALL_21704_14346.txt')


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--output', type=Path, default=DEST)
    args = ap.parse_args()
    root, out = args.root, args.output
    result = validator.validate(root, root/RUNNER)
    source = root/'real_tests/bin/logs'
    cases, associations, copies, problems = [], [], {RUNNER}, []
    slots = result['mc']['slots_detail']
    steps = {x['number']:x for x in result['steps_detail']}
    for step in steps.values():
        log = Path('real_tests/bin/logs')/step['log']
        console = Path('real_tests/logs')/('console_21704_14346_'+step['name']+'.txt')
        copies.update([log, console])
        original = (root/log).read_text(errors='replace').splitlines()
        console_lines = (root/console).read_text(errors='replace').splitlines()
        # Ignore only watchdog envelope. Every bin-log line must match the console body.
        if console_lines[1:-1] != original:
            problems.append(dict(type='console_bin_disagreement', step=step['number'], log=str(log), console=str(console)))
        cases.append(dict(step=step['number'], name=step['name'], kind=step['kind'],
                          runner=str(RUNNER), runner_line=step['runner_line'], log=str(log), console=str(console),
                          mc_rounds=[x for x in result['mc']['rounds_detail'] if x['step']==step['number']],
                          mc_slots=[x for x in slots if x['step']==step['number']],
                          dde_reads=[x for x in result['reads_detail'] if x['step']==step['number']]))
    decoded = []
    for rec in result['reads_detail']:
        if 'capture' not in rec:
            continue
        raw = (source/rec['capture']).read_bytes()
        capture = Path('real_tests/bin/logs')/rec['capture']
        copies.add(capture)
        step = steps[rec['step']]
        log = Path('real_tests/bin/logs')/rec['log']
        lines = (root/log).read_text(errors='replace').splitlines()
        raw_line = next(i for i,s in enumerate(lines,1) if 'Raw response:' in s and '\\'+rec['capture']+' ' in s)
        association = dict(rec, runner=str(RUNNER), runner_line=step['runner_line'], log=str(log),
                           capture=str(capture), raw_response_line=raw_line,
                           console='real_tests/logs/console_21704_14346_'+step['name']+'.txt',
                           console_read_line=rec['line']+1, console_raw_response_line=raw_line+1,
                           bytes=len(raw))
        associations.append(association)
        if rec['format']=='binary':
            payload = raw[20:]
            size = int.from_bytes(raw[12:16], 'little')
            if size != len(payload):
                problems.append(dict(type='payload_size', capture=str(capture), declared=size, actual=len(payload)))
            if 'SysTimeBCD' in rec['item']:
                value = dict(raw_bcd_hex=payload.hex(), all_nibbles_decimal=all(n<10 for b in payload for n in (b>>4,b&15)))
                kind='BCD_clock'
            elif int.from_bytes(raw[4:6],'little')==1:
                value=struct.unpack('<i',payload)[0]; kind='integer'
            elif int.from_bytes(raw[4:6],'little')==2:
                value=struct.unpack('<d',payload)[0]; kind='double'
            else:
                value=payload.split(b'\0',1)[0].decode('ascii'); kind='string'
            decoded.append(dict(association, header_hex=raw[:20].hex(), payload_hex=payload.hex(),
                                sequence=raw[7], kind=kind, value=value))
    def copy_one(relative):
        target=out/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root/relative,target)
        if target.read_bytes() != (root/relative).read_bytes():
            raise RuntimeError('Byte copy mismatch: '+str(relative))
    # Only independent bounded corpus reads/copies are parallelized.
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(copy_one,sorted(copies)))
    static_checks=[]
    expected_steps={'integer':25,'string':23}
    for r in decoded:
        if r['kind'] not in expected_steps and not re.search(r'/R\[u1,(1|2|10|20)\]$',r['item']):
            continue
        expected_step=expected_steps.get(r['kind'],27)
        candidates=[s for s in slots if s['step']==expected_step and s['item']==r['item'] and s['error']=='0x00000000']
        for s in candidates[:1]:
            expected=int(s['value']) if r['kind']=='integer' else float(s['value']) if r['kind']=='double' else s['value']
            check=dict(capture=r['capture'], dde_log=r['log'], dde_line=r['line'], mc_log=s['log'],
                       mc_step=s['step'], mc_round=s['round'], ordinal=s['ordinal'], item=r['item'],
                       observed=r['value'], expected=expected, match=r['value']==expected)
            static_checks.append(check)
    clocks=[s for s in slots if s['item'] and 'SysTimeBCD' in s['item'] and s['value'] is not None]
    clock_differences=[]
    for a,b in zip(clocks,clocks[1:]):
        clock_differences.append(dict(from_step=a['step'], from_round=a['round'], from_ordinal=a['ordinal'],
                                     to_step=b['step'], to_round=b['round'], to_ordinal=b['ordinal'],
                                     cache_from=a['cache'], cache_to=b['cache'],
                                     ole_date_delta=float(b['value'])-float(a['value'])))
    transitions=result['observed_word_header']['transitions_detail']
    by_capture={Path(x['capture']).name:x for x in associations}
    counter_provenance=[dict(t, from_evidence=by_capture[t['from_capture']], to_evidence=by_capture[t['to_capture']],
                             intervening_mc_rounds=[m for m in result['mc']['rounds_detail'] if t['from_step']<m['step']<t['to_step']]) for t in transitions]
    categories={
        'integers': [25,60], 'BCD_clock':[20,21,28,62,99,102,103], 'R10_R100':[27,65],
        'nonexistent_probes':[29,30,31,32,33,34,35,80,82,88,92,93,94,95],
        'duplicates_20_and_mixed':[17,18], 'text_OEM_binary':[50,53,54,58,66,67,68,69,70,71,72],
        'cache_0_1_2':[38,39,40,41,42,43,44,45,46,47,48],
        'unsupported_variant_array':[36,84], 'repeated_MC_20':[14,90], 'bridges':list(range(73,92))}
    dump(out/'cases.json',dict(categories=categories,cases=cases))
    dump(out/'provenance.json',dict(copied_files=len(copies), console_policy='Console/bin copies cross-checked once; bin logs alone drive events.', associations=associations))
    dump(out/'counter_transitions.json',counter_provenance)
    dump(out/'decoded_binary.json',decoded)
    dump(out/'clock_value_differences.json',clock_differences)
    dump(out/'static_differential.json',static_checks)
    static_mismatches=[x for x in static_checks if not x['match']]
    regression=dict(steps=result['steps'], binary_responses=result['strict_valid_responses'], transitions=len(transitions),
                    counter_mismatches=result['observed_word_header']['counter_mismatches'], structural_mismatches=result['structural_mismatches'],
                    extraction_mismatches=problems, static_checks=len(static_checks), static_mismatches=static_mismatches,
                    clock_value_differences=len(clock_differences), copy_files=len(copies), raw_capture_pairs=len(associations),
                    decoded_kinds=dict(Counter(x['kind'] for x in decoded)), categories=categories,
                    limitations='Offline preserved-run regression; static value equality is empirical. Dynamic BCD and OLE_DATE changes are retained separately; neither establishes freshness.')
    dump(out/'fixture_regression.json',regression)
    print(json.dumps({k:v for k,v in regression.items() if k!='categories'},indent=2))
    return int(bool(problems or static_mismatches or result['structural_mismatches'] or result['observed_word_header']['counter_mismatches']))

if __name__=='__main__':
    raise SystemExit(main())
