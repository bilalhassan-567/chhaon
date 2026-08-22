"""Covers app/routes/push.py and PushSubscriptionStore — the Web Push opt-in path,
the WhatsApp-independent analog of the ALERT ON/STOP registration flow."""

from fastapi.testclient import TestClient

from app.main import app
from app.models import PushSubscription

client = TestClient(app)

_SUB_BODY = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/example-endpoint-1",
    "p256dh": "fake_p256dh_key",
    "auth": "fake_auth_secret",
    "zone_id": "model_town",
}


def test_vapid_public_key_endpoint_returns_configured_key(monkeypatch):
    monkeypatch.setattr("app.routes.push.VAPID_PUBLIC_KEY", "test_public_key_value")
    response = client.get("/api/push/vapid-public-key")
    assert response.status_code == 200
    assert response.json()["publicKey"] == "test_public_key_value"


def test_subscribe_with_known_zone_succeeds(push_subscription_store):
    response = client.post("/api/push/subscribe", json=_SUB_BODY)
    assert response.status_code == 200
    subs = push_subscription_store.list_for_zone("model_town")
    assert len(subs) == 1
    assert subs[0].endpoint == _SUB_BODY["endpoint"]


def test_subscribe_with_unknown_zone_is_rejected(push_subscription_store):
    bad = {**_SUB_BODY, "zone_id": "not_a_real_zone"}
    response = client.post("/api/push/subscribe", json=bad)
    assert response.status_code == 400


def test_resubscribing_the_same_endpoint_is_idempotent_not_duplicated(push_subscription_store):
    client.post("/api/push/subscribe", json=_SUB_BODY)
    client.post("/api/push/subscribe", json=_SUB_BODY)
    assert len(push_subscription_store.list_for_zone("model_town")) == 1


def test_unsubscribe_removes_the_subscription(push_subscription_store):
    client.post("/api/push/subscribe", json=_SUB_BODY)
    response = client.post("/api/push/unsubscribe", json={"endpoint": _SUB_BODY["endpoint"]})
    assert response.status_code == 200
    assert push_subscription_store.list_for_zone("model_town") == []


def test_zones_with_subscriptions_reflects_current_state(push_subscription_store):
    push_subscription_store.subscribe(
        PushSubscription(endpoint="e1", p256dh="p", auth="a", zone_id="gulberg")
    )
    push_subscription_store.subscribe(
        PushSubscription(endpoint="e2", p256dh="p", auth="a", zone_id="dha")
    )
    assert push_subscription_store.zones_with_subscriptions() == {"gulberg", "dha"}
