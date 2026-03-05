from __future__ import annotations

import json
import sqlite3
from collections import Counter

from app.db.database import get_tracking_conn


def _dumps(payload: dict | list | None) -> str:
    return json.dumps(payload or {}, ensure_ascii=False)


def save_pipeline_run(payload: dict) -> None:
    with get_tracking_conn() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_runs(run_date, status, step_count, critical_error, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.get("date"),
                payload.get("status", "unknown"),
                len(payload.get("steps", [])),
                payload.get("critical_error"),
                _dumps(payload),
            ),
        )
        conn.commit()


def save_quality_check(run_date: str, payload: dict) -> None:
    with get_tracking_conn() as conn:
        conn.execute(
            """
            INSERT INTO quality_check_logs(run_date, overall_status, warn_count, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_date,
                payload.get("overall"),
                payload.get("warn_count"),
                _dumps(payload),
            ),
        )
        conn.commit()


def save_signal_pack(run_date: str, payload: dict) -> None:
    payload = _merge_signal_with_advisor_consensus(run_date, payload)
    consensus = payload.get("consensus", {}) if isinstance(payload, dict) else {}
    with get_tracking_conn() as conn:
        conn.execute(
            """
            INSERT INTO signal_packs(run_date, summary, consensus_direction, role_agreement, payload_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_date,
                payload.get("summary"),
                consensus.get("direction"),
                consensus.get("role_agreement"),
                _dumps(payload),
            ),
        )
        conn.commit()


def _merge_signal_with_advisor_consensus(run_date: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    merged = dict(payload)
    with get_tracking_conn() as conn:
        rows = conn.execute(
            """
            SELECT consensus_direction, agreement_ratio
            FROM advisor_consensus
            WHERE analysis_date=?
            """,
            (run_date,),
        ).fetchall()
    if not rows:
        return merged
    dirs = [r[0] for r in rows if r[0]]
    agreements = [float(r[1]) for r in rows if r[1] is not None]
    if not dirs or not agreements:
        return merged
    majority_dir = Counter(dirs).most_common(1)[0][0]
    avg_agreement = round(sum(agreements) / len(agreements), 4)
    consensus = dict(merged.get("consensus", {}))
    consensus["direction"] = majority_dir
    consensus["role_agreement"] = avg_agreement
    consensus["advisor_consensus_count"] = len(rows)
    merged["consensus"] = consensus
    return merged


def save_archive_log(run_date: str, payload: dict) -> None:
    capacity = payload.get("capacity", {}) if isinstance(payload, dict) else {}
    with get_tracking_conn() as conn:
        conn.execute(
            """
            INSERT INTO archive_logs(run_date, capacity_mb, capacity_status, payload_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                run_date,
                capacity.get("total_mb"),
                capacity.get("status"),
                _dumps(payload),
            ),
        )
        conn.commit()


def _fetch_latest(table_name: str) -> dict | None:
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None


def get_latest_pipeline_run() -> dict | None:
    return _fetch_latest("pipeline_runs")


def get_latest_quality_check() -> dict | None:
    return _fetch_latest("quality_check_logs")


def get_latest_signal_pack() -> dict | None:
    return _fetch_latest("signal_packs")


def get_latest_archive_log() -> dict | None:
    return _fetch_latest("archive_logs")


def get_recent_quality_checks(limit: int = 10) -> list[dict]:
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_date, overall_status, warn_count FROM quality_check_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_archive_logs(limit: int = 10) -> list[dict]:
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_date, capacity_mb, capacity_status FROM archive_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_recent_signal_packs(limit: int = 10) -> list[dict]:
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT run_date, consensus_direction, role_agreement FROM signal_packs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_rollback_event() -> dict | None:
    with get_tracking_conn() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, change_date, reason
            FROM parameter_audit
            WHERE source='rollback'
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        event_id = row["id"]
        detail_rows = conn.execute(
            """
            SELECT param_path, old_value, new_value
            FROM parameter_audit
            WHERE source='rollback' AND reason=? AND change_date=?
            ORDER BY id DESC
            LIMIT 20
            """,
            (row["reason"], row["change_date"]),
        ).fetchall()
        return {
            "id": event_id,
            "change_date": row["change_date"],
            "reason": row["reason"],
            "changes": [dict(r) for r in detail_rows],
        }
