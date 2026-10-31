#!/usr/bin/env python3
import json
from pathlib import Path

SOURCE = Path('/root/PL/stages/stage16/reports/typelib_decode.json')
OUT = Path('/root/PL/stages/stage16_5/abi')
TARGETS = {
    'IVar', 'IVar2', 'IReadVarAsyncCallback', 'IWriteVarAsyncCallback',
    'IReadVarAsyncCallback2', 'IWriteVarAsyncCallback2',
    'IMCCommand', 'IMCCommandAsyncCallback',
}

def canonical_typeinfo(t):
    # Preserve decoded ABI facts, excluding no fields; key sorting makes the record stable.
    return {k: t[k] for k in sorted(t)}

def sig(f):
    return {
        'memid': f['memid'],
        'name': f['name'],
        'funckind': f['funckind'],
        'invkind': f['invkind'],
        'callconv': f['callconv'],
        'flags': f['flags'],
        'entry': f['entry'],
        'params': [
            {
                'name': p['name'],
                'flags': p['flags'],
                'tdesc': p['tdesc'],
                'default_value': p['default_value'],
                'custom_data': p['custom_data'],
            } for p in f['params']
        ],
        'help_string': f['help_string'],
        'custom_data': f['custom_data'],
    }

def compact(t):
    return {
        'name': t['name'], 'guid': t['guid'], 'typekind': t['typekind'],
        'flags': t['flags'], 'alignment': t['alignment'],
        'version': t['version'], 'doc_string': t['doc_string'],
        'impltypes': t['impltypes'],
        'functions': [sig(f) for f in t['funcs']],
    }

data = json.loads(SOURCE.read_text())
all_records = {}
for side in ('old', 'new'):
    records = {}
    for t in data[side]['library']['typeinfos']:
        if t.get('name') in TARGETS:
            records[t['name']] = canonical_typeinfo(t)
    all_records[side] = records

normalized = {
    'schema': 'stage16_5.type-library-abi.v1',
    'source': str(SOURCE),
    'scope': sorted(TARGETS),
    'records': {
        side: {name: compact(t) for name, t in sorted(recs.items())}
        for side, recs in all_records.items()
    },
}
(OUT / 'typelib_abi_records.json').write_text(json.dumps(normalized, indent=2, sort_keys=True) + '\n')

# JSON-level comparison retains exact old/new values and identifies changed paths.
def diff(a, b, path=''):
    out = []
    if type(a) is not type(b): return [path or '$']
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            p = f'{path}.{k}' if path else k
            if k not in a or k not in b: out.append(p)
            else: out += diff(a[k], b[k], p)
    elif isinstance(a, list):
        if len(a) != len(b): out.append(path + '.length')
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    elif a != b: out.append(path)
    return out

changes = {}
for name in sorted(TARGETS):
    old = normalized['records']['old'].get(name)
    new = normalized['records']['new'].get(name)
    paths = diff(old, new)
    changes[name] = {'status': 'unchanged' if not paths else 'changed', 'changed_paths': paths,
                     'old_present': old is not None, 'new_present': new is not None}
comparison = {
    'schema': 'stage16_5.type-library-abi-comparison.v1',
    'source': str(SOURCE), 'scope': sorted(TARGETS), 'interfaces': changes,
    'summary': {
        'target_count': len(TARGETS),
        'unchanged_count': sum(v['status'] == 'unchanged' for v in changes.values()),
        'changed_count': sum(v['status'] == 'changed' for v in changes.values()),
    },
}
(OUT / 'typelib_abi_comparison.json').write_text(json.dumps(comparison, indent=2, sort_keys=True) + '\n')
