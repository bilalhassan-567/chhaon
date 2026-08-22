import pytest

from app.services.whatsapp_flow import _conversations
from app.storage.alert_state_store import LocalJSONAlertStateStore
from app.storage.local_store import LocalJSONReportStore
from app.storage.registration_store import LocalJSONRegistrationStore


@pytest.fixture(autouse=True)
def reset_conversations():
    """Conversation state is a module-level dict keyed by phone number — clear it
    between tests so one test's phone numbers can't bleed into another's."""
    _conversations.clear()
    yield
    _conversations.clear()


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
    routes/api), not at the storage factory, since both modules imported the name
    directly into their own namespace."""
    store = LocalJSONReportStore(path=tmp_path / "reports.json")
    monkeypatch.setattr("app.services.whatsapp_flow.get_store", lambda: store)
    monkeypatch.setattr("app.routes.api.get_store", lambda: store)
    monkeypatch.setattr("app.routes.gap.get_store", lambda: store)
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
