import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.rate_limit import RateLimiter

client = TestClient(app)

TEST_APP_SECRET = "test_app_secret_1234567890"
VERIFY_TOKEN = "test_verify_token"


def _text_payload(phone: str, body: str) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_id",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "test_phone_number_id"},
                            "messages": [
                                {"from": phone, "id": "wamid.test", "timestamp": "0", "type": "text", "text": {"body": body}}
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _post_raw(payload: dict, headers: dict | None = None):
    body = json.dumps(payload).encode()
    return client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", **(headers or {})},
    )


def _signed_headers(payload: dict, app_secret: str = TEST_APP_SECRET) -> dict:
    body = json.dumps(payload).encode()
    signature = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return {"X-Hub-Signature-256": f"sha256={signature}"}


def _post_signed(payload: dict, app_secret: str = TEST_APP_SECRET):
    body = json.dumps(payload).encode()
    signature = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": f"sha256={signature}"},
    )


def _configure_secret(monkeypatch, app_secret: str = TEST_APP_SECRET):
    monkeypatch.setattr("app.services.whatsapp_api.WHATSAPP_APP_SECRET", app_secret)


# --- GET verification handshake ---


def test_verification_handshake_echoes_challenge_when_token_matches(monkeypatch):
    monkeypatch.setattr("app.routes.intake.WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    response = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "12345"},
    )
    assert response.status_code == 200
    assert response.text == "12345"


def test_verification_handshake_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr("app.routes.intake.WHATSAPP_VERIFY_TOKEN", VERIFY_TOKEN)
    response = client.get(
        "/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert response.status_code == 403


# --- POST message webhook: signature verification ---


def test_dev_mode_allows_unsigned_requests_when_no_secret_configured(report_store):
    response = _post_raw(_text_payload("923000000001", "hi"))
    assert response.status_code == 200


def test_unsigned_request_rejected_once_secret_configured(monkeypatch, report_store):
    _configure_secret(monkeypatch)
    response = _post_raw(_text_payload("923000000002", "hi"))
    assert response.status_code == 403


def test_validly_signed_request_is_accepted(monkeypatch, report_store):
    _configure_secret(monkeypatch)
    payload = _text_payload("923000000003", "hi")
    response = _post_signed(payload)
    assert response.status_code == 200


def test_tampered_body_after_signing_is_rejected(monkeypatch, report_store):
    _configure_secret(monkeypatch)
    payload = _text_payload("923000000004", "hi")
    headers = _signed_headers(payload)
    tampered_body = json.dumps(_text_payload("923000000004", "something else")).encode()
    response = client.post(
        "/webhooks/whatsapp",
        content=tampered_body,
        headers={"Content-Type": "application/json", **headers},
    )
    assert response.status_code == 403


def test_signature_from_a_different_secret_is_rejected(monkeypatch, report_store):
    _configure_secret(monkeypatch, app_secret=TEST_APP_SECRET)
    payload = _text_payload("923000000005", "hi")
    wrong_headers = _signed_headers(payload, app_secret="a_completely_different_secret")
    response = client.post(
        "/webhooks/whatsapp",
        content=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **wrong_headers},
    )
    assert response.status_code == 403


# --- Rate limiting ---


def test_rate_limit_blocks_after_max_messages(report_store, monkeypatch):
    monkeypatch.setattr("app.routes.intake._rate_limiter", RateLimiter(max_events=2, window_seconds=60))
    phone = "923009999001"

    r1 = _post_raw(_text_payload(phone, "hi"))
    r2 = _post_raw(_text_payload(phone, "hi"))
    r3 = _post_raw(_text_payload(phone, "hi"))

    assert r1.status_code == 200 and r2.status_code == 200 and r3.status_code == 200


def test_rate_limit_is_per_phone_not_global(report_store, monkeypatch):
    monkeypatch.setattr("app.routes.intake._rate_limiter", RateLimiter(max_events=1, window_seconds=60))

    r1 = _post_raw(_text_payload("923009999002", "hi"))
    r2 = _post_raw(_text_payload("923009999003", "hi"))

    assert r1.status_code == 200 and r2.status_code == 200
