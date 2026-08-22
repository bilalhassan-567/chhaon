from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.config import (
    BASE_DIR,
    WEB_REPORT_RATE_LIMIT_MAX_MESSAGES,
    WEB_REPORT_RATE_LIMIT_WINDOW_MINUTES,
)
from app.models import GeoSource, IncidentType, NewReport
from app.services.rate_limit import RateLimiter
from app.services.zones import find_zone_by_name, nearest_zone
from app.storage import get_store

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

_rate_limiter = RateLimiter(
    max_events=WEB_REPORT_RATE_LIMIT_MAX_MESSAGES,
    window_seconds=WEB_REPORT_RATE_LIMIT_WINDOW_MINUTES * 60,
)


def _client_ip(request: Request) -> str:
    """Vercel (and most reverse proxies) put the real client IP in X-Forwarded-For,
    not the raw connection — request.client.host would just be the proxy's own
    address in production. Take the first hop, which is the original client."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class WebReportSubmission(BaseModel):
    incident_type: IncidentType
    lat: float | None = None
    lon: float | None = None
    zone_name: str | None = None


@router.get("/report")
def report_form(request: Request):
    """A plain web form — the WhatsApp-independent secondary intake channel. Uses the
    browser's Geolocation API client-side to auto-detect the reporter's position
    (falls back to typed zone name if location is denied/unavailable), same two-path
    design as the WhatsApp flow's location-pin/zone-name fallback."""
    return templates.TemplateResponse(request, "report.html", {})


@router.post("/api/report")
def submit_web_report(submission: WebReportSubmission, request: Request):
    """Same anonymous, aggregate-only storage path real WhatsApp intake uses
    (NewReport -> add_or_increment), tagged source="web" so it's honestly
    distinguishable from WhatsApp reports everywhere the map/Gap Dashboard disclose
    real vs. demo vs. channel. Rate-limited per IP (see _client_ip) since a web form
    has less inherent friction than needing a WhatsApp account."""
    ip = _client_ip(request)
    if not _rate_limiter.allow(ip):
        raise HTTPException(status_code=429, detail="Too many reports from this connection. Please wait and try again.")

    if submission.lat is not None and submission.lon is not None:
        zone = nearest_zone(submission.lat, submission.lon)
        geo_source = GeoSource.location_pin
    elif submission.zone_name:
        zone = find_zone_by_name(submission.zone_name)
        if zone is None:
            raise HTTPException(status_code=400, detail="Couldn't match that to a known Lahore zone.")
        geo_source = GeoSource.zone_name
    else:
        raise HTTPException(status_code=400, detail="Share your location or type a neighbourhood name.")

    report = get_store().add_or_increment(
        NewReport(
            zone_id=zone.id,
            lat=submission.lat,
            lon=submission.lon,
            geo_source=geo_source,
            incident_type=submission.incident_type,
            source="web",
        )
    )
    return {"status": "ok", "zone_name": zone.name, "report_count": report.report_count}
