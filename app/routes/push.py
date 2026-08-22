from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import VAPID_PUBLIC_KEY
from app.models import PushSubscription
from app.services.zones import load_zones
from app.storage import get_push_subscription_store

router = APIRouter()


@router.get("/api/push/vapid-public-key")
def vapid_public_key():
    """The public half of the VAPID keypair — safe to expose to any browser, it's
    exactly what PushManager.subscribe() needs as applicationServerKey."""
    return {"publicKey": VAPID_PUBLIC_KEY}


class SubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str
    zone_id: str


@router.post("/api/push/subscribe")
def subscribe(req: SubscribeRequest):
    """Unlike WhatsApp alert registration, this genuinely can be an open endpoint
    without RULES.md §9's phone-number-abuse concern — a push subscription's
    endpoint/keys are issued by the browser's own push service only to whichever
    page called PushManager.subscribe(), so there's no way to register a stranger's
    browser through this form the way an open phone-number field could be abused."""
    zone_ids = {z.id for z in load_zones()}
    if req.zone_id not in zone_ids:
        raise HTTPException(status_code=400, detail="Unknown zone_id.")

    get_push_subscription_store().subscribe(
        PushSubscription(endpoint=req.endpoint, p256dh=req.p256dh, auth=req.auth, zone_id=req.zone_id)
    )
    return {"status": "ok"}


class UnsubscribeRequest(BaseModel):
    endpoint: str


@router.post("/api/push/unsubscribe")
def unsubscribe(req: UnsubscribeRequest):
    get_push_subscription_store().unsubscribe(req.endpoint)
    return {"status": "ok"}
