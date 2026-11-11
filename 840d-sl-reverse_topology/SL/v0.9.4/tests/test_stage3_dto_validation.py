import pytest
from application.dto import error
from application.validation import validate_request, validate_response, ValidationError

def test_dto_error_rejects_unknown_not_comparable_reason():
    with pytest.raises(ValueError):
        error(1, 'NOT_COMPARABLE', 'cannot compare', {'reason': 'invented_reason'})

def test_dto_error_requires_mapping_reason_and_valid_opaque_snapshot_ids():
    cases = [
        None,
        {},
        {'reason': 'identity_mismatch', 'actual_snapshot_id': ''},
        {'reason': 'identity_mismatch', 'target_snapshot_id': '\x00bad'},
        {'reason': 'identity_mismatch', 'actual_snapshot_id': 1},
    ]
    for data in cases:
        with pytest.raises(ValueError):
            error(1, 'NOT_COMPARABLE', 'cannot compare', data)

def test_dto_error_accepts_each_not_comparable_reason_and_opaque_ids():
    reasons = {
        'selector_mismatch', 'representation_mismatch', 'incomplete_snapshot',
        'identity_mismatch', 'unsupported_comparison',
    }
    for reason in reasons:
        response = error(1, 'NOT_COMPARABLE', 'cannot compare', {
            'reason': reason, 'actual_snapshot_id': 'a', 'target_snapshot_id': 't',
        })
        assert response['error']['data']['reason'] == reason

def test_not_comparable_response_requires_known_reason_and_valid_ids():
    response = {'jsonrpc':'2.0','id':1,'error':{'code':'NOT_COMPARABLE','message':'cannot compare','data':{}}}
    with pytest.raises(ValidationError): validate_response(response, 'topology.reconcile')
    response['error']['data'] = {'reason':'made_up'}
    with pytest.raises(ValidationError): validate_response(response, 'topology.reconcile')
    response['error']['data'] = {'reason':'identity_mismatch','actual_snapshot_id':''}
    with pytest.raises(ValidationError): validate_response(response, 'topology.reconcile')

def test_all_methods_have_explicit_params_contract():
    for method, params in [("capabilities.get",{}),("health.get",{}),("snapshot.list",{}),("snapshot.get",{"snapshot_id":"s"}),("topology.query",{"snapshot_id":"s"}),("topology.reconcile",{"actual_snapshot_id":"a","target_snapshot_id":"t"}),("evidence.get",{"evidence_id":"e"}),("event.list",{})]:
        validate_request({"jsonrpc":"2.0","id":1,"method":method,"params":params})

def test_replay_starts_are_exclusive():
    with pytest.raises(ValidationError): validate_request({"jsonrpc":"2.0","id":1,"method":"event.list","params":{"from_event_id":"e","from_offset":1}})
