"""Day 6: outbound preventive-alert threshold checker.

Intended to run on a schedule via .github/workflows/alert-check.yml, but works
standalone against the local JSON store for manual testing:

    python ingestion/alert_check.py --dry-run   # logs what it would send, sends nothing
    python ingestion/alert_check.py              # sends real WhatsApp messages (needs
                                                   # real Meta WhatsApp credentials in .env)

Only checks zones that have at least one alert registration — most of Lahore's zones
will have none, so this avoids burning Open-Meteo calls (and, more importantly, avoids
ever constructing a message for a zone with nobody to send it to).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (  # noqa: E402
    ALERT_COOLDOWN_HOURS,
    ALERT_HEAT_INDEX_THRESHOLD_C,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
)
from app.services.open_meteo import fetch_current_heat_index  # noqa: E402
from app.services.whatsapp_api import send_message  # noqa: E402
from app.services.zones import load_zones  # noqa: E402
from app.storage import get_alert_state_store, get_registration_store  # noqa: E402


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


def run(dry_run: bool = False) -> None:
    if not dry_run and not (WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise RuntimeError(
            "Meta WhatsApp credentials are not configured (WHATSAPP_ACCESS_TOKEN / "
            "WHATSAPP_PHONE_NUMBER_ID) — cannot send real alerts. Set them in .env "
            "locally or as GitHub Actions secrets in CI, or pass --dry-run to test "
            "the threshold logic without sending anything."
        )

    registration_store = get_registration_store()
    alert_state_store = get_alert_state_store()
    zones_by_id = {z.id: z for z in load_zones()}

    target_zone_ids = registration_store.zones_with_registrations()
    if not target_zone_ids:
        print("No zones have any alert registrations — nothing to check.")
        return

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
        message = build_alert_message(zone.name, reading.apparent_temperature_c)
        print(
            f"{zone.name}: {reading.apparent_temperature_c:.1f}°C >= "
            f"{ALERT_HEAT_INDEX_THRESHOLD_C}°C threshold — alerting {len(phones)} "
            "registered number(s)."
        )

        if dry_run:
            for phone in phones:
                print(f"  [dry run] would alert {mask_phone(phone)}")
            continue  # dry run must have zero side effects — no cooldown state written

        sent_any = False
        for phone in phones:
            if send_whatsapp_alert(phone, message):
                sent_any = True

        if sent_any:
            alert_state_store.record_alert_sent(zone_id, now)


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
