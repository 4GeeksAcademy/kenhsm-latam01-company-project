"""Authenticated endpoints for weekly business KPIs and pipeline execution."""

from __future__ import annotations

from datetime import date, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from brasaland_api.core.deps import get_current_user, require_admin
from data.pipelines import run_store
from data.pipelines.pipeline import trigger_weekly_location_performance_flow


router = APIRouter(prefix="/reporting", tags=["reporting"])


class PipelineRunAccepted(BaseModel):
    run_id: str
    status: str


class PipelineRunOut(BaseModel):
    run_id: str
    flow_name: str
    trigger_type: str
    week_start: date
    status: str
    phase: str
    started_at: datetime
    ended_at: datetime | None = None
    source_counts: dict[str, int]
    source_min_timestamp: datetime | None = None
    source_max_timestamp: datetime | None = None
    source_watermark: datetime | None = None
    output_rows: int
    records_processed: int
    error_code: str | None = None
    error_message: str | None = None
    errors: list[str] = Field(default_factory=list)
    local_mode: bool = False


class WeeklyLocationKPI(BaseModel):
    location_id: str
    country: str
    total_purchase_cost: float
    total_waste_cost: float
    waste_ratio: float
    stockout_events_count: int
    price_alert_events_count: int
    currency: str


class WeeklyLocationPerformanceOut(BaseModel):
    week_start: date
    locations: list[WeeklyLocationKPI]


@router.get("/pipeline-runs/latest", response_model=PipelineRunOut)
def latest_pipeline_run(_current_user=Depends(get_current_user)) -> PipelineRunOut:
    record = run_store.get_latest_pipeline_run()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hay corridas del pipeline registradas.")
    return record


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_pipeline_run(
    background_tasks: BackgroundTasks,
    week_start: date | None = Query(None),
    _current_user=Depends(require_admin),
) -> PipelineRunAccepted:
    if week_start is not None and week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start debe ser lunes.")
    run_id = str(uuid4())
    background_tasks.add_task(
        trigger_weekly_location_performance_flow,
        week_start=week_start,
        run_id=run_id,
    )
    return PipelineRunAccepted(run_id=run_id, status="scheduled")


@router.get("/weekly-location-performance", response_model=WeeklyLocationPerformanceOut)
def weekly_location_performance(
    week_start: date | None = Query(None),
    _current_user=Depends(get_current_user),
) -> WeeklyLocationPerformanceOut:
    if week_start is not None and week_start.weekday() != 0:
        raise HTTPException(status_code=400, detail="week_start debe ser lunes.")
    report = run_store.query_weekly_location_performance(week_start)
    if report is None:
        raise HTTPException(status_code=404, detail="No hay KPIs publicados para esa semana.")
    return report