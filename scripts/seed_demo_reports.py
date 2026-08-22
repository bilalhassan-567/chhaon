"""Seeds a small, realistic set of demo reports so the live map and Gap Dashboard
aren't empty during judging.

Every seeded report is written with source="demo_seed" (never "whatsapp") — the map
and Gap Dashboard both disclose the real/demo split honestly rather than presenting
seed data as genuine incoming community reports (RULES.md §7's ethics framing applies
to seeded data too, not just real reports).

Writes through the same ReportStore interface and dedup logic real intake uses
(app.storage.get_store()), so it respects whatever STORAGE_BACKEND is set in the
environment this runs in. Usage:

    python scripts/seed_demo_reports.py --dry-run   # preview, writes nothing
    python scripts/seed_demo_reports.py --yes       # actually write

--yes is required whenever STORAGE_BACKEND=firestore, since that writes into the real
production database judges will see — a deliberate guard against an accidental prod
write, same pattern as ingestion/alert_check.py's --dry-run default.
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import STORAGE_BACKEND  # noqa: E402
from app.models import GeoSource, IncidentType, NewReport  # noqa: E402
from app.services.zones import load_zones  # noqa: E402
from app.storage import get_store  # noqa: E402

# (zone_id, incident_type, geo_source). Listed twice for walled_city/heat_exhaustion on
# purpose — the second call exercises the same duplicate-detection path a real pair of
# WhatsApp reports from the same area would hit (PS3's "verified sensors" dedup ask),
# so the seeded data also demonstrates that feature working, not just fills space.
# Skews toward denser, lower-income zones having more reports and fewer AC/shade options
# (Walled City, Mughalpura, Shalimar, Baghbanpura, Ravi Town) versus fewer in
# higher-income zones (DHA, Gulberg) — not a claim about real incidence, just a more
# realistic-looking spread than uniform coverage across all 20 zones.
DEMO_REPORTS = [
    ("walled_city", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("walled_city", IncidentType.heat_exhaustion, GeoSource.location_pin),  # merges -> count 2
    ("walled_city", IncidentType.heatstroke, GeoSource.zone_name),
    ("mughalpura", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("mughalpura", IncidentType.heatstroke, GeoSource.zone_name),
    ("shalimar", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("baghbanpura", IncidentType.heat_exhaustion, GeoSource.zone_name),
    ("baghbanpura", IncidentType.death, GeoSource.location_pin),
    ("ravi_town", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("samanabad", IncidentType.other, GeoSource.zone_name),
    ("township", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("iqbal_town", IncidentType.heatstroke, GeoSource.zone_name),
    ("model_town", IncidentType.heat_exhaustion, GeoSource.location_pin),
    ("dha", IncidentType.heat_exhaustion, GeoSource.zone_name),
]

# Small jitter so location-pin reports don't all land exactly on the zone centroid —
# roughly +/- 400m, deterministic seed so re-running --dry-run shows the same preview.
_JITTER_DEGREES = 0.0035
random.seed("chhaon-demo-seed")


def _jittered(lat: float, lon: float) -> tuple[float, float]:
    return (
        round(lat + random.uniform(-_JITTER_DEGREES, _JITTER_DEGREES), 6),
        round(lon + random.uniform(-_JITTER_DEGREES, _JITTER_DEGREES), 6),
    )


def run(dry_run: bool) -> None:
    zones_by_id = {z.id: z for z in load_zones()}

    print(f"STORAGE_BACKEND={STORAGE_BACKEND}")
    if dry_run:
        print("[dry run] would seed the following, nothing will be written:\n")
    else:
        print(f"Seeding {len(DEMO_REPORTS)} demo reports for real...\n")

    store = None if dry_run else get_store()

    for zone_id, incident_type, geo_source in DEMO_REPORTS:
        zone = zones_by_id[zone_id]
        if geo_source == GeoSource.location_pin:
            lat, lon = _jittered(zone.lat, zone.lon)
        else:
            lat = lon = None

        line = f"  {zone.name:30s} {incident_type.value:16s} {geo_source.value:14s}"
        if dry_run:
            print(line)
            continue

        report = store.add_or_increment(
            NewReport(
                zone_id=zone_id,
                lat=lat,
                lon=lon,
                geo_source=geo_source,
                incident_type=incident_type,
                source="demo_seed",
            )
        )
        print(f"{line} -> report_count={report.report_count}")

    if dry_run:
        print("\nRe-run with --yes to actually write these (requires --yes if")
        print("STORAGE_BACKEND=firestore, since that's the live production database).")
    else:
        print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview only, writes nothing")
    parser.add_argument(
        "--yes", action="store_true", help="required to actually write when STORAGE_BACKEND=firestore"
    )
    args = parser.parse_args()

    if not args.dry_run and STORAGE_BACKEND == "firestore" and not args.yes:
        print(
            "STORAGE_BACKEND=firestore — this would write into the live production "
            "database. Re-run with --yes to confirm, or --dry-run to preview first."
        )
        sys.exit(1)

    run(dry_run=args.dry_run)
