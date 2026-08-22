import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.config import LOCAL_REGISTRATIONS_FILE
from app.models import AlertRegistration
from app.storage.firestore_client import get_firestore_client

_lock = threading.Lock()


class RegistrationStore(ABC):
    """Alert-registration storage. Deliberately separate from ReportStore: this data
    holds real phone numbers (necessary to send an alert) so it has a different
    security profile than the anonymous report data — never exposed via any API,
    never joined with report data, written to a separate collection/file."""

    @abstractmethod
    def register(self, phone: str, zone_id: str) -> None:
        """Idempotent: registering the same phone+zone twice is a no-op."""

    @abstractmethod
    def unregister_all(self, phone: str) -> None:
        """STOP/ALERT OFF — remove every registration for this phone number."""

    @abstractmethod
    def list_for_zone(self, zone_id: str) -> list[str]:
        """Phone numbers registered for a zone. Internal use only (alert dispatch) —
        never returned from an HTTP endpoint."""

    @abstractmethod
    def zones_with_registrations(self) -> set[str]:
        """Which zones have at least one registration — lets the threshold checker
        skip an Open-Meteo call for zones nobody is listening for."""


class LocalJSONRegistrationStore(RegistrationStore):
    def __init__(self, path=LOCAL_REGISTRATIONS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("[]", encoding="utf-8")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    def register(self, phone: str, zone_id: str) -> None:
        with _lock:
            rows = self._read()
            if any(r["phone"] == phone and r["zone_id"] == zone_id for r in rows):
                return
            reg = AlertRegistration(phone=phone, zone_id=zone_id)
            rows.append(json.loads(reg.model_dump_json()))
            self._write(rows)

    def unregister_all(self, phone: str) -> None:
        with _lock:
            rows = [r for r in self._read() if r["phone"] != phone]
            self._write(rows)

    def list_for_zone(self, zone_id: str) -> list[str]:
        return [r["phone"] for r in self._read() if r["zone_id"] == zone_id]

    def zones_with_registrations(self) -> set[str]:
        return {r["zone_id"] for r in self._read()}


class FirestoreRegistrationStore(RegistrationStore):
    """Same interface as the local store, backed by a separate `registrations`
    collection — kept apart from `reports` since this is the one place a real phone
    number is stored (see the class docstring above)."""

    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection("registrations")

    def _doc_id(self, phone: str, zone_id: str) -> str:
        # Deterministic id from (phone, zone_id) makes register() naturally
        # idempotent via set() — no read-before-write needed.
        return f"{phone}__{zone_id}"

    def register(self, phone: str, zone_id: str) -> None:
        self.collection.document(self._doc_id(phone, zone_id)).set(
            {"phone": phone, "zone_id": zone_id, "registered_at": datetime.now(timezone.utc)}
        )

    def unregister_all(self, phone: str) -> None:
        for doc in self.collection.where("phone", "==", phone).stream():
            doc.reference.delete()

    def list_for_zone(self, zone_id: str) -> list[str]:
        return [doc.to_dict()["phone"] for doc in self.collection.where("zone_id", "==", zone_id).stream()]

    def zones_with_registrations(self) -> set[str]:
        return {doc.to_dict()["zone_id"] for doc in self.collection.stream()}
