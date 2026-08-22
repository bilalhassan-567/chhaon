import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime

from app.config import LOCAL_ALERT_STATE_FILE
from app.storage.firestore_client import get_firestore_client

_lock = threading.Lock()


class AlertStateStore(ABC):
    """Tracks the last time an alert was sent for a zone, so the threshold checker
    (run repeatedly by a cron job) doesn't re-alert the same zone every run while
    conditions stay dangerous — see ALERT_COOLDOWN_HOURS."""

    @abstractmethod
    def last_alert_at(self, zone_id: str) -> datetime | None: ...

    @abstractmethod
    def record_alert_sent(self, zone_id: str, at: datetime) -> None: ...


class LocalJSONAlertStateStore(AlertStateStore):
    def __init__(self, path=LOCAL_ALERT_STATE_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def last_alert_at(self, zone_id: str) -> datetime | None:
        raw = self._read().get(zone_id)
        return datetime.fromisoformat(raw) if raw else None

    def record_alert_sent(self, zone_id: str, at: datetime) -> None:
        with _lock:
            data = self._read()
            data[zone_id] = at.isoformat()
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class FirestoreAlertStateStore(AlertStateStore):
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection("alert_state")

    def last_alert_at(self, zone_id: str) -> datetime | None:
        doc = self.collection.document(zone_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()["last_alert_at"]

    def record_alert_sent(self, zone_id: str, at: datetime) -> None:
        self.collection.document(zone_id).set({"last_alert_at": at})
