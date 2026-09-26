"""File-backed key space, encoding, digests and snapshots."""

import pytest

from desalplant.errors import StoreError, UnknownKeyError
from desalplant.store import keys
from desalplant.store.checksum import digest, short
from desalplant.store.codec import canonical, decode, encode
from desalplant.store.query import matches, select
from desalplant.store.snapshot import SNAPSHOT_VERSION, build
from desalplant.store.store import Store


def test_put_get_and_require_round_trip():
    store = Store()
    store.put("a", {"value": 1})
    assert store.get("a") == {"value": 1}
    assert store.get("missing") is None
    assert store.get("missing", "fallback") == "fallback"
    assert store.require("a") == {"value": 1}
    assert store.has("a") is True
    assert store.has("missing") is False


def test_require_raises_for_an_absent_key():
    store = Store()
    with pytest.raises(UnknownKeyError):
        store.require("missing")


def test_empty_key_is_refused():
    store = Store()
    with pytest.raises(StoreError):
        store.put("", 1)


def test_keys_count_and_export(store):
    store.put("plant/state", "idle")
    store.put("plant/started_at", 1)
    store.put("audit/sequence", 0)
    assert store.keys() == ("audit/sequence", "plant/started_at", "plant/state")
    assert store.keys("plant/") == ("plant/started_at", "plant/state")
    assert store.count() == 3
    exported = store.export()
    exported["plant/state"] = "changed"
    assert store.get("plant/state") == "idle"


def test_checksum_is_order_insensitive(store):
    store.put("a", 1)
    store.put("b", 2)
    checksum = store.checksum()
    assert store.verify(checksum) is True
    assert store.verify("deadbeef") is False
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
    assert short(checksum, 8) == checksum[:8]


def test_short_rejects_a_non_positive_width():
    with pytest.raises(ValueError):
        short("abcdef", 0)


def test_snapshot_reports_count_and_digest(store):
    store.put("a", 1)
    store.put("b", 2)
    snapshot = store.snapshot()
    assert snapshot.version == SNAPSHOT_VERSION
    assert snapshot.count == 2
    assert snapshot.to_dict()["keys"] == ["a", "b"]
    assert build({"a": 1}, "missing").count == 0


def test_store_persists_across_instances(tmp_path):
    path = str(tmp_path / "plant.json")
    first = Store(path)
    first.put("plant/state", "running")
    assert first.path == path
    reopened = Store(path)
    assert reopened.get("plant/state") == "running"


def test_store_ignores_an_empty_document(tmp_path):
    path = tmp_path / "plant.json"
    path.write_text("   ", encoding="utf-8")
    assert Store(str(path)).count() == 0


def test_store_rejects_a_non_object_document(tmp_path):
    path = tmp_path / "plant.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(StoreError):
        Store(str(path))


def test_store_without_a_path_never_writes(tmp_path):
    store = Store()
    store.put("a", 1)
    store.flush()
    assert store.path is None
    assert list(tmp_path.iterdir()) == []


def test_flush_failure_is_reported(tmp_path):
    path = tmp_path / "plant.json"
    store = Store(str(path))
    store.put("a", 1)
    (tmp_path / "plant.json.tmp").mkdir()
    with pytest.raises(StoreError):
        store.put("b", 2)


def test_codec_round_trip_and_canonical_form():
    value = {"b": 2, "a": [1, 2]}
    assert decode(encode(value)) == value
    assert canonical(value) == '{"a":[1,2],"b":2}'


def test_query_helpers():
    assert matches("plant/state", "") is True
    assert matches("plant/state", "plant/") is True
    assert matches("audit/sequence", "plant/") is False
    assert select(["b", "a", "c"], "a") == ("a",)


def test_key_builders():
    assert keys.audit_event_key(7) == "audit/event/000007"
    assert keys.audit_last_key("start") == "audit/last/start"
    assert keys.PLANT_STATE == "plant/state"
    with pytest.raises(ValueError):
        keys.audit_event_key(0)
