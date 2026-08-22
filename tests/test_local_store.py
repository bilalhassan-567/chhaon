import json
from datetime import datetime, timedelta, timezone

from app.models import GeoSource, IncidentType, NewReport
from app.storage.local_store import LocalJSONReportStore


def make_store(tmp_path):
    return LocalJSONReportStore(path=tmp_path / "reports.json")


def make_report(**overrides):
    defaults = dict(
        zone_id="model_town",
        lat=31.4805,
        lon=74.3232,
        geo_source=GeoSource.location_pin,
        incident_type=IncidentType.heatstroke,
    )
    defaults.update(overrides)
    return NewReport(**defaults)


def test_first_report_is_created_with_count_one(tmp_path):
    store = make_store(tmp_path)
    report = store.add_or_increment(make_report())
    assert report.report_count == 1
    assert len(store.list_since()) == 1


def test_duplicate_same_zone_type_and_location_increments(tmp_path):
    store = make_store(tmp_path)
    first = store.add_or_increment(make_report())
    second = store.add_or_increment(make_report(lat=31.4810, lon=74.3235))  # a few metres away

    assert second.id == first.id
    assert second.report_count == 2
    assert len(store.list_since()) == 1


def test_different_incident_type_is_a_separate_report(tmp_path):
    store = make_store(tmp_path)
    store.add_or_increment(make_report(incident_type=IncidentType.heatstroke))
    store.add_or_increment(make_report(incident_type=IncidentType.death))

    assert len(store.list_since()) == 2


def test_far_away_report_is_not_merged(tmp_path):
    store = make_store(tmp_path)
    store.add_or_increment(make_report(lat=31.4805, lon=74.3232))
    # Walled City-ish coordinates — well outside the dedup radius.
    far = store.add_or_increment(make_report(lat=31.5820, lon=74.3300))

    assert far.report_count == 1
    assert len(store.list_since()) == 2


def test_zone_name_fallback_report_has_no_coordinates(tmp_path):
    store = make_store(tmp_path)
    report = store.add_or_increment(
        make_report(lat=None, lon=None, geo_source=GeoSource.zone_name)
    )
    assert report.lat is None
    assert report.geo_source == GeoSource.zone_name


def test_stale_report_outside_dedup_window_is_not_merged(tmp_path):
    store = make_store(tmp_path)
    stale_timestamp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    store.path.write_text(
        json.dumps(
            [
                {
                    "zone_id": "model_town",
                    "lat": 31.4805,
                    "lon": 74.3232,
                    "geo_source": "location_pin",
                    "incident_type": "heatstroke",
                    "id": "old-report",
                    "timestamp": stale_timestamp,
                    "source": "whatsapp",
                    "report_count": 1,
                }
            ]
        ),
        encoding="utf-8",
    )

    fresh = store.add_or_increment(make_report())

    assert fresh.id != "old-report"
    assert len(store.list_since()) == 2


def test_list_since_filters_by_timestamp(tmp_path):
    store = make_store(tmp_path)
    store.add_or_increment(make_report())
    cutoff = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert store.list_since(cutoff) == []
    assert len(store.list_since(cutoff - timedelta(minutes=2))) == 1


def test_counts_by_zone_sums_report_count_not_row_count(tmp_path):
    store = make_store(tmp_path)
    store.add_or_increment(make_report())
    store.add_or_increment(make_report(lat=31.4806, lon=74.3233))  # merges into the same row
    store.add_or_increment(make_report(zone_id="gulberg", lat=31.5085, lon=74.3505))

    counts = store.counts_by_zone()
    assert counts == {"model_town": 2, "gulberg": 1}
