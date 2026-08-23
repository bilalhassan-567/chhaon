from collections import Counter

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.services.official_figures import load_official_figures
from app.storage import get_store

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def compute_gap_stats() -> dict:
    """Shared aggregation behind both the /gap HTML page and the /api/gap JSON
    endpoint (used for live polling) — one source of truth, so the two can never
    drift out of sync with each other."""
    reports = get_store().list_since()
    total_reports = sum(r.report_count for r in reports)
    real_reports = sum(r.report_count for r in reports if r.source != "demo_seed")
    demo_reports = total_reports - real_reports
    by_incident_type = Counter()
    for r in reports:
        by_incident_type[r.incident_type.value] += r.report_count

    official_figures = load_official_figures()
    # The single starkest documented figure (0 officially recorded, 2022, 50°C, ~120M
    # people) — pulled by id rather than duplicating its text, so the headline banner
    # can never drift from docs/sources.md's one source of truth.
    headline_figure = next(f for f in official_figures if f.id == "punjab_2022")

    return {
        "total_reports": total_reports,
        "real_reports": real_reports,
        "demo_reports": demo_reports,
        "zones_reporting": len({r.zone_id for r in reports}),
        "by_incident_type": dict(by_incident_type),
        "official_figures": official_figures,
        "headline_figure": headline_figure,
    }


@router.get("/gap")
def gap_view(request: Request):
    return templates.TemplateResponse(request, "gap.html", compute_gap_stats())


@router.get("/api/gap")
def gap_json():
    """Live-polled by gap.html so the numbers update automatically as new reports
    come in, without a manual page refresh — official_figures/headline_figure are
    dataclasses, not JSON-serializable as-is, so only the parts the page actually
    needs to refresh are returned (the cited-figures panel itself is static)."""
    stats = compute_gap_stats()
    return {
        "total_reports": stats["total_reports"],
        "real_reports": stats["real_reports"],
        "demo_reports": stats["demo_reports"],
        "zones_reporting": stats["zones_reporting"],
        "by_incident_type": stats["by_incident_type"],
    }
