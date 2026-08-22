"""Open-Meteo integration — free, keyless API (see PLAN.md's stack table). This is
the one external data source that needs no account at all, so it's fully live and
testable from Day 1, unlike the WhatsApp/Firestore paths.

Open-Meteo has no field literally called "heat index" — `apparent_temperature`
("feels like", factoring in humidity and wind) is the closest equivalent and is what
the master doc's "heat-index overlay" refers to in practice.
"""

from dataclasses import dataclass

import httpx

from app.config import LAHORE_LAT, LAHORE_LON

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class HeatIndexReading:
    temperature_c: float
    apparent_temperature_c: float
    relative_humidity_pct: float
    observed_at: str


def fetch_current_heat_index(lat: float = LAHORE_LAT, lon: float = LAHORE_LON) -> HeatIndexReading:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m",
        "timezone": "Asia/Karachi",
    }
    response = httpx.get(OPEN_METEO_URL, params=params, timeout=10)
    response.raise_for_status()
    current = response.json()["current"]
    return HeatIndexReading(
        temperature_c=current["temperature_2m"],
        apparent_temperature_c=current["apparent_temperature"],
        relative_humidity_pct=current["relative_humidity_2m"],
        observed_at=current["time"],
    )
