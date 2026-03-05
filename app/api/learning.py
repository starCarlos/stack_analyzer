from __future__ import annotations

from fastapi import APIRouter, Query

from app.core import learner
from app.db.ops import (
    get_latest_pipeline_run,
    get_latest_quality_check,
    get_latest_rollback_event,
    get_latest_signal_pack,
    get_recent_archive_logs,
    get_recent_quality_checks,
    get_recent_signal_packs,
)

router = APIRouter(tags=["learning"])


@router.get("/learning/today")
def learning_today() -> dict:
    report = learner.build_daily_report()
    latest_run = get_latest_pipeline_run()
    latest_quality = get_latest_quality_check()
    latest_signal = get_latest_signal_pack()
    rollback = get_latest_rollback_event()
    report["pipeline_snapshot"] = {
        "status": latest_run.get("status") if latest_run else "no_run",
        "step_count": latest_run.get("step_count") if latest_run else 0,
        "quality_overall": latest_quality.get("overall_status") if latest_quality else "unknown",
        "role_agreement": latest_signal.get("role_agreement") if latest_signal else None,
        "rollback_event": rollback,
    }
    return report


@router.get("/learning/history")
def learning_history(days: int = Query(default=30, ge=1, le=365)) -> dict:
    limit = min(days, 30)
    return {
        "days": days,
        "quality_trend": get_recent_quality_checks(limit),
        "capacity_trend": get_recent_archive_logs(limit),
        "agreement_trend": get_recent_signal_packs(limit),
    }


@router.get("/learning/params")
def learning_params() -> dict:
    return {"changes": learner.learn_from_evaluations()["param_changes"]}
