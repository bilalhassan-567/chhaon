"""Sends a Web Push notification (RFC 8292 VAPID) to a single browser subscription.

The WhatsApp-independent half of the outbound alert path — app/services/whatsapp_api.py
is the other. Both are called from ingestion/alert_check.py for the same threshold
event; a zone crossing the danger threshold notifies everyone registered for it on
whichever channel(s) they opted into.
"""

import json

from pywebpush import WebPushException, webpush

from app.config import VAPID_CLAIMS_EMAIL, VAPID_PRIVATE_KEY
from app.models import PushSubscription


def send_push_notification(subscription: PushSubscription, title: str, body: str) -> bool:
    """Returns False on any failure (including an expired/revoked subscription)
    rather than raising — matches send_message()'s contract in whatsapp_api.py, so
    ingestion/alert_check.py can treat both channels the same way: one failed
    recipient must never block the rest of the batch."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps({"title": title, "body": body}),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
        )
        return True
    except WebPushException:
        return False
