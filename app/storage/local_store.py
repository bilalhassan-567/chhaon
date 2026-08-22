import json
import threading
import uuid
from datetime import datetime, timedelta, timezone

from app.config import DEDUP_RADIUS_METERS, DEDUP_WINDOW_MINUTES, LOCAL_REPORTS_FILE
from app.models import NewReport, Report
from app.services.geo import haversine_meters
from app.storage.base import ReportStore

_lock = threading.Lock()


class LocalJSONReportStore(ReportStore):
    """Dev/demo backend — no Firebase account required. Same interface as the
    Firestore backend, so this is a drop-in until Day 2's real account exists."""

    def __init__(self, path=LOCAL_REPORTS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        if not self.path.exists():
            # Self-heals if the backing file is deleted out from under a running
            # process (e.g. manual cleanup during dev) — a fresh empty store is the
            # correct recovery, not a crash.
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[]", encoding="utf-8")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    def add_or_increment(self, new_report: NewReport) -> Report:
        with _lock:
            rows = self._read()
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)

            for row in rows:
                if row["zone_id"] != new_report.zone_id:
                    continue
                if row["incident_type"] != new_report.incident_type.value:
                    continue
                row_ts = datetime.fromisoformat(row["timestamp"])
                if row_ts < window_start:
                    continue
                if new_report.lat is not None and row.get("lat") is not None:
                    distance = haversine_meters(new_report.lat, new_report.lon, row["lat"], row["lon"])
                    if distance > DEDUP_RADIUS_METERS:
                        continue
                # Match: same zone + incident type within the window (and within
                # radius, if both have coordinates) — bump the count instead of
                # writing a duplicate.
                row["report_count"] += 1
                self._write(rows)
                return Report(**row)

            report = Report(
                id=str(uuid.uuid4()),
                zone_id=new_report.zone_id,
                lat=new_report.lat,
                lon=new_report.lon,
                geo_source=new_report.geo_source,
                incident_type=new_report.incident_type,
                timestamp=now,
            )
            rows.append(json.loads(report.model_dump_json()))
            self._write(rows)
            return report

    def list_since(self, since: datetime | None = None) -> list[Report]:
        rows = self._read()
        reports = [Report(**row) for row in rows]
        if since is None:
            return reports
        return [r for r in reports if r.timestamp >= since]
