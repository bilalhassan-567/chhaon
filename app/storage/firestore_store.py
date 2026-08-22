"""Production backend — Firebase Firestore (Spark/free plan, see PLAN.md's stack table).

Implements the same ReportStore interface as LocalJSONReportStore, so
STORAGE_BACKEND=firestore in .env is the only change needed to switch; no route or
template code depends on which backend is active.

Query design note: dedup matching filters on zone_id + incident_type (both equality —
Firestore handles multiple equality filters without needing a manual composite index)
and then filters the *time window* and *radius* in Python rather than in the Firestore
query itself. Adding timestamp as a third (range) filter alongside two equality filters
would require a composite index to be created in the Firebase console before the query
works at all — a real deployment-day surprise easy to hit by accident. Report volume
per zone+type at hackathon-demo scale is small enough that fetching the equality-matched
set and filtering in Python is simple, correct, and avoids that entirely.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.config import DEDUP_RADIUS_METERS, DEDUP_WINDOW_MINUTES
from app.models import GeoSource, IncidentType, NewReport, Report
from app.services.geo import haversine_meters
from app.storage.base import ReportStore
from app.storage.firestore_client import get_firestore_client


def _report_to_doc(report: Report) -> dict:
    return {
        "id": report.id,
        "zone_id": report.zone_id,
        "lat": report.lat,
        "lon": report.lon,
        "geo_source": report.geo_source.value,
        "incident_type": report.incident_type.value,
        "timestamp": report.timestamp,
        "source": report.source,
        "report_count": report.report_count,
    }


def _doc_to_report(data: dict) -> Report:
    return Report(
        id=data["id"],
        zone_id=data["zone_id"],
        lat=data.get("lat"),
        lon=data.get("lon"),
        geo_source=GeoSource(data["geo_source"]),
        incident_type=IncidentType(data["incident_type"]),
        timestamp=data["timestamp"],
        source=data.get("source", "whatsapp"),
        report_count=data.get("report_count", 1),
    )


class FirestoreReportStore(ReportStore):
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection("reports")

    def add_or_increment(self, new_report: NewReport) -> Report:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=DEDUP_WINDOW_MINUTES)

        query = self.collection.where("zone_id", "==", new_report.zone_id).where(
            "incident_type", "==", new_report.incident_type.value
        )
        for doc in query.stream():
            row = doc.to_dict()
            row_ts = row["timestamp"]
            if row_ts < window_start:
                continue
            if new_report.lat is not None and row.get("lat") is not None:
                distance = haversine_meters(new_report.lat, new_report.lon, row["lat"], row["lon"])
                if distance > DEDUP_RADIUS_METERS:
                    continue
            new_count = row["report_count"] + 1
            doc.reference.update({"report_count": new_count})
            row["report_count"] = new_count
            return _doc_to_report(row)

        report = Report(
            id=str(uuid.uuid4()),
            zone_id=new_report.zone_id,
            lat=new_report.lat,
            lon=new_report.lon,
            geo_source=new_report.geo_source,
            incident_type=new_report.incident_type,
            source=new_report.source,
            timestamp=now,
        )
        self.collection.document(report.id).set(_report_to_doc(report))
        return report

    def list_since(self, since: datetime | None = None) -> list[Report]:
        query = self.collection
        if since is not None:
            query = query.where("timestamp", ">=", since)
        return [_doc_to_report(doc.to_dict()) for doc in query.stream()]
