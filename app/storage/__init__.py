from functools import lru_cache

from app.config import STORAGE_BACKEND
from app.storage.alert_state_store import AlertStateStore
from app.storage.base import ReportStore
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
