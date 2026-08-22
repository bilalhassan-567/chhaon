from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import INTAKE_RATE_LIMIT_MAX_MESSAGES, INTAKE_RATE_LIMIT_WINDOW_MINUTES, WHATSAPP_VERIFY_TOKEN
from app.services.rate_limit import RateLimiter
from app.services.whatsapp_api import parse_incoming_messages, send_message, verify_webhook_signature
from app.services.whatsapp_flow import handle_incoming_message

router = APIRouter()

_rate_limiter = RateLimiter(
    max_events=INTAKE_RATE_LIMIT_MAX_MESSAGES,
    window_seconds=INTAKE_RATE_LIMIT_WINDOW_MINUTES * 60,
)


async def require_valid_whatsapp_signature(request: Request) -> None:
    if not await verify_webhook_signature(request):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")


@router.get("/webhooks/whatsapp")
def whatsapp_webhook_verification(
    hub_mode: str = Query("", alias="hub.mode"),
    hub_verify_token: str = Query("", alias="hub.verify_token"),
    hub_challenge: str = Query("", alias="hub.challenge"),
):
    """Meta's one-time handshake: before it will send real message webhooks, it GETs
    this URL with a token we chose (WHATSAPP_VERIFY_TOKEN, entered in the Meta App
    Dashboard's webhook config) and expects the challenge echoed back verbatim if the
    token matches — proves we control the endpoint, not that any given request is
    genuinely from Meta (that's what the POST route's signature check is for)."""
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN and WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/webhooks/whatsapp", dependencies=[Depends(require_valid_whatsapp_signature)])
async def whatsapp_webhook_message(request: Request):
    """Meta's inbound message webhook: nested JSON, not form-encoded. Verified against
    Meta's documented payload shape via direct POSTs in tests/test_routes.py; a real
    Meta app (the Day 1 setup) is needed to confirm actual delivery, but the handler
    logic itself is fully exercised without depending on live traffic.

    Security: `require_valid_whatsapp_signature` rejects any request not validly
    signed by Meta once WHATSAPP_APP_SECRET is configured — see
    app/services/whatsapp_api.py. A per-phone-number rate limit sits below that.

    Unlike Twilio's inline TwiML reply, Meta has no equivalent — every reply is a
    separate outbound API call via send_message().
    """
    payload = await request.json()

    for message in parse_incoming_messages(payload):
        phone = message["phone"]

        if not _rate_limiter.allow(phone):
            send_message(phone, "You're sending messages too quickly. Please wait a bit and try again.")
            continue

        reply_text = handle_incoming_message(
            phone=phone, body=message["body"], latitude=message["latitude"], longitude=message["longitude"]
        )
        send_message(phone, reply_text)

    return {"status": "ok"}
