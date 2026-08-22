"""Day 6: outbound preventive-alert threshold checker.

Intended to run on a schedule via .github/workflows/alert-check.yml, but works
standalone against the local JSON store for manual testing:

    python ingestion/alert_check.py --dry-run   # logs what it would send, sends nothing
    python ingestion/alert_check.py              # sends real alerts (needs real
                                                   # WhatsApp and/or VAPID credentials
                                                   # in .env, whichever channel has
                                                   # registered recipients)

Only checks zones that have at least one registration on *either* channel (WhatsApp
phone registration or Web Push subscription) — most of Lahore's zones will have none,
so this avoids burning Open-Meteo calls and constructing a message nobody receives.

Two independent, additive channels: a zone crossing the threshold alerts everyone
registered for it via WhatsApp *and* everyone subscribed via the web push widget —
whichever they opted into. One shared per-zone cooldown across both channels (not
per-channel), so a zone that stays above threshold doesn't re-alert anyone within
ALERT_COOLDOWN_HOURS regardless of which channel they're on.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
    ALERT_COOLDOWN_HOURS,
    ALERT_HEAT_INDEX_THRESHOLD_C,
    VAPID_PRIVATE_KEY,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
)
from app.services.open_meteo import fetch_current_heat_index  # noqa: E402
from app.services.web_push import send_push_notification  # noqa: E402
from app.services.whatsapp_api import send_message  # noqa: E402
from app.services.zones import load_zones  # noqa: E402
from app.storage import get_alert_state_store, get_push_subscription_store, get_registration_store  # noqa: E402


def mask_phone(phone: str) -> str:
    """Never print a full phone number — GitHub Actions logs are visible to every
    repo collaborator, and a phone number is the one piece of real PII this project
    stores at all."""
    if len(phone) <= 6:
        return "***"
    return phone[:6] + "…" + phone[-2:]


def build_alert_message(zone_name: str, apparent_temp_c: float) -> str:
    return (
        f"Chhaon heat warning: the heat index in {zone_name} has reached "
        f"{apparent_temp_c:.0f}°C, a dangerous level. Stay hydrated, avoid direct sun "
        "during peak hours, and rest in the nearest shaded or cool space if you feel "
        "unwell. Reply STOP to opt out of these alerts."
    )


def send_whatsapp_alert(phone: str, message: str) -> bool:
    try:
        return send_message(phone, message)
    except Exception as exc:  # one bad/unreachable number must not stop the whole run
        print(f"  failed to alert {mask_phone(phone)}: {exc}")
        return False


def send_push_alert(subscription, zone_name: str, message: str) -> bool:
    try:
        return send_push_notification(subscription, title=f"Chhaon heat warning — {zone_name}", body=message)
    except Exception as exc:  # one stale/revoked subscription must not stop the batch
        print(f"  failed to push-alert a subscription: {exc}")
        return False


def run(dry_run: bool = False) -> None:
    registration_store = get_registration_store()
    push_store = get_push_subscription_store()
    alert_state_store = get_alert_state_store()
    zones_by_id = {z.id: z for z in load_zones()}

    whatsapp_zone_ids = registration_store.zones_with_registrations()
    push_zone_ids = push_store.zones_with_subscriptions()
    target_zone_ids = whatsapp_zone_ids | push_zone_ids

    if not target_zone_ids:
        print("No zones have any alert registrations — nothing to check.")
        return

    if not dry_run:
        if whatsapp_zone_ids and not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
            raise RuntimeError(
                "Zones have WhatsApp registrations but WHATSAPP_ACCESS_TOKEN / "
                "WHATSAPP_PHONE_NUMBER_ID aren't configured — set them in .env locally "
                "or as GitHub Actions secrets in CI, or pass --dry-run."
            )
        if push_zone_ids and not VAPID_PRIVATE_KEY:
            raise RuntimeError(
                "Zones have Web Push subscriptions but VAPID_PRIVATE_KEY isn't "
                "configured — run scripts/generate_vapid_keys.py, or pass --dry-run."
            )

    now = datetime.now(timezone.utc)
    for zone_id in sorted(target_zone_ids):
        zone = zones_by_id.get(zone_id)
        if zone is None:
            continue  # a stale registration for a zone id no longer in zones.json

        reading = fetch_current_heat_index(zone.lat, zone.lon)
        if reading.apparent_temperature_c < ALERT_HEAT_INDEX_THRESHOLD_C:
            print(f"{zone.name}: {reading.apparent_temperature_c:.1f}°C — below threshold, skipping.")
            continue

        last_alert = alert_state_store.last_alert_at(zone_id)
        if last_alert is not None:
            hours_since = (now - last_alert).total_seconds() / 3600
            if hours_since < ALERT_COOLDOWN_HOURS:
                print(f"{zone.name}: above threshold but alerted {hours_since:.1f}h ago (cooldown {ALERT_COOLDOWN_HOURS}h) — skipping.")
                continue

        phones = registration_store.list_for_zone(zone_id)
        subscriptions = push_store.list_for_zone(zone_id)
        message = build_alert_message(zone.name, reading.apparent_temperature_c)
        print(
            f"{zone.name}: {reading.apparent_temperature_c:.1f}°C >= "
            f"{ALERT_HEAT_INDEX_THRESHOLD_C}°C threshold — alerting {len(phones)} "
            f"WhatsApp number(s) and {len(subscriptions)} browser subscription(s)."
        )

        if dry_run:
            for phone in phones:
                print(f"  [dry run] would WhatsApp-alert {mask_phone(phone)}")
            for _ in subscriptions:
                print("  [dry run] would push-alert a browser subscription")
            continue  # dry run must have zero side effects — no cooldown state written

        sent_any = False
        for phone in phones:
            if send_whatsapp_alert(phone, message):
                sent_any = True
        for subscription in subscriptions:
            if send_push_alert(subscription, zone.name, message):
                sent_any = True

        if sent_any:
            alert_state_store.record_alert_sent(zone_id, now)


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
