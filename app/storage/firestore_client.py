"""Shared Firebase app initialization for every Firestore-backed store. Idempotent —
firebase_admin errors if initialize_app() is called twice, so every store checks
firebase_admin._apps first rather than each managing its own init flag.
"""

import json

from app.config import FIREBASE_CREDENTIALS_JSON, FIREBASE_CREDENTIALS_PATH


def get_firestore_client():
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not firebase_admin._apps:
        if FIREBASE_CREDENTIALS_JSON:
            # CI path: the service-account key as a single secret string, since GitHub
            # Actions secrets can't mount a file directly.
            cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS_JSON))
        elif FIREBASE_CREDENTIALS_PATH:
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
        else:
            raise RuntimeError(
                "Neither FIREBASE_CREDENTIALS_JSON nor FIREBASE_CREDENTIALS_PATH is "
                "set — the Firestore project has not been created yet. See "
                "docs/master-workout/PROGRESS.md for the outstanding account signup."
            )
        firebase_admin.initialize_app(cred)

    return firestore.client()
