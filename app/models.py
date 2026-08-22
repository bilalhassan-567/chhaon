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


class Report(NewReport):
    """A stored report — anonymous, aggregate-only. No name, no phone number, no exact address."""

    id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "whatsapp"
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
