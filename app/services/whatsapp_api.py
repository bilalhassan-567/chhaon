"""Meta WhatsApp Cloud API integration — replaces Twilio (switched 22 Aug 2026, see
docs/master-workout/PROGRESS.md: Twilio's trial isn't offered in Pakistan).

Key differences from Twilio that shaped this module:
- Inbound webhook payload is nested JSON (entry -> changes -> value -> messages), not
  flat form fields.
- Replies are NOT returned inline in the webhook response (no TwiML equivalent) — they
  are sent via a separate POST to the Graph API, using the same send_message() this
  module exposes for both webhook replies and outbound alerts.
- Signature verification uses X-Hub-Signature-256 (HMAC-SHA256 over the raw request
  body, keyed by the app secret) instead of Twilio's URL+params HMAC-SHA1 scheme.
- Meta also requires a one-time GET verification handshake before it will send real
  webhooks at all — see app/routes/intake.py.

Phone numbers here are Meta's own wire format: digits only, country code, no leading
"+", no "whatsapp:" prefix (e.g. "923001234567") — used as-is as the canonical `phone`
value everywhere in this app (conversation state keys, registration store, rate
limiter), so there's never a format conversion to get wrong between "what we received"
and "what we send back to".
"""

import hashlib
import hmac

import httpx
from fastapi import Request

from app.config import (
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_API_VERSION,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_NUMBER_ID,
)

GRAPH_API_BASE = "https://graph.facebook.com"


async def verify_webhook_signature(request: Request) -> bool:
    """Fails closed once WHATSAPP_APP_SECRET is configured (production); only skips
    in pure local dev before any account exists, same policy as the old Twilio check."""
    if not WHATSAPP_APP_SECRET:
        return True

    signature_header = request.headers.get("X-Hub-Signature-256", "")
    if not signature_header.startswith("sha256="):
        return False
    provided_signature = signature_header.removeprefix("sha256=")

    body = await request.body()
    expected_signature = hmac.new(WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(provided_signature, expected_signature)


def parse_incoming_messages(payload: dict) -> list[dict]:
    """Extracts a flat list of {phone, body, latitude, longitude} from Meta's nested
    webhook payload. Meta batches messages into entry[].changes[].value.messages[] —
    usually exactly one, but the shape allows more, so handle all of them. Silently
    skips message types we don't handle (e.g. images, reactions, button replies) —
    this app's flow is text and location only."""
    messages = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                phone = message.get("from", "")
                msg_type = message.get("type")

                if msg_type == "text":
                    messages.append(
                        {"phone": phone, "body": message["text"]["body"], "latitude": None, "longitude": None}
                    )
                elif msg_type == "location":
                    loc = message["location"]
                    messages.append(
                        {"phone": phone, "body": "", "latitude": str(loc["latitude"]), "longitude": str(loc["longitude"])}
                    )
                # other types (image, interactive, reaction, ...) intentionally skipped
    return messages


def send_message(to: str, body: str) -> bool:
    if not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise RuntimeError(
            "WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID not configured — see .env.example."
        )

    url = f"{GRAPH_API_BASE}/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        print(f"  WhatsApp send failed: {exc}")
        return False
