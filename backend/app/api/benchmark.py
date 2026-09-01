from fastapi import APIRouter, HTTPException

from app.utils.results import ResultsUnavailableError, load_metrics


router = APIRouter(prefix="/api", tags=["benchmark"])


@router.get("/benchmark")
def benchmark():
    try:
        return load_metrics()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
