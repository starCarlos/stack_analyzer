from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.data_manager import get_sector_universe_status
from app.db.ops import (
    get_latest_archive_log,
    get_latest_pipeline_run,
    get_latest_quality_check,
    get_latest_signal_pack,
)

router = APIRouter(tags=["system"])


class ConfigPayload(BaseModel):
    app_title: str | None = None
    pipeline_time: str | None = None


@router.get("/system/health")
def system_health() -> dict:
    latest_run = get_latest_pipeline_run()
    latest_quality = get_latest_quality_check()
    latest_signal = get_latest_signal_pack()
    latest_archive = get_latest_archive_log()
    return {
        "status": latest_run.get("status", "unknown") if latest_run else "no_run",
        "data_freshness": "good" if latest_run else "unknown",
        "llm_status": "configured" if os.getenv("LLM_API_KEY") else "missing_key",
        "latest_run": {
            "run_date": latest_run.get("run_date") if latest_run else None,
            "step_count": latest_run.get("step_count") if latest_run else 0,
            "critical_error": latest_run.get("critical_error") if latest_run else None,
        },
        "quality": {
            "overall": latest_quality.get("overall_status") if latest_quality else "unknown",
            "warn_count": latest_quality.get("warn_count") if latest_quality else None,
        },
        "signal": {
            "consensus_direction": latest_signal.get("consensus_direction") if latest_signal else None,
            "role_agreement": latest_signal.get("role_agreement") if latest_signal else None,
        },
        "capacity": {
            "total_mb": latest_archive.get("capacity_mb") if latest_archive else None,
            "status": latest_archive.get("capacity_status") if latest_archive else None,
        },
    }


@router.get("/system/config")
def system_config() -> dict:
    return {
        "APP_TITLE": os.getenv("APP_TITLE", "A股智能投研系统"),
        "PIPELINE_TIME": os.getenv("PIPELINE_TIME", "18:30"),
        "ENABLE_AUTO_LEARN": os.getenv("ENABLE_AUTO_LEARN", "true"),
        "FULL_SECTOR_MODE": os.getenv("FULL_SECTOR_MODE", "auto"),
    }


@router.post("/system/config")
def update_system_config(payload: ConfigPayload) -> dict:
    if payload.app_title:
        os.environ["APP_TITLE"] = payload.app_title
    if payload.pipeline_time:
        os.environ["PIPELINE_TIME"] = payload.pipeline_time
    return {"updated": payload.model_dump(exclude_none=True)}


@router.get("/system/sectors")
def system_sectors() -> dict:
    return get_sector_universe_status()
