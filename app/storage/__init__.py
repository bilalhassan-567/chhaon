from functools import lru_cache

from app.config import STORAGE_BACKEND
from app.storage.alert_state_store import AlertStateStore
from app.storage.base import ReportStore
from app.storage.conversation_store import ConversationStateStore
from app.storage.push_subscription_store import PushSubscriptionStore
from app.storage.registration_store import RegistrationStore


@lru_cache
def get_store() -> ReportStore:
    if STORAGE_BACKEND == "firestore":
        from app.storage.firestore_store import FirestoreReportStore

        return FirestoreReportStore()

    from app.storage.local_store import LocalJSONReportStore

    return LocalJSONReportStore()


@lru_cache
def get_registration_store() -> RegistrationStore:
    if STORAGE_BACKEND == "firestore":
        from app.storage.registration_store import FirestoreRegistrationStore

        return FirestoreRegistrationStore()

    from app.storage.registration_store import LocalJSONRegistrationStore

    return LocalJSONRegistrationStore()


@lru_cache
def get_alert_state_store() -> AlertStateStore:
    if STORAGE_BACKEND == "firestore":
        from app.storage.alert_state_store import FirestoreAlertStateStore

        return FirestoreAlertStateStore()

    from app.storage.alert_state_store import LocalJSONAlertStateStore

    return LocalJSONAlertStateStore()


@lru_cache
def get_push_subscription_store() -> PushSubscriptionStore:
    if STORAGE_BACKEND == "firestore":
        from app.storage.push_subscription_store import FirestorePushSubscriptionStore

        return FirestorePushSubscriptionStore()

    from app.storage.push_subscription_store import LocalJSONPushSubscriptionStore

    return LocalJSONPushSubscriptionStore()


@lru_cache
def get_conversation_store() -> ConversationStateStore:
    if STORAGE_BACKEND == "firestore":
        from app.storage.conversation_store import FirestoreConversationStateStore

        return FirestoreConversationStateStore()

    from app.storage.conversation_store import LocalJSONConversationStateStore

    return LocalJSONConversationStateStore()
