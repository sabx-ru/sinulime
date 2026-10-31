import json

import pytest

from application.service import OfflineApplicationService
from application.validation import ValidationError, validate_event, validate_request
from persistence.filesystem import EventStore
from persistence.publication import PublicationCoordinator


def test_event_offsets_and_revisions_reject_bool():
    with pytest.raises(ValidationError):
        validate_event({"id": "1", "event_id": "e", "offset": True})
    with pytest.raises(ValidationError):
        validate_event({"event_version": "event-v1", "event_id": "e", "offset": 1,
                        "installation_id": "i", "kind": "k", "revision": False,
                        "payload": {}})


def test_filter_values_must_be_json_serializable():
    with pytest.raises(ValidationError):
        validate_request({"jsonrpc": "2.0", "id": 1, "method": "snapshot.list",
                          "params": {"filters": {"bad": object()}}})


def test_malformed_store_cursor_is_resync_required():
    class Store:
        def list(self, query, cursor, limit):
            return {"items": [], "has_more": True, "next_cursor": "not-an-integer"}

    response = OfflineApplicationService(snapshots=Store()).handle(
        {"jsonrpc": "2.0", "id": 1, "method": "snapshot.list", "params": {}}
    )
    assert response["error"]["code"] == "RESYNC_REQUIRED"


def test_event_cursor_is_log_coordinate_and_stale_after_retention(tmp_path):
    store = EventStore(tmp_path / "events.json")
    store.append_batch([{"id": "1", "event_id": "e1", "offset": 10},
                       {"id": "2", "event_id": "e2", "offset": 20},
                       {"id": "3", "event_id": "e3", "offset": 30}])
    first = store.list({}, None, 1)
    second = store.list({}, int(first["next_cursor"]), 1)
    assert [item["offset"] for item in second["items"]] == [20]
    store.retain_through(10)
    with pytest.raises(IndexError):
        store.list({}, 10, 1)


def test_event_cursor_is_stale_when_retention_leaves_empty_log(tmp_path):
    store = EventStore(tmp_path / "events.json")
    store.append_batch([{"id": "1", "event_id": "e1", "offset": 10},
                       {"id": "2", "event_id": "e2", "offset": 20}])
    store.retain_through(20)
    with pytest.raises(IndexError):
        store.list({"from_offset": 10}, None, 1)
    assert store.earliest_offset() == 21


def test_internal_error_does_not_disclose_exception_text():
    class BrokenStore:
        def list(self, query, cursor, limit):
            raise RuntimeError("secret filesystem path")
    response = OfflineApplicationService(snapshots=BrokenStore()).handle(
        {"jsonrpc": "2.0", "id": 1, "method": "snapshot.list", "params": {}})
    assert response["error"] == {"code": "INTERNAL_ERROR", "message": "internal error", "data": {}}


def test_publication_rejects_corrupt_nested_evidence(tmp_path):
    path = tmp_path / "publication.json"
    path.write_text(json.dumps({"revision": 1, "snapshot": {},
                                "evidence": [{"evidence_id": "broken"}],
                                "events": []}))
    with pytest.raises(RuntimeError):
        PublicationCoordinator(path)
