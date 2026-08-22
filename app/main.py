from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.routes import api, gap, intake, map as map_route, push, report

app = FastAPI(title="Chhaon")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # Served from root (not /static/sw.js) so its default scope covers the whole
    # origin — a service worker can only control paths at or below where it's served.
    return FileResponse(BASE_DIR / "app" / "static" / "sw.js", media_type="application/javascript")


app.include_router(map_route.router)
app.include_router(gap.router)
app.include_router(api.router)
app.include_router(intake.router)
app.include_router(report.router)
app.include_router(push.router)
