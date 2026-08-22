from datetime import datetime, timezone

from app.storage.alert_state_store import LocalJSONAlertStateStore


def make_store(tmp_path):
    return LocalJSONAlertStateStore(path=tmp_path / "alert_state.json")


def test_last_alert_at_is_none_initially(tmp_path):
    assert make_store(tmp_path).last_alert_at("model_town") is None


def test_record_and_retrieve_last_alert(tmp_path):
    store = make_store(tmp_path)
    now = datetime.now(timezone.utc)
    store.record_alert_sent("model_town", now)
    retrieved = store.last_alert_at("model_town")
    assert abs((retrieved - now).total_seconds()) < 1


def test_zones_are_independent(tmp_path):
    store = make_store(tmp_path)
    store.record_alert_sent("model_town", datetime.now(timezone.utc))
    assert store.last_alert_at("gulberg") is None
