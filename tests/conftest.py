import pytest

from app.storage.alert_state_store import LocalJSONAlertStateStore
from app.storage.conversation_store import LocalJSONConversationStateStore
from app.storage.local_store import LocalJSONReportStore
from app.storage.push_subscription_store import LocalJSONPushSubscriptionStore
from app.storage.registration_store import LocalJSONRegistrationStore


@pytest.fixture(autouse=True)
def conversation_store(tmp_path, monkeypatch):
    """Conversation state is now a persisted store (see conversation_store.py's
    docstring for why) — isolate it per test the same way every other store is,
    patched at the point of use, so one test's phone numbers can't bleed into
    another's and no test depends on real local/Firestore conversation data."""
    store = LocalJSONConversationStateStore(path=tmp_path / "conversations.json")
    monkeypatch.setattr("app.services.whatsapp_flow.get_conversation_store", lambda: store)
    return store


@pytest.fixture(autouse=True)
def block_real_whatsapp_sends(monkeypatch):
    """The intake route and the alert checker both call send_message() for real.
    Tests must never depend on — or be affected by — whatever's in the developer's
    actual .env; without this, the moment a real WHATSAPP_ACCESS_TOKEN is configured
    locally, every test run would start sending real WhatsApp messages and burning
    real API quota. Records calls instead of sending; tests that care about what was
    "sent" read `sent_whatsapp_messages` via the same list object.
    """
    sent = []

    def fake_send_message(to: str, body: str) -> bool:
        sent.append({"to": to, "body": body})
        return True

    monkeypatch.setattr("app.routes.intake.send_message", fake_send_message)
    monkeypatch.setattr("ingestion.alert_check.send_message", fake_send_message)
    return sent


@pytest.fixture(autouse=True)
def block_real_web_push_sends(monkeypatch):
    """Same reasoning as block_real_whatsapp_sends, for the Web Push channel: once
    real VAPID keys are configured locally, tests must not attempt real pushes."""
    sent = []

    def fake_send_push_notification(subscription, title: str, body: str) -> bool:
        sent.append({"endpoint": subscription.endpoint, "title": title, "body": body})
        return True

    monkeypatch.setattr("ingestion.alert_check.send_push_notification", fake_send_push_notification)
    return sent


@pytest.fixture(autouse=True)
def isolate_whatsapp_secrets(monkeypatch):
    """Tests must not depend on whatever's actually in the developer's .env — once a
    real WHATSAPP_APP_SECRET is configured locally (as it now is), every test that
    posts an unsigned request to the webhook would otherwise start failing with 403,
    not because the code is wrong but because ambient config leaked into the test.
    Default posture for all tests: no secret configured (signature check skipped,
    dev-mode bypass) — tests that specifically want to exercise the configured-secret
    path (see test_intake_security.py) explicitly set their own value, which overrides
    this."""
    monkeypatch.setattr("app.services.whatsapp_api.WHATSAPP_APP_SECRET", "")
    monkeypatch.setattr("app.routes.intake.WHATSAPP_VERIFY_TOKEN", "")


@pytest.fixture
def report_store(tmp_path, monkeypatch):
    """An isolated LocalJSONReportStore backed by a tmp file, wired in wherever
    `get_store()` is called from — patched at the point of use (whatsapp_flow,
    routes/api, routes/report), not at the storage factory, since each module
    imported the name directly into its own namespace."""
    store = LocalJSONReportStore(path=tmp_path / "reports.json")
    monkeypatch.setattr("app.services.whatsapp_flow.get_store", lambda: store)
    monkeypatch.setattr("app.routes.api.get_store", lambda: store)
    monkeypatch.setattr("app.routes.gap.get_store", lambda: store)
    monkeypatch.setattr("app.routes.report.get_store", lambda: store)
    return store


@pytest.fixture
def registration_store(tmp_path, monkeypatch):
    """Isolated RegistrationStore, patched wherever get_registration_store() is
    called from (same "patch at point of use" reasoning as report_store)."""
    store = LocalJSONRegistrationStore(path=tmp_path / "registrations.json")
    monkeypatch.setattr("app.services.whatsapp_flow.get_registration_store", lambda: store)
    return store


@pytest.fixture
def alert_state_store(tmp_path):
    return LocalJSONAlertStateStore(path=tmp_path / "alert_state.json")


@pytest.fixture
def push_subscription_store(tmp_path, monkeypatch):
    """Isolated PushSubscriptionStore, patched wherever get_push_subscription_store()
    is called from (same "patch at point of use" reasoning as report_store)."""
    store = LocalJSONPushSubscriptionStore(path=tmp_path / "push_subscriptions.json")
    monkeypatch.setattr("app.routes.push.get_push_subscription_store", lambda: store)
    monkeypatch.setattr("ingestion.alert_check.get_push_subscription_store", lambda: store)
    return store
