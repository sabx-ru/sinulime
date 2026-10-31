#!/usr/bin/env python3
"""Recount raw decoded TypeLib function descriptors and cross-check ABI records."""
import argparse
import json
from collections import Counter
from pathlib import Path

SOURCE = Path('/root/PL/stages/stage16/reports/typelib_decode.json')
ABI = Path('/root/PL/stages/stage16_5/abi/typelib_abi_records.json')
OUTPUT = Path(__file__).with_name('method_count.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--decode', type=Path, default=SOURCE)
    parser.add_argument('--abi', type=Path, default=ABI)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    decoded = json.loads(args.decode.read_text())
    abi = json.loads(args.abi.read_text())
    scope = abi['scope']
    result = {
        'schema': 'stage16_6.method-counts.v1',
        'sources': {'decoded_typelib': str(args.decode), 'abi_records': str(args.abi)},
        'definitions': {
            'direct_func_records': 'count every entry in a TypeInfo funcs array once',
            'inherited_methods': 'not expanded; refs/impltypes add no funcs records',
            'duplicate_memids': 'not collapsed; each descriptor is counted, duplicates separately reported per TypeInfo',
            'properties': 'accessor FUNCDESCs remain functions; INVOKE_PROPERTY* records identified separately',
            'variables': 'vars descriptors are separate and not methods',
        },
        'revisions': {},
    }
    for rev in ('old', 'new'):
        tis = decoded[rev]['library']['typeinfos']
        by_name = {ti['name']: ti for ti in tis}
        rows = []
        for ti in tis:
            funcs = ti.get('funcs', [])
            memids = Counter(f.get('memid') for f in funcs)
            rows.append({
                'name': ti['name'], 'typekind': ti.get('typekind'),
                'direct_func_records': len(funcs), 'unique_memids': len(memids),
                'duplicate_memids': {str(k): n for k, n in memids.items() if n > 1},
                'property_accessor_records': sum(f.get('invkind') in ('INVOKE_PROPERTYGET', 'INVOKE_PROPERTYPUT', 'INVOKE_PROPERTYPUTREF') for f in funcs),
                'variables': len(ti.get('vars', [])),
            })
        target_rows = [next(r for r in rows if r['name'] == n) for n in scope]
        checks = {n: len(by_name[n].get('funcs', [])) == len(abi['records'][rev][n]['functions']) for n in scope}
        result['revisions'][rev] = {
            'typeinfo_count': len(tis),
            'direct_func_records_all_typeinfos': sum(r['direct_func_records'] for r in rows),
            'target_typeinfo_count': len(scope),
            'target_direct_func_records': sum(r['direct_func_records'] for r in target_rows),
            'target_unique_memids_sum_per_typeinfo': sum(r['unique_memids'] for r in target_rows),
            'target_duplicate_memids': sum(len(r['duplicate_memids']) for r in target_rows),
            'target_property_accessor_records': sum(r['property_accessor_records'] for r in target_rows),
            'target_variables': sum(r['variables'] for r in target_rows),
            'dispatch_target_typeinfos': sum(r['typekind'] == 'TKIND_DISPATCH' for r in target_rows),
            'abi_function_counts_match_per_target': checks,
            'target_rows': target_rows,
            'all_typeinfo_rows': rows,
        }
    for rev, data in result['revisions'].items():
        assert data['typeinfo_count'] == 28
        assert data['direct_func_records_all_typeinfos'] == 92
        assert data['target_direct_func_records'] == 32
        assert data['target_property_accessor_records'] == 0
        assert data['target_duplicate_memids'] == 0
        assert data['target_variables'] == 0
        assert all(data['abi_function_counts_match_per_target'].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f'Wrote {args.output}')
    for rev, data in result['revisions'].items():
        print(f"{rev}: {data['typeinfo_count']} TypeInfos; {data['direct_func_records_all_typeinfos']} all-library funcs; {data['target_direct_func_records']} target funcs; 0 properties; ABI records match")


if __name__ == '__main__':
    main()
