from datetime import datetime, timedelta, timezone

import pytest

from app.services.open_meteo import HeatIndexReading
from app.storage.alert_state_store import LocalJSONAlertStateStore
from app.storage.push_subscription_store import LocalJSONPushSubscriptionStore
from app.storage.registration_store import LocalJSONRegistrationStore
from ingestion import alert_check


@pytest.fixture
def alert_env(tmp_path, monkeypatch):
    reg_store = LocalJSONRegistrationStore(path=tmp_path / "registrations.json")
    state_store = LocalJSONAlertStateStore(path=tmp_path / "alert_state.json")
    # alert_check.run() always checks push_store.zones_with_subscriptions() too, even
    # in tests that only care about WhatsApp — without patching this, that call would
    # hit whatever get_push_subscription_store() actually resolves to (real Firestore,
    # if the developer's own .env has STORAGE_BACKEND=firestore set, as it does here).
    push_store = LocalJSONPushSubscriptionStore(path=tmp_path / "push_subscriptions.json")
    monkeypatch.setattr(alert_check, "get_registration_store", lambda: reg_store)
    monkeypatch.setattr(alert_check, "get_alert_state_store", lambda: state_store)
    monkeypatch.setattr(alert_check, "get_push_subscription_store", lambda: push_store)
    monkeypatch.setattr(alert_check, "WHATSAPP_ACCESS_TOKEN", "test_token")
    monkeypatch.setattr(alert_check, "WHATSAPP_PHONE_NUMBER_ID", "test_phone_number_id")
    return reg_store, state_store, push_store


def _reading(apparent_c: float) -> HeatIndexReading:
    return HeatIndexReading(
        temperature_c=apparent_c - 5,
        apparent_temperature_c=apparent_c,
        relative_humidity_pct=30,
        observed_at="2026-06-01T14:00",
    )


def test_no_registrations_does_nothing(alert_env, capsys):
    alert_check.run(dry_run=True)
    assert "nothing to check" in capsys.readouterr().out


def test_below_threshold_sends_nothing(alert_env, monkeypatch, block_real_whatsapp_sends):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(30.0))

    alert_check.run(dry_run=True)

    assert state_store.last_alert_at("model_town") is None
    assert block_real_whatsapp_sends == []


def test_above_threshold_sends_to_every_registered_number(alert_env, monkeypatch, block_real_whatsapp_sends):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    reg_store.register("923000000002", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    alert_check.run(dry_run=False)

    assert len(block_real_whatsapp_sends) == 2
    recipients = {m["to"] for m in block_real_whatsapp_sends}
    assert recipients == {"923000000001", "923000000002"}
    assert state_store.last_alert_at("model_town") is not None


def test_only_zones_with_registrations_are_checked(alert_env, monkeypatch):
    reg_store, _, _ = alert_env
    reg_store.register("923000000001", "model_town")
    checked_zones = []

    def fake_fetch(lat, lon):
        checked_zones.append((lat, lon))
        return _reading(30.0)

    monkeypatch.setattr(alert_check, "fetch_current_heat_index", fake_fetch)
    alert_check.run(dry_run=True)

    assert len(checked_zones) == 1  # not all 20 zones in data/zones.json


def test_cooldown_prevents_repeat_alert(alert_env, monkeypatch, block_real_whatsapp_sends):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))
    state_store.record_alert_sent("model_town", datetime.now(timezone.utc))

    alert_check.run(dry_run=False)

    assert block_real_whatsapp_sends == []


def test_cooldown_expired_sends_again(alert_env, monkeypatch, block_real_whatsapp_sends):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))
    state_store.record_alert_sent("model_town", datetime.now(timezone.utc) - timedelta(hours=7))

    alert_check.run(dry_run=False)

    assert len(block_real_whatsapp_sends) == 1


def test_dry_run_has_no_side_effects(alert_env, monkeypatch, block_real_whatsapp_sends):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    alert_check.run(dry_run=True)

    assert block_real_whatsapp_sends == []
    assert state_store.last_alert_at("model_town") is None


def test_missing_credentials_without_dry_run_raises(alert_env, monkeypatch):
    reg_store, _, _ = alert_env
    reg_store.register("923000000001", "model_town")
    monkeypatch.setattr(alert_check, "WHATSAPP_ACCESS_TOKEN", "")

    with pytest.raises(RuntimeError):
        alert_check.run(dry_run=False)


def test_one_failed_send_does_not_block_the_others(alert_env, monkeypatch):
    reg_store, state_store, _ = alert_env
    reg_store.register("923000000001", "model_town")
    reg_store.register("923000000002", "model_town")
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    sent = []

    def flaky_send(to, body):
        if to == "923000000001":
            raise RuntimeError("simulated send failure")
        sent.append(to)
        return True

    monkeypatch.setattr(alert_check, "send_message", flaky_send)

    alert_check.run(dry_run=False)

    assert sent == ["923000000002"]
    assert state_store.last_alert_at("model_town") is not None  # the one success still counts


def test_mask_phone_never_exposes_the_full_number():
    masked = alert_check.mask_phone("923001234567")
    assert "923001234567" not in masked


def test_build_alert_message_includes_zone_and_temperature_and_opt_out():
    message = alert_check.build_alert_message("Model Town", 45.2)
    assert "Model Town" in message
    assert "45" in message
    assert "STOP" in message


# --- Web Push channel (WhatsApp-independent) ---


def test_push_only_zone_alerts_without_any_whatsapp_registration(
    alert_env, monkeypatch, block_real_web_push_sends, block_real_whatsapp_sends
):
    from app.models import PushSubscription

    _, state_store, push_store = alert_env
    push_store.subscribe(PushSubscription(endpoint="e1", p256dh="p", auth="a", zone_id="model_town"))
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    alert_check.run(dry_run=False)

    assert len(block_real_web_push_sends) == 1
    assert block_real_web_push_sends[0]["endpoint"] == "e1"
    assert block_real_whatsapp_sends == []  # nobody registered on that channel
    assert state_store.last_alert_at("model_town") is not None


def test_both_channels_alerted_independently_for_the_same_zone(
    alert_env, monkeypatch, block_real_web_push_sends, block_real_whatsapp_sends
):
    from app.models import PushSubscription

    reg_store, _, push_store = alert_env
    reg_store.register("923000000001", "model_town")
    push_store.subscribe(PushSubscription(endpoint="e1", p256dh="p", auth="a", zone_id="model_town"))
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    alert_check.run(dry_run=False)

    assert len(block_real_whatsapp_sends) == 1
    assert len(block_real_web_push_sends) == 1


def test_missing_vapid_key_without_dry_run_raises_when_push_subscribers_exist(alert_env, monkeypatch):
    from app.models import PushSubscription

    _, _, push_store = alert_env
    push_store.subscribe(PushSubscription(endpoint="e1", p256dh="p", auth="a", zone_id="model_town"))
    monkeypatch.setattr(alert_check, "VAPID_PRIVATE_KEY", "")

    with pytest.raises(RuntimeError):
        alert_check.run(dry_run=False)


def test_push_dry_run_sends_nothing_and_writes_no_state(alert_env, monkeypatch, block_real_web_push_sends):
    from app.models import PushSubscription

    _, state_store, push_store = alert_env
    push_store.subscribe(PushSubscription(endpoint="e1", p256dh="p", auth="a", zone_id="model_town"))
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    alert_check.run(dry_run=True)

    assert block_real_web_push_sends == []
    assert state_store.last_alert_at("model_town") is None


def test_one_failed_push_does_not_block_the_others(alert_env, monkeypatch):
    from app.models import PushSubscription

    _, state_store, push_store = alert_env
    push_store.subscribe(PushSubscription(endpoint="good", p256dh="p", auth="a", zone_id="model_town"))
    push_store.subscribe(PushSubscription(endpoint="bad", p256dh="p", auth="a", zone_id="model_town"))
    monkeypatch.setattr(alert_check, "fetch_current_heat_index", lambda lat, lon: _reading(45.0))

    sent = []

    def flaky_push(subscription, title, body):
        if subscription.endpoint == "bad":
            raise RuntimeError("simulated push failure")
        sent.append(subscription.endpoint)
        return True

    monkeypatch.setattr(alert_check, "send_push_notification", flaky_push)

    alert_check.run(dry_run=False)

    assert sent == ["good"]
    assert state_store.last_alert_at("model_town") is not None  # the one success still counts
