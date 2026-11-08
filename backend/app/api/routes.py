"""HTTP endpoints. There is intentionally NO endpoint that sends email."""
from fastapi import APIRouter, HTTPException, Request, status

from app.api.run_manager import RunConflictError, RunManager, RunNotFound
from app.api.schemas import ResumeRequest, RunCreated, RunSummary
from app.models import ProspectInput

router = APIRouter()


def _runs(req: Request) -> RunManager:
    return req.app.state.runs


@router.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


@router.post("/runs", response_model=RunCreated, status_code=status.HTTP_202_ACCEPTED, tags=["runs"])
def create_run(body: ProspectInput, req: Request):
    """Start researching a prospect. Returns immediately; poll `GET /runs/{run_id}` for progress."""
    return RunCreated(run_id=_runs(req).start(body), status="running")


@router.get("/runs", response_model=list[RunSummary], tags=["runs"])
def list_runs(req: Request, limit: int = 50):
    """Prospect history, newest first."""
    return [RunSummary.model_validate(r.model_dump()) for r in _runs(req).store.list(limit=max(1, min(limit, 200)))]


@router.get("/runs/{run_id}", tags=["runs"])
def get_run(run_id: str, req: Request):
    """Status, progress, research, evidence, ranking, draft, quality report and any pending pause (`pending`)."""
    try:
        return _runs(req).detail(run_id)
    except RunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")


@router.post("/runs/{run_id}/resume", status_code=status.HTTP_202_ACCEPTED, tags=["runs"])
def resume_run(run_id: str, body: ResumeRequest, req: Request):
    """Answer the run's pending pause.

    - `review`: `{"action": "approve" | "reject" | "edit" | "choose_signal" | "regenerate", ...}`
    - `identity`: `{"candidate_id": "c1"}` or `{"company_only": true}` or `{"abort": true}`
    - `insufficient` / `sensitive`: `{"action": "add_context", "context": "..."}` or `{"action": "abstain"}`
    - `conflict`: `{"resolutions": {"<conflict_id>": "<evidence_id>" | "exclude"}}` or `{"abort": true}`

    Approving never sends email — it only marks the draft ready for you to send manually.
    """
    try:
        _runs(req).resume(run_id, body.type, body.value)
    except RunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    except RunConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    except ValueError as e:  # includes Pydantic ValidationError
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)[:600])
    return {"run_id": run_id, "status": "running"}


@router.post("/runs/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED, tags=["runs"])
def retry_run(run_id: str, req: Request):
    """Continue a failed or stale run from its last checkpoint."""
    try:
        _runs(req).retry(run_id)
    except RunNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    except RunConflictError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return {"run_id": run_id, "status": "running"}


@router.get("/usage", tags=["system"])
def usage(req: Request):
    """Total Groq tokens and Tavily credits used by runs in this server's history."""
    totals: dict[str, int] = {}
    for rec in _runs(req).store.list(limit=200):
        for k, v in ((rec.snapshot or {}).get("usage") or {}).items():
            totals[k] = totals.get(k, 0) + v
    return totals
