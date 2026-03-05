from __future__ import annotations

TRACKING_TABLES: dict[str, str] = {
    "market_price_bars": """
    CREATE TABLE IF NOT EXISTS market_price_bars (
        symbol TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL,
        volume REAL, amount REAL, turnover REAL,
        source TEXT DEFAULT 'akshare',
        PRIMARY KEY (symbol, trade_date, source)
    );
    """,
    "price_forecasts": """
    CREATE TABLE IF NOT EXISTS price_forecasts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_type TEXT NOT NULL DEFAULT 'stock',
        symbol TEXT NOT NULL,
        forecast_date TEXT NOT NULL,
        target_date TEXT NOT NULL,
        window_days INTEGER NOT NULL,
        predicted_return REAL,
        predicted_direction TEXT,
        confidence REAL,
        method TEXT,
        features_json TEXT,
        as_of_date TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "forecast_evaluations": """
    CREATE TABLE IF NOT EXISTS forecast_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        forecast_id INTEGER REFERENCES price_forecasts(id),
        symbol TEXT NOT NULL,
        target_type TEXT DEFAULT 'stock',
        window_days INTEGER,
        predicted_return REAL,
        actual_return REAL,
        direction_hit INTEGER,
        abs_error REAL,
        evaluated_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "learning_log": """
    CREATE TABLE IF NOT EXISTS learning_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        evaluated_count INTEGER,
        hit_rate REAL,
        hit_rate_by_window TEXT,
        hit_rate_by_symbol TEXT,
        param_changes TEXT,
        notes TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "parameter_audit": """
    CREATE TABLE IF NOT EXISTS parameter_audit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        change_date TEXT NOT NULL,
        config_file TEXT NOT NULL,
        param_path TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        reason TEXT,
        source TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "advisor_analyses": """
    CREATE TABLE IF NOT EXISTS advisor_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        analysis_date TEXT NOT NULL,
        advisor_id TEXT NOT NULL,
        direction TEXT,
        confidence REAL,
        reasoning TEXT,
        key_factors TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "advisor_consensus": """
    CREATE TABLE IF NOT EXISTS advisor_consensus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        analysis_date TEXT NOT NULL,
        consensus_direction TEXT,
        agreement_ratio REAL,
        advisor_details TEXT,
        final_suggestion TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(symbol, analysis_date)
    );
    """,
    "paper_trades": """
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        action TEXT NOT NULL,
        quantity INTEGER,
        price REAL,
        commission REAL,
        stamp_tax REAL,
        reason TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "paper_snapshots": """
    CREATE TABLE IF NOT EXISTS paper_snapshots (
        snapshot_date TEXT PRIMARY KEY,
        cash REAL,
        positions_json TEXT,
        total_value REAL,
        daily_return REAL,
        cumulative_return REAL,
        max_drawdown REAL
    );
    """,
    "replay_sessions": """
    CREATE TABLE IF NOT EXISTS replay_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_name TEXT,
        as_of_start TEXT NOT NULL,
        as_of_end TEXT NOT NULL,
        symbols TEXT,
        total_forecasts INTEGER,
        hit_rate REAL,
        max_drawdown REAL,
        sharpe REAL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "pipeline_runs": """
    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        status TEXT NOT NULL,
        step_count INTEGER,
        critical_error TEXT,
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "quality_check_logs": """
    CREATE TABLE IF NOT EXISTS quality_check_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        overall_status TEXT,
        warn_count INTEGER,
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "signal_packs": """
    CREATE TABLE IF NOT EXISTS signal_packs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        summary TEXT,
        consensus_direction TEXT,
        role_agreement REAL,
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
    "archive_logs": """
    CREATE TABLE IF NOT EXISTS archive_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date TEXT NOT NULL,
        capacity_mb REAL,
        capacity_status TEXT,
        payload_json TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """,
}

NEWS_TABLES: dict[str, str] = {
    "news_items": """
    CREATE TABLE IF NOT EXISTS news_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        publish_time TEXT,
        title TEXT NOT NULL,
        source TEXT,
        url TEXT,
        content TEXT,
        sentiment TEXT,
        affected_symbols TEXT,
        llm_score REAL,
        llm_summary TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );
    """
}
