from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def capacity_report(data_dir: str = "output") -> dict:
    root = Path(data_dir)
    total_bytes = 0
    for p in root.rglob("*"):
        if p.is_file():
            total_bytes += p.stat().st_size
    total_mb = round(total_bytes / 1024 / 1024, 2)
    status = "warn" if total_mb >= 1024 else "pass"
    return {"total_mb": total_mb, "status": status, "advice": "接近阈值时建议拆库或归档冷数据"}


def archive_daily(run_date: str, pipeline_log: dict) -> dict:
    """4类归档步骤：写出每日快照并返回容量治理信息。"""
    archive_dir = Path("output/archive") / run_date.replace("-", "")
    archive_dir.mkdir(parents=True, exist_ok=True)

    summary_path = archive_dir / "pipeline_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "run_date": run_date,
                "status": pipeline_log.get("status"),
                "step_count": len(pipeline_log.get("steps", [])),
                "critical_error": pipeline_log.get("critical_error"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    full_log_path = archive_dir / "pipeline_full_log.json"
    with full_log_path.open("w", encoding="utf-8") as f:
        json.dump(pipeline_log, f, ensure_ascii=False, indent=2)

    capacity = capacity_report()
    return {
        "run_date": run_date,
        "archive_steps": {
            "detail_history": str(full_log_path),
            "evaluation_results": "待接真实评估明细归档",
            "report_snapshots": str(summary_path),
            "audit_logs": "待接审计日志归档",
        },
        "capacity": capacity,
        "created_at": str(date.today()),
        "pipeline_log_size": len(str(pipeline_log)),
    }
