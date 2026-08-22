from fastapi.testclient import TestClient

from app.main import app
from app.services.open_meteo import HeatIndexReading

client = TestClient(app)


def _message_payload(phone: str, body: str = "", latitude: float | None = None, longitude: float | None = None) -> dict:
    message = {"from": phone, "id": "wamid.test", "timestamp": "0"}
    if latitude is not None:
        message["type"] = "location"
        message["location"] = {"latitude": latitude, "longitude": longitude}
    else:
        message["type"] = "text"
        message["text"] = {"body": body}

    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_id",
                "changes": [{"value": {"messaging_product": "whatsapp", "messages": [message]}, "field": "messages"}],
            }
        ],
    }


def test_map_page_loads(report_store):
    response = client.get("/")
    assert response.status_code == 200
    assert "Live Community Heat-Risk Map" in response.text
    assert "not a verified medical or legal record" in response.text


def test_reports_api_empty_on_fresh_store(report_store):
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert response.json() == []


def test_heat_index_api_shape(monkeypatch):
    fake_reading = HeatIndexReading(
        temperature_c=38.2,
        apparent_temperature_c=44.1,
        relative_humidity_pct=41,
        observed_at="2026-06-01T14:00",
    )
    monkeypatch.setattr("app.routes.api.fetch_current_heat_index", lambda: fake_reading)

    response = client.get("/api/heat-index")
    assert response.status_code == 200
    body = response.json()
    assert body["apparent_temperature_c"] == 44.1
    assert body["temperature_c"] == 38.2


def test_whatsapp_webhook_full_conversation_end_to_end(report_store, block_real_whatsapp_sends):
    phone = "923001112222"

    r1 = client.post("/webhooks/whatsapp", json=_message_payload(phone, body="hi"))
    assert r1.status_code == 200
    assert "share your location" in block_real_whatsapp_sends[-1]["body"]

    r2 = client.post("/webhooks/whatsapp", json=_message_payload(phone, latitude=31.4805, longitude=74.3232))
    assert r2.status_code == 200
    assert "Model Town" in block_real_whatsapp_sends[-1]["body"]

    r3 = client.post("/webhooks/whatsapp", json=_message_payload(phone, body="2"))
    assert "Logged: model_town, heatstroke" in block_real_whatsapp_sends[-1]["body"]

    reports_response = client.get("/api/reports")
    reports = reports_response.json()
    assert len(reports) == 1
    assert reports[0]["zone_id"] == "model_town"
    assert reports[0]["count"] == 1


def test_webhook_ignores_non_message_events_gracefully(report_store, block_real_whatsapp_sends):
    """Meta sends other webhook event types too (e.g. message status updates) on the
    same endpoint — a payload with no `messages` key must not crash the handler."""
    status_update_payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "waba_id", "changes": [{"value": {"statuses": [{"id": "wamid.x", "status": "delivered"}]}, "field": "messages"}]}],
    }
    response = client.post("/webhooks/whatsapp", json=status_update_payload)
    assert response.status_code == 200
    assert block_real_whatsapp_sends == []
