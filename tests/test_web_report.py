"""Covers app/routes/report.py — the WhatsApp-independent secondary intake channel.
Same anonymous storage path as WhatsApp intake (NewReport -> add_or_increment), just
reached via a plain web form instead of a webhook."""

from fastapi.testclient import TestClient

from app.main import app
from app.services.rate_limit import RateLimiter

client = TestClient(app)


def test_report_form_page_loads():
    response = client.get("/report")
    assert response.status_code == 200
    assert "Report a Heat Incident" in response.text


def test_submit_with_coordinates_resolves_nearest_zone(report_store):
    response = client.post(
        "/api/report",
        json={"incident_type": "heat_exhaustion", "lat": 31.4805, "lon": 74.3232},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["zone_name"] == "Model Town"

    [report] = report_store.list_since()
    assert report.zone_id == "model_town"
    assert report.geo_source.value == "location_pin"
    assert report.source == "web"


def test_submit_with_zone_name_fallback(report_store):
    response = client.post(
        "/api/report",
        json={"incident_type": "heatstroke", "zone_name": "Gulberg"},
    )
    assert response.status_code == 200
    [report] = report_store.list_since()
    assert report.zone_id == "gulberg"
    assert report.geo_source.value == "zone_name"
    assert report.source == "web"


def test_submit_with_unrecognized_zone_name_is_rejected(report_store):
    response = client.post(
        "/api/report",
        json={"incident_type": "other", "zone_name": "Nowhere Land Atlantis"},
    )
    assert response.status_code == 400


def test_submit_with_neither_location_nor_zone_name_is_rejected(report_store):
    response = client.post("/api/report", json={"incident_type": "other"})
    assert response.status_code == 400


def test_submit_never_stores_ip_address_in_the_report(report_store):
    """Anonymous-by-design applies to the web channel too — the request's IP is only
    ever used for rate limiting in-memory, never persisted onto the report itself."""
    client.post("/api/report", json={"incident_type": "other", "zone_name": "Model Town"})
    [report] = report_store.list_since()
    assert "ip" not in report.model_dump()


def test_web_and_whatsapp_reports_in_the_same_zone_dedup_together(report_store):
    """The web form reuses the exact same add_or_increment dedup logic — a web
    report and a WhatsApp report in the same zone/incident type/window still merge,
    same as two WhatsApp reports would."""
    from app.models import GeoSource, IncidentType, NewReport

    report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heat_exhaustion,
            source="whatsapp",
        )
    )
    response = client.post(
        "/api/report",
        json={"incident_type": "heat_exhaustion", "lat": 31.4805, "lon": 74.3232},
    )
    assert response.status_code == 200
    assert response.json()["report_count"] == 2
    assert len(report_store.list_since()) == 1  # merged, not a second record


def test_rate_limit_blocks_after_max_from_same_ip(report_store, monkeypatch):
    monkeypatch.setattr("app.routes.report._rate_limiter", RateLimiter(max_events=1, window_seconds=60))
    body = {"incident_type": "other", "zone_name": "Model Town"}

    r1 = client.post("/api/report", json=body)
    r2 = client.post("/api/report", json=body)

    assert r1.status_code == 200
    assert r2.status_code == 429
