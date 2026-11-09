"""Application factory. `create_app(db_path)` lets tests use a throw-away database."""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import routes_api, routes_web
from app.database import connect, init_db
from app.events import EventBus, NotificationConsumer
from app.services import Conflict, Forbidden, NotFound
from app.workflow import InvalidTransition

TEMPLATES = Path(__file__).parent / "templates"


def create_app(db_path: str | None = None) -> FastAPI:
    db_path = db_path or os.environ.get("TRACKER_DB", "tracker.db")
    init_db(db_path)

    app = FastAPI(
        title="Demo Issue Tracker",
        description="A demo system under test, built for quality-engineering practice. All data is fake.",
        version="1.0.0",
    )
    app.state.db_path = db_path
    app.state.bus = EventBus()
    app.state.consumer = NotificationConsumer(connect(db_path))

    @app.exception_handler(NotFound)
    async def not_found(_: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(Conflict)
    async def conflict(_: Request, exc: Conflict):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(Forbidden)
    async def forbidden(_: Request, exc: Forbidden):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(InvalidTransition)
    async def invalid_transition(_: Request, exc: InvalidTransition):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    app.include_router(routes_api.router, prefix="/api")
    app.include_router(routes_web.router)
    return app


app = create_app()
