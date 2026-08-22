import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.config import LOCAL_PUSH_SUBSCRIPTIONS_FILE
from app.models import PushSubscription
from app.storage.firestore_client import get_firestore_client

_lock = threading.Lock()


class PushSubscriptionStore(ABC):
    """Web Push subscription storage — the WhatsApp-independent analog of
    RegistrationStore. Kept in its own collection/file for the same reason
    registrations are separate from reports: different data, different lifecycle
    (a subscription can go stale/be revoked by the browser at any time, unlike a
    phone number)."""

    @abstractmethod
    def subscribe(self, subscription: PushSubscription) -> None:
        """Idempotent: re-subscribing the same endpoint+zone is a no-op update."""

    @abstractmethod
    def unsubscribe(self, endpoint: str) -> None:
        """Remove every registration for this push endpoint (e.g. the user clicked
        'disable alerts', or the browser reports the subscription as expired)."""

    @abstractmethod
    def list_for_zone(self, zone_id: str) -> list[PushSubscription]:
        """Subscriptions registered for a zone. Internal use only (alert dispatch)."""

    @abstractmethod
    def zones_with_subscriptions(self) -> set[str]:
        """Which zones have at least one push subscription."""


class LocalJSONPushSubscriptionStore(PushSubscriptionStore):
    def __init__(self, path=LOCAL_PUSH_SUBSCRIPTIONS_FILE):
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

    def subscribe(self, subscription: PushSubscription) -> None:
        with _lock:
            rows = [r for r in self._read() if r["endpoint"] != subscription.endpoint]
            rows.append(json.loads(subscription.model_dump_json()))
            self._write(rows)

    def unsubscribe(self, endpoint: str) -> None:
        with _lock:
            rows = [r for r in self._read() if r["endpoint"] != endpoint]
            self._write(rows)

    def list_for_zone(self, zone_id: str) -> list[PushSubscription]:
        return [PushSubscription(**r) for r in self._read() if r["zone_id"] == zone_id]

    def zones_with_subscriptions(self) -> set[str]:
        return {r["zone_id"] for r in self._read()}


class FirestorePushSubscriptionStore(PushSubscriptionStore):
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection("push_subscriptions")

    def _doc_id(self, endpoint: str) -> str:
        # Endpoints are long URLs with characters Firestore doc IDs can't always take
        # cleanly (and can exceed length limits) — hash instead of using it raw.
        import hashlib

        return hashlib.sha256(endpoint.encode()).hexdigest()

    def subscribe(self, subscription: PushSubscription) -> None:
        self.collection.document(self._doc_id(subscription.endpoint)).set(
            {
                "endpoint": subscription.endpoint,
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
                "zone_id": subscription.zone_id,
                "registered_at": datetime.now(timezone.utc),
            }
        )

    def unsubscribe(self, endpoint: str) -> None:
        self.collection.document(self._doc_id(endpoint)).delete()

    def list_for_zone(self, zone_id: str) -> list[PushSubscription]:
        return [
            PushSubscription(**doc.to_dict())
            for doc in self.collection.where("zone_id", "==", zone_id).stream()
        ]

    def zones_with_subscriptions(self) -> set[str]:
        return {doc.to_dict()["zone_id"] for doc in self.collection.stream()}
