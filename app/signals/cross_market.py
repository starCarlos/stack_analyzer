from __future__ import annotations

from datetime import date


def market_thermometer() -> list[dict]:
    return [
        {"name": "沪深300", "value": "3,980.3", "change_pct": 0.62, "unit": "%"},
        {"name": "创业板指", "value": "2,145.8", "change_pct": -0.35, "unit": "%"},
        {"name": "北向净流入", "value": "+23.5", "change_pct": 1.2, "unit": "亿"},
        {"name": "两市成交额", "value": "9865", "change_pct": -4.8, "unit": "亿"},
        {"name": "10Y国债", "value": "2.31", "change_pct": -0.4, "unit": "%"},
        {"name": "USD/CNY", "value": "7.18", "change_pct": 0.18, "unit": "%"},
    ]


def build_cross_market_impact() -> dict:
    events = [
        {
            "region": "美股",
            "event": "纳指隔夜上涨，半导体指数领涨",
            "impact": "利好",
            "a_share_sectors": ["半导体", "消费电子"],
            "a_share_symbols": ["603986.SH", "300223.SZ"],
            "reason": "风险偏好提升+海外科技链共振",
        },
        {
            "region": "日本",
            "event": "日元走弱，汽车出口预期改善",
            "impact": "中性偏利好",
            "a_share_sectors": ["汽车整车"],
            "a_share_symbols": ["000625.SZ", "601633.SH"],
            "reason": "亚洲汽车产业链景气边际改善",
        },
        {
            "region": "欧洲",
            "event": "欧洲天然气价格回落",
            "impact": "利好",
            "a_share_sectors": ["化工", "有色金属"],
            "a_share_symbols": ["600309.SH", "603799.SH"],
            "reason": "上游能源成本下降，利润率修复预期增强",
        },
    ]
    return {"date": str(date.today()), "items": events}

