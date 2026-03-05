from __future__ import annotations

from datetime import datetime
import hashlib

from hotspot.infrastructure.sqlite_repo import SQLiteRepo
from hotspot.services.market_data_service import MarketDataService


class DashboardService:
    def __init__(self, repo: SQLiteRepo, market_data: MarketDataService) -> None:
        self.repo = repo
        self.market_data = market_data

    def _seed_market(self, trade_date: str) -> None:
        names = ['上证指数', '深证成指', '创业板指', '恒生指数']
        rows = []
        for n in names:
            h = int(hashlib.md5(f'{trade_date}:{n}'.encode('utf-8')).hexdigest()[:8], 16)
            rows.append(
                {
                    'index_name': n,
                    'value': 3000 + (h % 12000) / 10.0,
                    'change_pct': ((h % 600) - 300) / 100.0,
                    'source': 'synthetic',
                }
            )
        self.repo.upsert_market_snapshot(trade_date, rows)

    def _seed_sector(self, trade_date: str) -> None:
        sectors = ['人工智能', '机器人', '新能源', '白酒消费', '半导体']
        rows = []
        for s in sectors:
            h = int(hashlib.md5(f'{trade_date}:{s}'.encode('utf-8')).hexdigest()[:8], 16)
            rows.append(
                {
                    'sector_name': s,
                    'heat': round(50 + (h % 5000) / 100.0, 2),
                    'change_pct': round(((h % 800) - 400) / 100.0, 2),
                }
            )
        self.repo.upsert_sector_snapshot(trade_date, rows)

    def get_dashboard(self, trade_date: str | None = None) -> dict:
        d = trade_date or self.repo.latest_trade_date() or datetime.now().strftime('%Y-%m-%d')
        data = self.repo.get_dashboard(d)
        if not data['indices']:
            today = datetime.now().strftime('%Y-%m-%d')
            if d == today:
                real_rows = self.market_data.fetch_indices()
                if real_rows:
                    self.repo.upsert_market_snapshot(d, real_rows)
                else:
                    self._seed_market(d)
            else:
                self._seed_market(d)
        if not data['sectors']:
            self._seed_sector(d)
        data = self.repo.get_dashboard(d)
        data['date'] = d
        return data
