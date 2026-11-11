import json
from pathlib import Path


def _load(cnc):
    return json.loads((Path('runs/v1.0.0') / cnc / 'evidence.json').read_text())


def test_cnc135_and_cnc152_have_separate_actual_target_roles_and_schema_fields():
    for cnc in ('cnc135', 'cnc152'):
        data = _load(cnc)
        assert data['schema'] == 'read-only-topology/v1.0.0'
        summary = data['summary']
        assert summary['physical_edge_sets_equal'] is True
        assert summary['topology_all_tlv_complete'] is True
        assert summary['target_all_tlv_complete'] is True
        assert summary['unresolved_service_mappings'] == 0
        assert summary['actual_cu_with_complete_tlv'] == summary['cu_count']
        assert summary['target_cu_with_complete_tlv'] == summary['cu_count']

        for axis in data['axes']:
            assert axis['status'] in {'confirmed', 'provisional', 'unresolved'}
            assert axis['confidence'] in {'confirmed', 'provisional', 'ambiguous', 'unresolved'}
            if axis['status'] == 'confirmed':
                assert axis['chain']['cu'] is not None
                assert axis['chain']['slot'] is not None
            else:
                assert axis['chain']['cu'] is None or axis['chain']['slot'] is None
            assert axis['evidence']['source']
            for ref in axis['evidence'].values():
                if isinstance(ref, dict):
                    assert 'index' in ref

        for drive in data['drives']:
            assert drive['status'] in {'confirmed', 'provisional', 'unresolved'}
            assert drive['confidence'] in {'confirmed', 'provisional', 'ambiguous', 'unresolved'}
            assert drive['cu'] is not None
            assert drive['evidence']

        for component in data['components']:
            assert component['identity']
            assert component['device_class']
            assert component['status'] in {'confirmed', 'provisional', 'unresolved'}
            assert component['confidence'] in {'confirmed', 'provisional', 'ambiguous', 'unresolved'}
            assert component['evidence']

        for connection in data['connections']:
            assert connection['status'] in {'confirmed', 'reference_only', 'provisional', 'unresolved'}
            assert connection['confidence'] in {'confirmed', 'probable', 'provisional', 'ambiguous', 'unresolved'}
            assert connection['from'] and connection['to']
            assert connection['evidence']['source']
            if connection['status'] == 'confirmed':
                assert connection['confidence'] == 'confirmed'
                assert connection['evidence']

        assert data['unresolved_ports'] == []
        assert data['mapping_problems'] == []
