from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR
from app.routes import api, gap, intake, map as map_route

app = FastAPI(title="Chhaon")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")

app.include_router(map_route.router)
app.include_router(gap.router)
app.include_router(api.router)
app.include_router(intake.router)
