"""Regression coverage for a real bug: a long-running process's store crashed with
FileNotFoundError if its backing JSON file was deleted out from under it (discovered
when the dev server's local data file was cleaned up between test sessions while the
server was still running). Every local store must self-heal instead of crashing."""

from app.models import GeoSource, IncidentType, NewReport
from app.storage.alert_state_store import LocalJSONAlertStateStore
from app.storage.local_store import LocalJSONReportStore
from app.storage.registration_store import LocalJSONRegistrationStore


def test_report_store_recovers_if_file_deleted_after_init(tmp_path):
    path = tmp_path / "reports.json"
    store = LocalJSONReportStore(path=path)
    path.unlink()  # simulate the file disappearing while the process is still alive

    report = store.add_or_increment(
        NewReport(zone_id="model_town", geo_source=GeoSource.zone_name, incident_type=IncidentType.heatstroke)
    )

    assert report.report_count == 1
    assert path.exists()


def test_report_store_recovers_if_directory_deleted(tmp_path):
    subdir = tmp_path / "nested"
    path = subdir / "reports.json"
    store = LocalJSONReportStore(path=path)
    import shutil

    shutil.rmtree(subdir)

    reports = store.list_since()  # must not raise

    assert reports == []
    assert path.exists()


def test_registration_store_recovers_if_file_deleted(tmp_path):
    path = tmp_path / "registrations.json"
    store = LocalJSONRegistrationStore(path=path)
    path.unlink()

    store.register("whatsapp:+923000000001", "model_town")

    assert store.list_for_zone("model_town") == ["whatsapp:+923000000001"]


def test_alert_state_store_recovers_if_file_deleted(tmp_path):
    from datetime import datetime, timezone

    path = tmp_path / "alert_state.json"
    store = LocalJSONAlertStateStore(path=path)
    path.unlink()

    assert store.last_alert_at("model_town") is None  # must not raise

    store.record_alert_sent("model_town", datetime.now(timezone.utc))
    assert store.last_alert_at("model_town") is not None
