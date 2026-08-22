from fastapi.testclient import TestClient

from app.main import app
from app.models import GeoSource, IncidentType, NewReport

client = TestClient(app)


def test_gap_page_loads_with_no_reports(report_store):
    response = client.get("/gap")
    assert response.status_code == 200
    assert "No reports yet" in response.text
    assert "not a verified medical or legal record" in response.text


def test_gap_page_cites_only_sourced_official_figures(report_store):
    response = client.get("/gap")
    # Every figure must carry its citation — this is the dashboard's whole credibility.
    assert "Amnesty International" in response.text
    assert "Dawn" in response.text
    assert "72 heatstroke admissions" in response.text
    # The two flagged-unverifiable numbers from docs/sources.md must never appear.
    assert "1,165" not in response.text
    assert "2,300" not in response.text


def test_gap_page_reflects_live_report_counts(report_store):
    report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
        )
    )
    report_store.add_or_increment(
        NewReport(
            zone_id="gulberg",
            lat=31.5085,
            lon=74.3505,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.death,
        )
    )

    response = client.get("/gap")
    assert "2" in response.text  # total_reports
    assert "heatstroke" in response.text.lower()
    assert "death" in response.text.lower()


def test_gap_dashboard_never_exposes_individual_report_detail(report_store):
    """The dashboard shows aggregate counts only — no per-report zone/lat/lon/id,
    matching the anonymous-by-design schema (RULES.md §7)."""
    report = report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
        )
    )
    response = client.get("/gap")
    assert report.id not in response.text
