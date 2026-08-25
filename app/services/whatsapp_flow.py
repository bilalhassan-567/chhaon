"""The guided WhatsApp report flow sketched in docs/master-workout/day1-sketches.md,
plus alert registration (Day 6).

Conversation state is persisted via ConversationStateStore (Local/Firestore), the same
pattern as every other store in this project. It used to be a plain in-memory dict —
moved off that after a real, confirmed bug (25 Aug 2026, see PROGRESS.md): Vercel's
serverless functions don't guarantee two messages in the same conversation are handled
by the same warm process, so an in-memory dict could silently forget an in-progress
report between messages sent less than a minute apart, restarting the flow from
scratch with no error either side.

Security note on alert registration: it is reachable ONLY through this WhatsApp flow,
never through a web form. A phone number here is always the number Meta verified as
the actual sender of the message (and the intake webhook itself is signature-verified —
see app/services/whatsapp_api.py) — so a registration always means "this phone opted
itself in," never "someone typed in a stranger's number." An open web form accepting
an arbitrary phone number would let anyone sign up someone else for unwanted messages;
this design avoids that class of abuse by construction rather than by validation.
"""

from app.models import GeoSource, IncidentType, NewReport, WhatsAppConversationStage, WhatsAppConversationState
from app.services.zones import find_zone_by_name, nearest_zone
from app.storage import get_conversation_store, get_registration_store, get_store

INCIDENT_TYPE_MENU = {
    "1": IncidentType.heat_exhaustion,
    "2": IncidentType.heatstroke,
    "3": IncidentType.death,
    "4": IncidentType.other,
}

LOCATION_PROMPT = (
    "Please share your location (tap the + or paperclip icon -> Location -> Send "
    "Your Current Location) so we can map this report accurately. If you can't "
    "share location, just reply with your neighbourhood name instead (e.g. Model "
    "Town, Township, Walled City)."
)

INCIDENT_TYPE_PROMPT = (
    "What happened? Reply with a number:\n"
    "1) Heat exhaustion / dizziness\n"
    "2) Heatstroke (collapse, confusion, hot dry skin)\n"
    "3) Death\n"
    "4) Other heat-related"
)

WELCOME_PROMPT = (
    "Chhaon logs heat-related incidents anonymously to help track heat risk in "
    "Lahore. No names or exact addresses are ever collected. Reply ALERT ON to "
    "register for heat warnings instead of filing a report. " + LOCATION_PROMPT
)

ALERT_ZONE_PROMPT = (
    "Which area do you want heat warnings for? Reply with your neighbourhood name, "
    "or share your location. Reply STOP anytime to opt out."
)

ALERT_STOP_CONFIRMATION = (
    "You've been unsubscribed from heat alerts. You can still send a report anytime."
)

STOP_KEYWORDS = {"stop", "alert off", "unsubscribe"}
ALERT_ON_KEYWORDS = {"alert on", "alert", "subscribe"}


def handle_incoming_message(
    phone: str, body: str, latitude: str | None = None, longitude: str | None = None
) -> str:
    normalized = body.strip().lower()
    store = get_conversation_store()

    # Commands are checked before anything else, regardless of what the sender was
    # mid-way through — the safest, least surprising behaviour, and it means a stuck
    # or confused conversation can always be escaped with a keyword.
    if normalized in STOP_KEYWORDS:
        store.clear(phone)
        get_registration_store().unregister_all(phone)
        return ALERT_STOP_CONFIRMATION

    if normalized in ALERT_ON_KEYWORDS:
        store.set(WhatsAppConversationState(phone=phone, stage=WhatsAppConversationStage.awaiting_alert_zone))
        return ALERT_ZONE_PROMPT

    state = store.get(phone)

    if state is None:
        store.set(WhatsAppConversationState(phone=phone, stage=WhatsAppConversationStage.awaiting_location))
        return WELCOME_PROMPT

    if state.stage is WhatsAppConversationStage.awaiting_location:
        return _handle_location_step(store, state, body, latitude, longitude)

    if state.stage is WhatsAppConversationStage.awaiting_incident_type:
        return _handle_incident_type_step(store, state, body)

    if state.stage is WhatsAppConversationStage.awaiting_alert_zone:
        return _handle_alert_zone_step(store, phone, body, latitude, longitude)

    # Shouldn't happen, but never leave a caller stuck.
    store.clear(phone)
    return WELCOME_PROMPT


def _resolve_zone(body: str, latitude: str | None, longitude: str | None):
    """Shared by the report flow and the alert flow: a WhatsApp location pin
    (preferred — real coordinates) or a typed zone name (fallback)."""
    if latitude and longitude:
        return nearest_zone(float(latitude), float(longitude)), GeoSource.location_pin
    zone = find_zone_by_name(body)
    return (zone, GeoSource.zone_name) if zone else (None, None)


def _handle_location_step(
    store, state: WhatsAppConversationState, body: str, latitude: str | None, longitude: str | None
) -> str:
    zone, geo_source = _resolve_zone(body, latitude, longitude)
    if zone is None:
        return "Sorry, I didn't recognize that area. " + LOCATION_PROMPT

    state.zone_id = zone.id
    state.geo_source = geo_source
    if geo_source is GeoSource.location_pin:
        state.lat, state.lon = float(latitude), float(longitude)
    state.stage = WhatsAppConversationStage.awaiting_incident_type
    store.set(state)
    return f"Got it: {zone.name}. {INCIDENT_TYPE_PROMPT}"


def _handle_incident_type_step(store, state: WhatsAppConversationState, body: str) -> str:
    choice = body.strip()
    incident_type = INCIDENT_TYPE_MENU.get(choice)
    if incident_type is None:
        return "Please reply with a number 1-4.\n" + INCIDENT_TYPE_PROMPT

    report = get_store().add_or_increment(
        NewReport(
            zone_id=state.zone_id,
            lat=state.lat,
            lon=state.lon,
            geo_source=state.geo_source,
            incident_type=incident_type,
        )
    )
    store.clear(state.phone)
    return (
        f"Logged: {report.zone_id}, {incident_type.value}. Thank you — this report "
        "is anonymous and helps track heat risk in your area. This is a "
        "community-reported signal, not a verified medical or legal record."
    )


def _handle_alert_zone_step(store, phone: str, body: str, latitude: str | None, longitude: str | None) -> str:
    zone, _ = _resolve_zone(body, latitude, longitude)
    if zone is None:
        return "Sorry, I didn't recognize that area. " + ALERT_ZONE_PROMPT

    get_registration_store().register(phone, zone.id)
    store.clear(phone)
    return (
        f"You're registered for heat warnings in {zone.name}. We'll message you here "
        "when the heat index reaches a dangerous level, with practical guidance. "
        "Reply STOP anytime to opt out."
    )
