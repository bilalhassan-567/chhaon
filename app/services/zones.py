import json
from dataclasses import dataclass
from functools import lru_cache

from app.config import ZONES_FILE
from app.services.geo import haversine_meters


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    lat: float
    lon: float


@lru_cache
def load_zones() -> list[Zone]:
    data = json.loads(ZONES_FILE.read_text(encoding="utf-8"))
    return [Zone(**z) for z in data["zones"]]


def nearest_zone(lat: float, lon: float) -> Zone:
    zones = load_zones()
    return min(zones, key=lambda z: haversine_meters(lat, lon, z.lat, z.lon))


def find_zone_by_name(text: str) -> Zone | None:
    """Loose match: normalize whitespace/case, match on containment either direction."""
    needle = text.strip().lower()
    if not needle:
        return None
    for zone in load_zones():
        haystack = zone.name.lower()
        if needle == zone.id or needle in haystack or haystack in needle:
            return zone
    return None
