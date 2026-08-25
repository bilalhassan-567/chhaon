import json
import threading
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from app.config import CONVERSATION_STATE_TTL_MINUTES, LOCAL_CONVERSATIONS_FILE
from app.models import WhatsAppConversationState
from app.storage.firestore_client import get_firestore_client

_lock = threading.Lock()


class ConversationStateStore(ABC):
    """Mid-flow WhatsApp conversation state, keyed by phone number. Separate from
    ReportStore/RegistrationStore because its lifecycle is different again: short-
    lived, fully overwritten on every message, and safe to drop once stale (see
    get()'s TTL) rather than needing to be retained."""

    @abstractmethod
    def get(self, phone: str) -> WhatsAppConversationState | None:
        """None if there's no in-progress conversation, or the one on file is older
        than CONVERSATION_STATE_TTL_MINUTES (treated the same as none, and cleared)."""

    @abstractmethod
    def set(self, state: WhatsAppConversationState) -> None:
        """Overwrites any existing state for this phone number. Stamps updated_at at
        write time, regardless of what the passed state's updated_at was."""

    @abstractmethod
    def clear(self, phone: str) -> None:
        """Ends the conversation (completed normally, or a STOP/ALERT ON reset)."""


def _is_stale(updated_at: datetime) -> bool:
    return datetime.now(timezone.utc) - updated_at > timedelta(minutes=CONVERSATION_STATE_TTL_MINUTES)


class LocalJSONConversationStateStore(ConversationStateStore):
    def __init__(self, path=LOCAL_CONVERSATIONS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict:
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, rows: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")

    def get(self, phone: str) -> WhatsAppConversationState | None:
        with _lock:
            rows = self._read()
            row = rows.get(phone)
            if row is None:
                return None
            state = WhatsAppConversationState(**row)
            if _is_stale(state.updated_at):
                rows.pop(phone, None)
                self._write(rows)
                return None
            return state

    def set(self, state: WhatsAppConversationState) -> None:
        with _lock:
            rows = self._read()
            state.updated_at = datetime.now(timezone.utc)
            rows[state.phone] = json.loads(state.model_dump_json())
            self._write(rows)

    def clear(self, phone: str) -> None:
        with _lock:
            rows = self._read()
            rows.pop(phone, None)
            self._write(rows)


class FirestoreConversationStateStore(ConversationStateStore):
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = self.db.collection("whatsapp_conversations")

    def get(self, phone: str) -> WhatsAppConversationState | None:
        doc = self.collection.document(phone).get()
        if not doc.exists:
            return None
        state = WhatsAppConversationState(**doc.to_dict())
        if _is_stale(state.updated_at):
            self.collection.document(phone).delete()
            return None
        return state

    def set(self, state: WhatsAppConversationState) -> None:
        state.updated_at = datetime.now(timezone.utc)
        self.collection.document(state.phone).set(json.loads(state.model_dump_json()))

    def clear(self, phone: str) -> None:
        self.collection.document(phone).delete()
