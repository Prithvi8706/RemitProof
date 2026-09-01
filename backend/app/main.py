from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import benchmark, dashboard, exceptions
from app.utils.results import ResultsUnavailableError, load_results


app = FastAPI(
    title="RemitProof API",
    version="0.1.0",
    description="Evidence-grounded investigation for unresolved cross-border receivables.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(dashboard.router)
app.include_router(exceptions.router)
app.include_router(benchmark.router)


@app.get("/live")
def live():
    """Process liveness does not depend on generated benchmark artifacts."""
    return {"status": "alive"}


def _assert_ready() -> None:
    try:
        load_results()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/ready")
def ready():
    _assert_ready()
    return {"status": "ready"}


@app.get("/health")
def health():
    """Backward-compatible readiness endpoint."""
    _assert_ready()
    return {"status": "ok", "ready": True}
