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


@router.get("/api/reports")
def reports():
    """Zone-level aggregate counts for the map. Never returns individual report
    detail beyond zone + count — matches the anonymous-by-design schema."""
    counts = get_store().counts_by_zone()
    zones_by_id = {z.id: z for z in load_zones()}
    return [
        {
            "zone_id": zone_id,
            "zone_name": zones_by_id[zone_id].name if zone_id in zones_by_id else zone_id,
            "lat": zones_by_id[zone_id].lat if zone_id in zones_by_id else None,
            "lon": zones_by_id[zone_id].lon if zone_id in zones_by_id else None,
            "count": count,
        }
        for zone_id, count in counts.items()
    ]
