from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class IncidentType(str, Enum):
    heat_exhaustion = "heat_exhaustion"
    heatstroke = "heatstroke"
    death = "death"
    other = "other"


class GeoSource(str, Enum):
    location_pin = "location_pin"
    zone_name = "zone_name"


class NewReport(BaseModel):
    """What the intake flow has once a report is fully collected, before it's stored."""

    zone_id: str
    lat: float | None = None
    lon: float | None = None
    geo_source: GeoSource
    incident_type: IncidentType
    # "whatsapp" for real intake (the default, never overridden by whatsapp_flow.py);
    # "demo_seed" for reports written by scripts/seed_demo_reports.py so the UI can
    # honestly disclose which visible signal is real vs seeded for demo reliability.
    source: str = "whatsapp"


class Report(NewReport):
    """A stored report — anonymous, aggregate-only. No name, no phone number, no exact address."""

    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    report_count: int = 1


class AlertRegistration(BaseModel):
    """The one place a phone number is legitimately stored — needed to actually send
    the preventive alert back out. Registration only happens through the WhatsApp
    opt-in flow (the sender registers their own number, verified by Meta's webhook
    signature), never through an open form that could be used to sign up someone
    else's number without consent. Never exposed via any API response."""

    phone: str
    zone_id: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WhatsAppConversationStage(str, Enum):
    awaiting_location = "awaiting_location"
    awaiting_incident_type = "awaiting_incident_type"
    awaiting_alert_zone = "awaiting_alert_zone"


class WhatsAppConversationState(BaseModel):
    
    phone: str
    stage: WhatsAppConversationStage
    zone_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    geo_source: GeoSource | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PushSubscription(BaseModel):
    """A browser's Web Push subscription (RFC 8292), the WhatsApp-independent analog
    of AlertRegistration. Unlike a phone number, this can't be used to register
    someone else without their consent — the endpoint/keys are issued by the
    browser's own push service only to the page that requested them, so there's no
    open-form abuse vector to guard against the way there is for phone numbers."""

    endpoint: str
    p256dh: str
    auth: str
    zone_id: str
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
