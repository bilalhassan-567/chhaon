from fastapi import FastAPI

from app.routes import api, gap, intake, map as map_route

app = FastAPI(title="Chhaon")

app.include_router(map_route.router)
app.include_router(gap.router)
app.include_router(api.router)
app.include_router(intake.router)
