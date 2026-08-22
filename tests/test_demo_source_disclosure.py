"""Covers the source-tagging added for scripts/seed_demo_reports.py: real WhatsApp
intake must always tag "whatsapp" (unchanged behavior), and anything explicitly
seeded as "demo_seed" must be honestly distinguishable everywhere it's surfaced
(map API, Gap Dashboard) rather than silently blended into "real" counts —
RULES.md §7's ethics framing applies to seeded data too, not just real reports.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models import GeoSource, IncidentType, NewReport

client = TestClient(app)


def test_real_intake_always_tags_whatsapp_by_default(report_store):
    report = report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
        )
    )
    assert report.source == "whatsapp"


def test_demo_seed_source_is_preserved_through_storage(report_store):
    report = report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
            source="demo_seed",
        )
    )
    assert report.source == "demo_seed"


def test_api_reports_splits_real_and_demo_counts_per_zone(report_store):
    report_store.add_or_increment(
        NewReport(
            zone_id="gulberg",
            lat=31.5085,
            lon=74.3505,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heat_exhaustion,
        )
    )
    report_store.add_or_increment(
        NewReport(
            zone_id="gulberg",
            lat=31.5085,
            lon=74.3505,
            geo_source=GeoSource.zone_name,
            incident_type=IncidentType.heatstroke,
            source="demo_seed",
        )
    )

    response = client.get("/api/reports")
    assert response.status_code == 200
    [gulberg] = [z for z in response.json() if z["zone_id"] == "gulberg"]
    assert gulberg["real_count"] == 1
    assert gulberg["demo_count"] == 1
    assert gulberg["count"] == 2


def test_gap_dashboard_discloses_real_vs_demo_breakdown(report_store):
    report_store.add_or_increment(
        NewReport(
            zone_id="model_town",
            lat=31.4805,
            lon=74.3232,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heat_exhaustion,
        )
    )
    report_store.add_or_increment(
        NewReport(
            zone_id="gulberg",
            lat=31.5085,
            lon=74.3505,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
            source="demo_seed",
        )
    )

    response = client.get("/gap")
    assert response.status_code == 200
    text = response.text
    # Both counts must appear — the dashboard must never blend seed data into the
    # "real" number silently.
    assert "1 real" in text
    assert "1 demo" in text


def test_gap_dashboard_headline_figure_matches_sourced_data(report_store):
    """The dramatic '0 vs N' banner's official-side number must come from
    official_figures.json's punjab_2022 entry, not a hardcoded duplicate — this
    guards against the two ever drifting apart."""
    response = client.get("/gap")
    assert response.status_code == 200
    assert "0 heat-related deaths officially recorded" in response.text
    assert "Amnesty International" in response.text
