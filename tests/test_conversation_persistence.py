"""Targets the real bug found 25 Aug 2026 (see PROGRESS.md): conversation state used
to live in a plain in-memory dict, which a Vercel cold start between two messages
would silently wipe, restarting an in-progress WhatsApp report from scratch. These
tests simulate that scenario directly — two separate store instances pointed at the
same backing file, standing in for two different serverless invocations that don't
share process memory but do share the persisted store.
"""

import json
from datetime import datetime, timedelta, timezone

from app.config import CONVERSATION_STATE_TTL_MINUTES
from app.models import GeoSource, WhatsAppConversationStage, WhatsAppConversationState
from app.storage.conversation_store import LocalJSONConversationStateStore


def test_state_set_by_one_process_is_visible_to_a_fresh_instance(tmp_path):
    path = tmp_path / "conversations.json"
    process_a = LocalJSONConversationStateStore(path=path)
    process_a.set(
        WhatsAppConversationState(phone="+92300", stage=WhatsAppConversationStage.awaiting_incident_type, zone_id="model_town")
    )

    # A brand-new store instance, same backing file — simulates a fresh cold-started
    # process handling the reporter's next message.
    process_b = LocalJSONConversationStateStore(path=path)
    state = process_b.get("+92300")

    assert state is not None
    assert state.stage is WhatsAppConversationStage.awaiting_incident_type
    assert state.zone_id == "model_town"


def test_full_flow_survives_a_simulated_cold_start_between_every_message(report_store, tmp_path, monkeypatch):
    """The actual regression test for the 25 Aug 2026 bug: drive the full guided flow
    through handle_incoming_message(), but hand back a *brand-new*
    LocalJSONConversationStateStore instance on every single call — nothing can
    survive via a warm process's memory here, only via what's actually on disk."""
    from app.services import whatsapp_flow

    calls = {"n": 0}
    shared_path = tmp_path / "conversations.json"

    def get_fresh_store():
        calls["n"] += 1
        return LocalJSONConversationStateStore(path=shared_path)

    monkeypatch.setattr("app.services.whatsapp_flow.get_conversation_store", get_fresh_store)

    reply = whatsapp_flow.handle_incoming_message("+92301", "hi")
    assert "share your location" in reply

    reply = whatsapp_flow.handle_incoming_message("+92301", "Model Town")
    assert "Model Town" in reply
    assert "What happened" in reply

    reply = whatsapp_flow.handle_incoming_message("+92301", "3")
    assert "Logged: model_town, death" in reply

    assert calls["n"] >= 3  # confirms a fresh store instance really was used each time
    assert len(report_store.list_since()) == 1


def test_stale_state_is_treated_as_a_new_conversation(tmp_path):
    store = LocalJSONConversationStateStore(path=tmp_path / "conversations.json")
    stale = WhatsAppConversationState(
        phone="+92302",
        stage=WhatsAppConversationStage.awaiting_incident_type,
        zone_id="gulberg",
        geo_source=GeoSource.zone_name,
    )
    stale.updated_at = datetime.now(timezone.utc) - timedelta(minutes=CONVERSATION_STATE_TTL_MINUTES + 1)
    # Bypass set()'s own timestamp stamping to write a genuinely stale row directly.
    rows = json.loads(store.path.read_text(encoding="utf-8"))
    rows[stale.phone] = json.loads(stale.model_dump_json())
    store.path.write_text(json.dumps(rows, default=str), encoding="utf-8")

    assert store.get("+92302") is None


def test_clear_removes_state(tmp_path):
    store = LocalJSONConversationStateStore(path=tmp_path / "conversations.json")
    store.set(WhatsAppConversationState(phone="+92303", stage=WhatsAppConversationStage.awaiting_location))
    assert store.get("+92303") is not None

    store.clear("+92303")
    assert store.get("+92303") is None
