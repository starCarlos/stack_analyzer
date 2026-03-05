from __future__ import annotations

from contextlib import contextmanager
import json
import sqlite3
from typing import Any


class SQLiteRepo:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS market_snapshot (
                    trade_date TEXT NOT NULL,
                    index_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    change_pct REAL NOT NULL,
                    source TEXT,
                    PRIMARY KEY (trade_date, index_name)
                );
                CREATE TABLE IF NOT EXISTS sector_snapshot (
                    trade_date TEXT NOT NULL,
                    sector_name TEXT NOT NULL,
                    heat REAL NOT NULL,
                    change_pct REAL NOT NULL,
                    PRIMARY KEY (trade_date, sector_name)
                );
                CREATE TABLE IF NOT EXISTS recommendation (
                    trade_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    market TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    score REAL NOT NULL,
                    action TEXT NOT NULL,
                    reason TEXT,
                    listed INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (trade_date, symbol)
                );
                CREATE TABLE IF NOT EXISTS replay_result (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    as_of TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    predicted_return REAL NOT NULL,
                    actual_return REAL NOT NULL,
                    abs_error REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS model_weights (
                    weight_date TEXT PRIMARY KEY,
                    weights_json TEXT NOT NULL
                );
                '''
            )

    def upsert_market_snapshot(self, trade_date: str, rows: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.executemany(
                '''
                INSERT INTO market_snapshot(trade_date,index_name,value,change_pct,source)
                VALUES(?,?,?,?,?)
                ON CONFLICT(trade_date,index_name) DO UPDATE SET
                    value=excluded.value,
                    change_pct=excluded.change_pct,
                    source=excluded.source
                ''',
                [
                    (trade_date, r['index_name'], float(r['value']), float(r['change_pct']), r.get('source', 'generated'))
                    for r in rows
                ],
            )

    def upsert_sector_snapshot(self, trade_date: str, rows: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.executemany(
                '''
                INSERT INTO sector_snapshot(trade_date,sector_name,heat,change_pct)
                VALUES(?,?,?,?)
                ON CONFLICT(trade_date,sector_name) DO UPDATE SET
                    heat=excluded.heat,
                    change_pct=excluded.change_pct
                ''',
                [(trade_date, r['sector_name'], float(r['heat']), float(r['change_pct'])) for r in rows],
            )

    def save_recommendations(self, trade_date: str, rows: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.executemany(
                '''
                INSERT INTO recommendation(trade_date,symbol,name,market,sector,score,action,reason,listed)
                VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(trade_date,symbol) DO UPDATE SET
                    name=excluded.name,
                    market=excluded.market,
                    sector=excluded.sector,
                    score=excluded.score,
                    action=excluded.action,
                    reason=excluded.reason,
                    listed=excluded.listed
                ''',
                [
                    (
                        trade_date,
                        r['symbol'],
                        r['name'],
                        r['market'],
                        r['sector'],
                        float(r['score']),
                        r['action'],
                        r['reason'],
                        1 if r.get('listed', True) else 0,
                    )
                    for r in rows
                ],
            )

    def get_dashboard(self, trade_date: str) -> dict[str, Any]:
        with self._conn() as conn:
            idx = [dict(x) for x in conn.execute('SELECT index_name,value,change_pct,source FROM market_snapshot WHERE trade_date=? ORDER BY index_name', (trade_date,)).fetchall()]
            sec = [dict(x) for x in conn.execute('SELECT sector_name,heat,change_pct FROM sector_snapshot WHERE trade_date=? ORDER BY heat DESC', (trade_date,)).fetchall()]
            rec = [dict(x) for x in conn.execute('SELECT symbol,name,market,sector,score,action,reason,listed FROM recommendation WHERE trade_date=? ORDER BY score DESC', (trade_date,)).fetchall()]
        return {'indices': idx, 'sectors': sec, 'recommended_buy': rec}

    def latest_trade_date(self) -> str | None:
        with self._conn() as conn:
            row = conn.execute('SELECT max(trade_date) as d FROM recommendation').fetchone()
        return row['d'] if row and row['d'] else None

    def insert_replay_results(self, rows: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            conn.executemany(
                'INSERT INTO replay_result(as_of,symbol,predicted_return,actual_return,abs_error,created_at) VALUES(?,?,?,?,?,?)',
                [
                    (r['as_of'], r['symbol'], float(r['predicted_return']), float(r['actual_return']), float(r['abs_error']), r['created_at'])
                    for r in rows
                ],
            )

    def latest_replay_mae(self, as_of: str) -> float:
        with self._conn() as conn:
            row = conn.execute('SELECT avg(abs_error) as mae FROM replay_result WHERE as_of=?', (as_of,)).fetchone()
        return float(row['mae']) if row and row['mae'] is not None else 0.0

    def save_weights(self, weight_date: str, weights: dict[str, float]) -> None:
        payload = json.dumps(weights, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                'INSERT INTO model_weights(weight_date,weights_json) VALUES(?,?) ON CONFLICT(weight_date) DO UPDATE SET weights_json=excluded.weights_json',
                (weight_date, payload),
            )

    def latest_weights(self) -> dict[str, float]:
        with self._conn() as conn:
            row = conn.execute('SELECT weights_json FROM model_weights ORDER BY weight_date DESC LIMIT 1').fetchone()
        if not row:
            return {'fundamental': 0.4, 'sentiment': 0.3, 'risk': 0.3}
        return json.loads(row['weights_json'])
