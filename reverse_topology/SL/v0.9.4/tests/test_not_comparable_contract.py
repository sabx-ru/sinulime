import json

import pytest

from application.service import OfflineApplicationService
from application.validation import NOT_COMPARABLE_REASONS, ValidationError, validate_response
from persistence.filesystem import SnapshotStore
from topology100.reconcile import reconcile


FIXTURES = json.load(open("tests/fixtures/not_comparable_reasons.json"))


def _request(actual, target):
    return {"jsonrpc": "2.0", "id": "r1", "method": "topology.reconcile", "params": {
        "actual_snapshot_id": actual, "target_snapshot_id": target,
    }}


@pytest.mark.parametrize("reason", sorted(NOT_COMPARABLE_REASONS))
def test_reconcile_returns_contract_reason_and_both_snapshot_ids(tmp_path, reason):
    store = SnapshotStore(tmp_path / "snapshots.json")
    fixture = FIXTURES[reason]
    store.put(fixture["actual"])
    if fixture["target"]["id"] != fixture["actual"]["id"]:
        store.put(fixture["target"])

    response = OfflineApplicationService(snapshots=store, reconciler=reconcile).handle(
        _request(fixture["actual"]["id"], fixture["target"]["id"])
    )

    assert response["error"]["code"] == "NOT_COMPARABLE"
    assert response["error"]["data"] == {
        "reason": reason,
        "actual_snapshot_id": fixture["actual"]["id"],
        "target_snapshot_id": fixture["target"]["id"],
    }


from topology100.reconcile import validate_not_comparable_reason


def test_validate_not_comparable_reason_rejects_unknown_reason():
    with pytest.raises(ValueError):
        validate_not_comparable_reason("invented_reason")


def test_validate_response_rejects_unknown_not_comparable_reason():
    response = {"jsonrpc": "2.0", "id": "r1", "error": {
        "code": "NOT_COMPARABLE", "message": "comparison unavailable",
        "data": {"reason": "invented_reason"},
    }}
    with pytest.raises(ValidationError):
        validate_response(response)