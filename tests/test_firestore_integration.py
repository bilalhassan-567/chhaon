"""Real integration tests against the live Firestore project — not mocked, not the
local JSON store. Opt-in: skipped automatically when no Firebase credentials are
configured (e.g. in CI, unless FIREBASE_CREDENTIALS_JSON secret is set), so the main
suite stays fast and hermetic while this still gives real coverage against the actual
database when run locally.

Every test uses a uniquely-prefixed zone_id/phone so runs never collide with each
other or with real demo data, and cleans up everything it writes.
"""

import uuid
from datetime import datetime, timezone

import pytest

from app.config import FIREBASE_CREDENTIALS_JSON, FIREBASE_CREDENTIALS_PATH
from app.models import GeoSource, IncidentType, NewReport, PushSubscription

pytestmark = pytest.mark.skipif(
    not (FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON),
    reason="No Firebase credentials configured — set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON to run these.",
)


@pytest.fixture
def test_zone_id():
    return f"_test_zone_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_phone():
    return f"_test_phone_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def report_store():
    from app.storage.firestore_store import FirestoreReportStore

    store = FirestoreReportStore()
    yield store


@pytest.fixture
def registration_store():
    from app.storage.registration_store import FirestoreRegistrationStore

    store = FirestoreRegistrationStore()
    yield store


@pytest.fixture
def alert_state_store():
    from app.storage.alert_state_store import FirestoreAlertStateStore

    store = FirestoreAlertStateStore()
    yield store


@pytest.fixture
def push_subscription_store():
    from app.storage.push_subscription_store import FirestorePushSubscriptionStore

    store = FirestorePushSubscriptionStore()
    yield store


def test_report_store_add_and_list(report_store, test_zone_id):
    report = report_store.add_or_increment(
        NewReport(zone_id=test_zone_id, geo_source=GeoSource.zone_name, incident_type=IncidentType.heatstroke)
    )
    try:
        assert report.report_count == 1
        matching = [r for r in report_store.list_since() if r.zone_id == test_zone_id]
        assert len(matching) == 1
    finally:
        report_store.collection.document(report.id).delete()


def test_report_store_dedup_increments_in_real_firestore(report_store, test_zone_id):
    first = report_store.add_or_increment(
        NewReport(
            zone_id=test_zone_id,
            lat=31.48,
            lon=74.32,
            geo_source=GeoSource.location_pin,
            incident_type=IncidentType.heatstroke,
        )
    )
    try:
        second = report_store.add_or_increment(
            NewReport(
                zone_id=test_zone_id,
                lat=31.4801,
                lon=74.3201,
                geo_source=GeoSource.location_pin,
                incident_type=IncidentType.heatstroke,
            )
        )
        assert second.id == first.id
        assert second.report_count == 2
    finally:
        report_store.collection.document(first.id).delete()


def test_registration_store_round_trip(registration_store, test_zone_id, test_phone):
    registration_store.register(test_phone, test_zone_id)
    try:
        assert registration_store.list_for_zone(test_zone_id) == [test_phone]
        assert test_zone_id in registration_store.zones_with_registrations()
    finally:
        registration_store.unregister_all(test_phone)
    assert registration_store.list_for_zone(test_zone_id) == []


def test_alert_state_store_round_trip(alert_state_store, test_zone_id):
    assert alert_state_store.last_alert_at(test_zone_id) is None

    now = datetime.now(timezone.utc)
    alert_state_store.record_alert_sent(test_zone_id, now)
    try:
        retrieved = alert_state_store.last_alert_at(test_zone_id)
        assert abs((retrieved - now).total_seconds()) < 5
    finally:
        alert_state_store.collection.document(test_zone_id).delete()


def test_push_subscription_store_round_trip(push_subscription_store, test_zone_id):
    endpoint = f"https://_test_endpoint_{test_zone_id}"
    push_subscription_store.subscribe(
        PushSubscription(endpoint=endpoint, p256dh="test_p256dh", auth="test_auth", zone_id=test_zone_id)
    )
    try:
        subs = push_subscription_store.list_for_zone(test_zone_id)
        assert len(subs) == 1
        assert subs[0].endpoint == endpoint
        assert test_zone_id in push_subscription_store.zones_with_subscriptions()
    finally:
        push_subscription_store.unsubscribe(endpoint)
    assert push_subscription_store.list_for_zone(test_zone_id) == []
