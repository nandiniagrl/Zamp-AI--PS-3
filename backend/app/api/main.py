"""FastAPI app. Run locally:  uvicorn app.api.main:app --reload --port 8000   → docs at http://localhost:8000/docs"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.api.run_manager import RunManager
from app.config import get_settings
from app.graph.builder import build_graph
from app.graph.checkpoint import make_checkpointer
from app.logging_setup import setup_logging
from app.storage import make_store

log = logging.getLogger(__name__)


def create_app(manager: RunManager | None = None) -> FastAPI:
    """`manager` lets tests inject a RunManager (fakes + in-memory checkpointer)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_logging()
        s = get_settings()
        app.state.runs = manager or RunManager(build_graph(make_checkpointer(s)), make_store(s))
        app.state.runs.mark_stale_runs()
        log.info("Outreach Copilot API ready (checkpoints=%s, storage=%s)", s.checkpoint_backend, s.storage_backend)
        yield
        app.state.runs.shutdown()

    app = FastAPI(
        title="Outreach Copilot API", version="0.1.0", lifespan=lifespan,
        description="Researches B2B prospects and produces source-backed email drafts for HUMAN review. "
                    "This API never sends email.")
    app.add_middleware(CORSMiddleware,
                       allow_origins=[o.strip() for o in get_settings().cors_origins.split(",") if o.strip()],
                       allow_credentials=False, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type", "Authorization"])

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):  # never leak stack traces or secrets
        log.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error. Check the server logs."})

    app.include_router(router)
    return app


app = create_app()
