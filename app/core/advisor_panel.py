from __future__ import annotations

import json
from datetime import date

from app.advisors.panel import analyze_with_roles
from app.db.database import get_tracking_conn

def analyze(symbol: str) -> dict:
    role_result = analyze_with_roles(symbol)
    run_date = str(date.today())
    advisors = [
        {
            "id": item["role"],
            "name": item["role"],
            "direction": item["direction"],
            "confidence": item["confidence"],
            "key_factors": [item["reasoning"]],
        }
        for item in role_result["roles"]
    ]
    result = {
        "symbol": symbol,
        "date": run_date,
        "advisors": advisors,
        "consensus": {
            "direction": role_result["consensus_direction"],
            "agreement": role_result["role_agreement"],
            "suggestion": "一致性高可小仓位试探，一致性低则观望",
        },
        "personas": role_result["personas"],
    }
    with get_tracking_conn() as conn:
        for row in advisors:
            conn.execute(
                """
                INSERT INTO advisor_analyses
                (symbol, analysis_date, advisor_id, direction, confidence, reasoning, key_factors)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    run_date,
                    row["id"],
                    row["direction"],
                    row["confidence"],
                    row["key_factors"][0] if row["key_factors"] else "",
                    json.dumps(row["key_factors"], ensure_ascii=False),
                ),
            )
        conn.execute(
            """
            INSERT INTO advisor_consensus
            (symbol, analysis_date, consensus_direction, agreement_ratio, advisor_details, final_suggestion)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, analysis_date) DO UPDATE SET
                consensus_direction=excluded.consensus_direction,
                agreement_ratio=excluded.agreement_ratio,
                advisor_details=excluded.advisor_details,
                final_suggestion=excluded.final_suggestion
            """,
            (
                symbol,
                run_date,
                result["consensus"]["direction"],
                result["consensus"]["agreement"],
                json.dumps(advisors, ensure_ascii=False),
                result["consensus"]["suggestion"],
            ),
        )
        conn.commit()
    return result
