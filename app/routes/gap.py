from collections import Counter

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.services.official_figures import load_official_figures
from app.storage import get_store

router = APIRouter()
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@router.get("/gap")
def gap_view(request: Request):
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

    return templates.TemplateResponse(
        request,
        "gap.html",
        {
            "total_reports": total_reports,
            "real_reports": real_reports,
            "demo_reports": demo_reports,
            "zones_reporting": len({r.zone_id for r in reports}),
            "by_incident_type": dict(by_incident_type),
            "official_figures": official_figures,
            "headline_figure": headline_figure,
        },
    )
