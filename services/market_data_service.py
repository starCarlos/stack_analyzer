from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_pct: float
    currency: str
    source: str = "yahoo"


class MarketDataService:
    QUOTE_URL = "https://query1.finance.yahoo.com/v7/finance/quote"

    def __init__(self, timeout_seconds: int = 8) -> None:
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def to_yahoo_symbol(symbol: str) -> str:
        s = str(symbol or "").strip().upper()
        if s.endswith(".SH"):
            return s[:-3] + ".SS"
        return s

    def fetch_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        yahoo_symbols = [self.to_yahoo_symbol(s) for s in symbols if str(s).strip()]
        if not yahoo_symbols:
            return {}
        try:
            resp = requests.get(
                self.QUOTE_URL,
                params={"symbols": ",".join(yahoo_symbols)},
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            payload = resp.json()
            rows = payload.get("quoteResponse", {}).get("result", [])
            result: dict[str, Quote] = {}
            for row in rows:
                ysym = str(row.get("symbol", "")).upper()
                if not ysym:
                    continue
                raw_price = row.get("regularMarketPrice")
                raw_chg = row.get("regularMarketChangePercent")
                if raw_price is None or raw_chg is None:
                    continue
                q = Quote(
                    symbol=ysym,
                    price=float(raw_price),
                    change_pct=float(raw_chg),
                    currency=str(row.get("currency", "")),
                )
                result[ysym] = q
            return result
        except Exception:
            return {}

    def fetch_indices(self) -> list[dict[str, Any]]:
        index_map = {
            "^SSEC": "上证指数",
            "399001.SZ": "深证成指",
            "399006.SZ": "创业板指",
            "^HSI": "恒生指数",
        }
        quotes = self.fetch_quotes(list(index_map.keys()))
        rows: list[dict[str, Any]] = []
        for ysym, name in index_map.items():
            q = quotes.get(ysym.upper())
            if not q:
                continue
            rows.append(
                {
                    "index_name": name,
                    "value": q.price,
                    "change_pct": q.change_pct,
                    "source": q.source,
                }
            )
        return rows

