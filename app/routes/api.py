from fastapi import APIRouter

from app.services.open_meteo import fetch_current_heat_index
from app.services.zones import load_zones
from app.storage import get_store

router = APIRouter()


@router.get("/api/heat-index")
def heat_index():
    reading = fetch_current_heat_index()
    return {
        "temperature_c": reading.temperature_c,
        "apparent_temperature_c": reading.apparent_temperature_c,
        "relative_humidity_pct": reading.relative_humidity_pct,
        "observed_at": reading.observed_at,
    }


@router.get("/api/zones")
def zones():
    """The full 20-zone list (id + name only) — used by the push-alert opt-in
    widget's zone picker, distinct from /api/reports which only includes zones that
    already have at least one report."""
    return [{"zone_id": z.id, "zone_name": z.name} for z in load_zones()]


@router.get("/api/reports")
def reports():
    """Zone-level aggregate counts for the map. Never returns individual report
    detail beyond zone + count — matches the anonymous-by-design schema. Splits each
    zone's count into real (WhatsApp + web) vs demo-seeded so the map can disclose
    which markers are seeded for reliability during judging, same honesty standard as
    the Gap Dashboard — never presents seed data as real incoming reports. Also
    breaks real counts down by channel (whatsapp vs web) to make the secondary
    web-report intake path visibly demonstrable, not just theoretically present."""
    zones_by_id = {z.id: z for z in load_zones()}
    by_zone: dict[str, dict] = {}
    for r in get_store().list_since():
        entry = by_zone.setdefault(r.zone_id, {"real": 0, "demo": 0, "whatsapp": 0, "web": 0})
        if r.source == "demo_seed":
            entry["demo"] += r.report_count
        else:
            entry["real"] += r.report_count
            entry["whatsapp" if r.source == "whatsapp" else "web"] += r.report_count

    return [
        {
            "zone_id": zone_id,
            "zone_name": zones_by_id[zone_id].name if zone_id in zones_by_id else zone_id,
            "lat": zones_by_id[zone_id].lat if zone_id in zones_by_id else None,
            "lon": zones_by_id[zone_id].lon if zone_id in zones_by_id else None,
            "count": counts["real"] + counts["demo"],
            "real_count": counts["real"],
            "demo_count": counts["demo"],
            "whatsapp_count": counts["whatsapp"],
            "web_count": counts["web"],
        }
        for zone_id, counts in by_zone.items()
    ]
