from fastapi import APIRouter, HTTPException

from app.utils.results import (
    ResultsUnavailableError,
    load_case_comparisons,
    load_metrics,
)


router = APIRouter(prefix="/api", tags=["benchmark"])


@router.get("/benchmark")
def benchmark():
    try:
        return load_metrics()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/benchmark/cases")
def benchmark_cases():
    try:
        return load_case_comparisons()
    except ResultsUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
