# A股智能投研系统 — Claude Code 开发蓝图

> **用途**：将本文档交给 Claude Code，可直接生成对应代码。
>
> **定位**：以**预测**为核心的 FastAPI Web 应用。主页展示今日预测结果和学习报告，所有功能通过网页操作，后台调度器自动运行每日流水线。
>
> **版本**：v2.0 | 2026-03-05

---

## 〇、产品概览

### 0.1 用户看到什么

打开网页，首页就是今天的核心信息：

```
┌─────────────────────────────────────────────────────────────┐
│  A股智能投研系统                            2026-03-05 周三  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📊 今日大盘预测                                             │
│  沪深300: 看涨 ↑  置信度 68%  预测5日收益 +1.2%              │
│  市场情绪: 谨慎乐观  北向资金: +23.5亿                       │
│                                                             │
│  🎯 个股预测 TOP5                                            │
│  ┌──────────┬────┬──────┬──────┬────────────────┐           │
│  │ 标的     │方向│置信度│5日预测│关键理由         │           │
│  ├──────────┼────┼──────┼──────┼────────────────┤           │
│  │ 贵州茅台 │ ↑  │ 72% │+1.5% │PE低位+MACD金叉  │           │
│  │ 宁德时代 │ ↑  │ 65% │+2.1% │北向资金连续流入  │           │
│  │ ...      │    │      │      │                │           │
│  └──────────┴────┴──────┴──────┴────────────────┘           │
│                                                             │
│  📈 板块预测                                                 │
│  看好: 白酒(72%) 新能源(65%)  看空: 房地产(58%)              │
│                                                             │
│  📰 今日重要新闻 (3条)                                       │
│  • [利好] 央行下调MLF利率10bp → 影响: 银行/地产 ↑            │
│  • [利空] 某新能源补贴政策到期 → 影响: 光伏 ↓                │
│  • [中性] 证监会完善退市制度 → 影响: ST股 ↓                  │
│                                                             │
│  📝 系统学习报告                                             │
│  昨日预测命中率: 65%  本周: 62%  本月: 58%                   │
│  模型自动调优: forecast_model.momentum_weight 0.30→0.32      │
│  纸面账户: 累计收益 +5.2%  最大回撤 -3.1%                    │
│                                                             │
│  ──────────────── 导航 ────────────────                      │
│  [个股分析] [板块分析] [新闻中心] [历史回放]                  │
│  [预测记录] [学习报告] [纸面账户] [系统设置]                  │
└─────────────────────────────────────────────────────────────┘
```

### 0.2 核心功能

| 功能 | 说明 |
|------|------|
| **预测（核心）** | 个股/板块/大盘的多窗口预测，每日自动生成 |
| **新闻获取** | 自动抓取+LLM打分，识别影响方向和标的 |
| **行情分析** | 技术面+基本面+估值+资金面综合分析 |
| **历史回放** | 选择历史日期，用当时的数据重新生成预测，对比实际走势 |
| **自动学习** | 预测→评估→调参闭环，历史回放补充训练样本 |
| **人物Skill交叉分析** | 多个 advisor 角色独立分析，综合投票给出建议 |
| **纸面交易** | 虚拟账户跟踪系统建议的执行效果 |

### 0.3 技术栈

```
后端: Python 3.11+ / FastAPI / SQLite / APScheduler
前端: Jinja2 模板 + Tailwind CSS + HTMX（轻量，无需前端构建）
数据: AKShare（主力）/ Yahoo Finance（备用）
LLM:  OpenAI 兼容接口（支持自定义 base_url）
```

选 Jinja2+HTMX 而不是 React 的原因：项目核心价值在后端分析能力，前端以展示为主，不需要复杂交互。HTMX 可以实现局部刷新、加载动画等，够用且不增加构建复杂度。

---

## 一、项目结构

```
project_root/
├── main.py                          # FastAPI 入口 + 调度器
├── cli.py                           # 命令行工具（少量运维命令）
├── requirements.txt
├── .env.example
│
├── config/
│   ├── symbols.yaml                 # 标的与板块配置
│   ├── profiles.yaml                # advisor persona 定义
│   ├── forecast_model.yaml          # 预测模型参数
│   ├── valuation.yaml               # 估值规则 + event_llm
│   ├── decision_rules.json          # 硬性规则（不可自动修改）
│   └── push_config.yaml             # 推送渠道（可选）
│
├── app/
│   ├── __init__.py
│   │
│   ├── web/                         # 🌐 网页路由与模板
│   │   ├── router.py                # 所有页面路由
│   │   └── templates/
│   │       ├── base.html            # 布局基础模板
│   │       ├── index.html           # 首页：今日预测+学习报告
│   │       ├── stock.html           # 个股详情分析页
│   │       ├── sector.html          # 板块分析页
│   │       ├── news.html            # 新闻中心
│   │       ├── replay.html          # 历史回放页
│   │       ├── forecast_log.html    # 预测记录与评估
│   │       ├── learning.html        # 学习报告详情
│   │       ├── paper.html           # 纸面账户
│   │       ├── advisor.html         # 人物Skill交叉分析
│   │       └── settings.html        # 系统设置
│   │
│   ├── api/                         # 📡 JSON API（供 HTMX 和外部调用）
│   │   ├── forecast.py              # 预测相关 API
│   │   ├── news.py                  # 新闻 API
│   │   ├── analysis.py              # 分析 API
│   │   ├── replay.py                # 历史回放 API
│   │   ├── learning.py              # 学习报告 API
│   │   ├── paper.py                 # 纸面交易 API
│   │   ├── advisor.py               # 人物Skill API
│   │   └── system.py                # 系统状态/设置 API
│   │
│   ├── core/                        # 🧠 核心业务逻辑
│   │   ├── data_manager.py          # 数据获取与清洗（统一入口）
│   │   ├── analyzer.py              # 行情分析（技术面+基本面+估值+资金）
│   │   ├── forecaster.py            # 预测引擎（个股+板块+大盘）
│   │   ├── evaluator.py             # 预测评估
│   │   ├── learner.py               # 自动学习（评估→调参闭环）
│   │   ├── replayer.py              # 历史回放
│   │   ├── advisor_panel.py         # 人物Skill交叉分析
│   │   ├── candidate_picker.py      # 买入候选筛选
│   │   ├── paper_trader.py          # 纸面交易模拟
│   │   └── alerter.py               # 告警与推送
│   │
│   ├── llm/                         # 🤖 LLM 集成
│   │   ├── client.py                # 统一调用接口
│   │   ├── cache.py                 # 结构化缓存
│   │   ├── news_scorer.py           # 新闻打分
│   │   ├── policy_scorer.py         # 政策评级
│   │   └── event_analyst.py         # 估值事件多角色分析
│   │
│   ├── crawler/                     # 🕷️ 数据抓取
│   │   ├── news_crawler.py          # 新闻抓取
│   │   └── rss_fetcher.py           # RSS 订阅
│   │
│   ├── db/                          # 💾 数据库
│   │   ├── database.py              # SQLite 连接管理
│   │   └── schema.py                # 表结构
│   │
│   └── scheduler/                   # ⏰ 后台调度
│       └── jobs.py                  # 所有定时任务定义
│
├── static/                          # 静态资源
│   └── css/
│       └── app.css                  # 自定义样式（Tailwind CDN + 少量自定义）
│
└── output/                          # 运行时产物（gitignore）
    ├── news.db                      # 新闻数据库
    └── tracking.db                  # 预测/行情/交易/归档统一库
```

**和之前的区别**：没有 `scripts/pipeline/` 下的 30 多个文件。流水线逻辑在 `app/scheduler/jobs.py` 里用 Python 函数组织，由 APScheduler 调度，不需要 shell 脚本。`cli.py` 只保留少量运维命令（初始化数据库、手动回填数据、手动触发流水线）。

---

## 二、配置文件

### 2.1 `.env.example`

```bash
# ===== 基础 =====
APP_HOST=0.0.0.0
APP_PORT=1236
APP_TITLE=A股智能投研系统

# ===== 数据源 =====
DATA_PROVIDER=akshare        # akshare | yahoo
DATA_DIR=output

# ===== 标的（也可在 config/symbols.yaml 中配置）=====
SYMBOLS=600519.SH,300750.SZ,000858.SZ
BENCHMARK=000300.SH

# ===== LLM =====
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT=60

# ===== 功能开关 =====
ENABLE_NEWS_LLM=true         # 新闻 LLM 打分
ENABLE_POLICY_LLM=true       # 政策 LLM 评级
ENABLE_CANDIDATE_LLM=true    # 买入候选 LLM 风控
ENABLE_ADVISOR_PANEL=true    # 人物Skill交叉分析
ENABLE_PAPER_TRADING=true    # 纸面交易
ENABLE_AUTO_LEARN=true       # 自动学习调参
ENABLE_PUSH=false            # 推送告警

# ===== 调度 =====
CRAWL_INTERVAL_HOURS=4
PIPELINE_TIME=18:30          # 每日流水线执行时间
PIPELINE_WEEKDAYS=mon-fri
```

### 2.2 `config/symbols.yaml`

```yaml
universe:
  - symbol: "600519.SH"
    name: "贵州茅台"
    market: cn-a
    sector: "白酒"
    weight: 0.4
  - symbol: "300750.SZ"
    name: "宁德时代"
    market: cn-a
    sector: "新能源"
    weight: 0.3
  - symbol: "000858.SZ"
    name: "五粮液"
    market: cn-a
    sector: "白酒"
    weight: 0.3

sectors:
  - name: "白酒"
    proxy_index: "BK0477"    # 东方财富板块代码
    members: ["600519.SH", "000858.SZ", "000568.SZ"]
  - name: "新能源"
    proxy_index: "BK0478"
    members: ["300750.SZ", "002594.SZ", "601012.SH"]

benchmark:
  symbol: "000300.SH"
  name: "沪深300"
```

### 2.3 `config/profiles.yaml`

```yaml
# 人物 Skill 交叉分析的 advisor 定义
advisors:
  - id: fundamental
    name: "基本面分析师"
    focus: "营收/利润/ROE/现金流，关注企业内在价值"
    prompt_prefix: >
      你是一位专注基本面分析的投资分析师。你关注企业的营收增长、
      利润质量、ROE变化趋势和现金流健康度。忽略短期价格波动，
      聚焦企业3-5年的内在价值变化。

  - id: technical
    name: "技术面分析师"
    focus: "K线形态/均线/MACD/RSI/成交量，关注趋势和买卖时机"
    prompt_prefix: >
      你是一位技术分析专家。你通过均线系统、MACD、RSI、KDJ等
      指标判断趋势方向和强度，识别买卖信号和关键支撑阻力位。

  - id: policy
    name: "政策分析师"
    focus: "宏观政策/行业监管/财政货币政策对市场的影响"
    prompt_prefix: >
      你是一位宏观政策分析师。你关注央行货币政策、产业政策方向、
      监管态度变化，判断政策对行业和个股的影响方向和力度。

  - id: risk
    name: "风险分析师"
    focus: "下行风险/黑天鹅/财务造假/质押/减持/诉讼"
    prompt_prefix: >
      你是一位风险分析师。你专注识别投资中的下行风险，包括财务
      造假信号、大股东质押和减持、诉讼风险、行业政策风险等。
      你的职责是找出别人忽略的风险因素。

consensus_rule:
  min_agreement: 3           # 至少3个advisor同方向才算有效信号
  fallback: "hold"           # 不满足一致性时默认观望
```

### 2.4 `config/decision_rules.json`

```json
{
  "_comment": "硬性规则，不可被系统自动修改",
  "position": {
    "max_single_pct": 0.10,
    "max_total_pct": 0.60,
    "max_daily_buy_pct": 0.05
  },
  "filter": {
    "exclude_st": true,
    "min_listing_days": 365,
    "min_market_cap_billion": 10,
    "index_scope": ["000300.SH", "000905.SH"]
  },
  "stop_loss_pct": 0.08,
  "market_brake": {
    "benchmark_below_ma20_no_new_buy": true
  },
  "confidence_threshold": 0.60,
  "a_share_rules": {
    "t_plus_1": true,
    "lot_size": 100,
    "commission_rate": 0.0003,
    "commission_min": 5.0,
    "stamp_tax_rate": 0.0005,
    "limit_up_down": {
      "main_board": 0.10,
      "star_gem": 0.20,
      "st": 0.05
    }
  }
}
```

### 2.5 `config/forecast_model.yaml`

```yaml
price:
  windows: [5, 10, 20]          # 预测窗口（交易日）
  method: ensemble
  weights:
    momentum: 0.30
    mean_reversion: 0.30
    fundamental: 0.40

sector:
  windows: [10, 20]
  enabled: true

market:                          # 大盘预测
  benchmark: "000300.SH"
  windows: [5, 10]
  features_extra:
    - total_turnover
    - north_flow_ma5
    - advance_decline_ratio
```

---

## 三、数据库 Schema

> 两个 SQLite 文件：`news.db`（新闻专用，避免锁竞争）和 `tracking.db`（其他所有）。

### 3.1 `app/db/schema.py`

```python
"""
数据库表结构。启动时调用 ensure_tables() 自动建表。
"""

# ── tracking.db 的表 ──
TRACKING_TABLES = {

"market_price_bars": """
CREATE TABLE IF NOT EXISTS market_price_bars (
    symbol      TEXT NOT NULL,
    trade_date  TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, amount REAL, turnover REAL,
    adj_factor  REAL,
    source      TEXT DEFAULT 'akshare',
    PRIMARY KEY (symbol, trade_date, source)
);""",

"fundamentals": """
CREATE TABLE IF NOT EXISTS fundamentals (
    symbol      TEXT NOT NULL,
    report_date TEXT NOT NULL,
    revenue REAL, net_profit REAL, gross_margin REAL, net_margin REAL,
    roe REAL, debt_ratio REAL, ocf REAL,
    pe_ttm REAL, pb REAL, ps_ttm REAL, dividend_yield REAL, market_cap REAL,
    source      TEXT DEFAULT 'akshare',
    updated_at  TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, report_date, source)
);""",

"north_flow": """
CREATE TABLE IF NOT EXISTS north_flow (
    trade_date      TEXT PRIMARY KEY,
    net_buy_amount  REAL,
    buy_amount REAL, sell_amount REAL,
    updated_at      TEXT DEFAULT (datetime('now'))
);""",

"price_forecasts": """
CREATE TABLE IF NOT EXISTS price_forecasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT NOT NULL DEFAULT 'stock',  -- stock / sector / market
    symbol          TEXT NOT NULL,
    forecast_date   TEXT NOT NULL,
    target_date     TEXT NOT NULL,
    window_days     INTEGER NOT NULL,
    predicted_return REAL,
    predicted_direction TEXT,    -- up / down / flat
    confidence      REAL,
    method          TEXT,
    features_json   TEXT,
    as_of_date      TEXT,       -- 历史回放用
    created_at      TEXT DEFAULT (datetime('now'))
);""",

"forecast_evaluations": """
CREATE TABLE IF NOT EXISTS forecast_evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    forecast_id     INTEGER REFERENCES price_forecasts(id),
    symbol          TEXT NOT NULL,
    target_type     TEXT DEFAULT 'stock',
    window_days     INTEGER,
    predicted_return REAL,
    actual_return   REAL,
    direction_hit   INTEGER,    -- 1/0
    abs_error       REAL,
    evaluated_at    TEXT DEFAULT (datetime('now'))
);""",

"advisor_analyses": """
CREATE TABLE IF NOT EXISTS advisor_analyses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    analysis_date   TEXT NOT NULL,
    advisor_id      TEXT NOT NULL,   -- fundamental/technical/policy/risk
    direction       TEXT,            -- bullish/bearish/neutral
    confidence      REAL,
    reasoning       TEXT,
    key_factors     TEXT,            -- JSON array
    created_at      TEXT DEFAULT (datetime('now'))
);""",

"advisor_consensus": """
CREATE TABLE IF NOT EXISTS advisor_consensus (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    analysis_date   TEXT NOT NULL,
    consensus_direction TEXT,        -- bullish/bearish/hold
    agreement_ratio REAL,            -- 0-1
    advisor_details TEXT,            -- JSON: 各advisor结果
    final_suggestion TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(symbol, analysis_date)
);""",

"paper_trades": """
CREATE TABLE IF NOT EXISTS paper_trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    trade_date  TEXT NOT NULL,
    action      TEXT NOT NULL,       -- buy / sell
    quantity    INTEGER,
    price       REAL,
    commission  REAL,
    stamp_tax   REAL,
    reason      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);""",

"paper_snapshots": """
CREATE TABLE IF NOT EXISTS paper_snapshots (
    snapshot_date   TEXT PRIMARY KEY,
    cash            REAL,
    positions_json  TEXT,
    total_value     REAL,
    daily_return    REAL,
    cumulative_return REAL,
    max_drawdown    REAL
);""",

"learning_log": """
CREATE TABLE IF NOT EXISTS learning_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    log_date        TEXT NOT NULL,
    evaluated_count INTEGER,
    hit_rate        REAL,
    hit_rate_by_window TEXT,         -- JSON
    hit_rate_by_symbol TEXT,         -- JSON
    param_changes   TEXT,            -- JSON: 本次自动调参详情
    notes           TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);""",

"parameter_audit": """
CREATE TABLE IF NOT EXISTS parameter_audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    change_date TEXT NOT NULL,
    config_file TEXT NOT NULL,
    param_path  TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    reason      TEXT,
    source      TEXT,               -- auto / manual
    created_at  TEXT DEFAULT (datetime('now'))
);""",

"replay_sessions": """
CREATE TABLE IF NOT EXISTS replay_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name    TEXT,
    as_of_start     TEXT NOT NULL,
    as_of_end       TEXT NOT NULL,
    symbols         TEXT,            -- JSON array
    total_forecasts INTEGER,
    hit_rate        REAL,
    sharpe          REAL,
    max_drawdown    REAL,
    details_json    TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);""",

"llm_cache": """
CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key   TEXT PRIMARY KEY,
    task_type   TEXT NOT NULL,       -- news_score / policy_score / advisor / event
    response    TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);""",

}

# ── news.db 的表 ──
NEWS_TABLES = {

"articles": """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    normalized_title TEXT,
    content         TEXT,
    source          TEXT,
    publish_time    TEXT,
    crawl_time      TEXT DEFAULT (datetime('now')),
    importance      INTEGER DEFAULT 0,
    symbols_json    TEXT,
    direction       TEXT,
    llm_score       REAL,
    llm_summary     TEXT,
    UNIQUE(normalized_title, source)
);""",

}
```

---

## 四、核心模块规格

### 4.1 `app/core/data_manager.py` — 数据管理（统一入口）

```
职责：所有数据获取、存储、清洗的统一入口

公开方法：
  get_bars(symbol, start, end, adjust='qfq') -> DataFrame
    # 优先从 DB 读，缺失部分从 AKShare 补并入库
    # 列: trade_date, open, high, low, close, volume, amount, turnover

  get_fundamentals(symbol) -> dict
    # 最新财务数据 + PE/PB 百分位

  get_north_flow(days=30) -> DataFrame
    # 北向资金，含 3日/5日/10日累计

  get_index_components(index_symbol) -> List[str]
    # 指数成分股列表

  refresh_all(symbols) -> dict
    # 刷新所有标的的行情+基本面+北向，返回状态摘要

内部处理（A股特有）：
  代码映射：600519.SH → sh600519（AKShare）→ 600519.SS（Yahoo）
  复权：qfq=前复权(技术分析), hfq=后复权(收益计算)
  涨跌停标记：在 DataFrame 加 limit_up/limit_down 列
  停牌：不填充，保留 NaN
```

### 4.2 `app/core/analyzer.py` — 行情分析

```
职责：对单个标的做全维度分析

analyze(symbol) -> dict:
  返回结构：
  {
    "symbol": "600519.SH",
    "name": "贵州茅台",
    "price": {"close": 1680, "change_1d": 0.5, "change_5d": 2.1, "change_20d": -1.3},
    "technical": {
      "ma": {"ma5": .., "ma10": .., "ma20": .., "ma60": ..},
      "macd": {"dif": .., "dea": .., "hist": .., "signal": "golden_cross"},
      "rsi_14": 55,
      "kdj": {"k": 60, "d": 55, "j": 70},
      "bollinger": {"upper": .., "middle": .., "lower": .., "position": 0.6},
      "volume_ratio_5": 1.2,
      "trend": "uptrend"            # uptrend/downtrend/sideways
    },
    "fundamental": {
      "pe_ttm": 28.5, "pe_percentile": 0.35,
      "pb": 8.2, "pb_percentile": 0.42,
      "roe": 0.31, "revenue_growth_yoy": 0.12,
      "net_profit_growth_yoy": 0.08, "ocf_to_profit": 1.1
    },
    "valuation_zone": "moderate",    # cheap(<25%) / moderate / expensive(>75%)
    "north_flow": {"net_3d": 5.2, "net_10d": -3.1, "trend": "inflow"},
    "risk_flags": ["解禁: 2026-03-15, 5%股份"]
  }

analyze_sector(sector_name) -> dict:
  对板块做聚合分析：成员平均涨幅、资金流向、估值中位数

analyze_market() -> dict:
  大盘分析：指数位置、MA状态、成交额、北向、涨跌家数比
```

### 4.3 `app/core/forecaster.py` — 预测引擎（核心）

```
职责：对个股/板块/大盘生成预测，写入 price_forecasts 表

forecast_stock(symbol, as_of_date=None) -> dict:
  输入：标的代码，可选 as_of_date（历史回放时传入）
  输出：
  {
    "symbol": "600519.SH",
    "forecast_date": "2026-03-05",
    "predictions": [
      {"window": 5,  "return": 0.015, "direction": "up", "confidence": 0.72},
      {"window": 10, "return": 0.022, "direction": "up", "confidence": 0.65},
      {"window": 20, "return": 0.018, "direction": "up", "confidence": 0.58}
    ],
    "key_factors": ["PE百分位35%偏低", "MACD金叉", "北向3日净流入5.2亿"],
    "method": "ensemble"
  }

  集成模型：
    momentum子模型(weight=0.30):
      输入: MA趋势(MA5>MA10>MA20?), MACD方向, RSI位置, 量比
      逻辑: 趋势延续假设，均线多头排列+MACD正→预测上涨
      输出: predicted_return, confidence

    mean_reversion子模型(weight=0.30):
      输入: PE/PB百分位, 布林带位置, RSI极值
      逻辑: 估值均值回归，PE百分位<20%→预测上涨，>80%→预测下跌
      输出: predicted_return, confidence

    fundamental子模型(weight=0.40):
      输入: ROE稳定性, 营收增速, 利润增速, 现金流匹配度
      逻辑: 基本面趋势，连续正增长+ROE>15%→看多
      输出: predicted_return, confidence

    集成:
      return = sum(weight_i * return_i)
      confidence = sum(weight_i * conf_i)
      direction = 'up' if return > 0.005 else 'down' if < -0.005 else 'flat'

forecast_sector(sector_name, as_of_date=None) -> dict:
  对板块成员分别预测后取加权平均

forecast_market(as_of_date=None) -> dict:
  大盘预测，额外使用: 成交额趋势、北向资金MA、涨跌家数比

forecast_all(as_of_date=None) -> dict:
  对所有标的+板块+大盘生成预测，返回汇总结果
  这是每日流水线的核心调用
```

### 4.4 `app/core/evaluator.py` — 预测评估

```
职责：对到期预测做准确性评估

evaluate_due_forecasts() -> dict:
  1. 查 price_forecasts 中 target_date <= today 且未评估的
  2. 获取实际价格，计算 actual_return
  3. 写入 forecast_evaluations 表
  4. 返回:
  {
    "evaluated_count": 15,
    "overall_hit_rate": 0.65,
    "by_type": {"stock": 0.62, "sector": 0.70, "market": 0.60},
    "by_window": {"5": 0.58, "10": 0.65, "20": 0.70},
    "by_symbol": {"600519.SH": {"hit_rate": 0.72, "mae": 0.02}},
    "trend": {"this_week": 0.65, "this_month": 0.60, "total": 0.58}
  }

get_forecast_history(symbol=None, days=30) -> List[dict]:
  查询历史预测记录（用于前端展示）
```

### 4.5 `app/core/learner.py` — 自动学习

```
职责：基于评估结果自动调整模型参数

learn_from_evaluations() -> dict:
  1. 读取近 N 天的 forecast_evaluations
  2. 按子模型拆解命中率:
     - momentum 命中 70% → 表现好
     - mean_reversion 命中 45% → 表现差
     - fundamental 命中 65% → 正常
  3. 调整 forecast_model.yaml 的 weights:
     - 表现好的 +0.02，表现差的 -0.02
     - 不超过 [0.10, 0.60] 范围
     - 权重之和归一化为 1.0
  4. 所有变更写入 parameter_audit 表
  5. 返回变更详情

安全阀：
  - 单次 weight 变动不超过 ±0.05
  - 连续 3 天同向才落盘
  - 评估样本 < 10 条时不调参

learn_from_history(start_date, end_date) -> dict:
  历史回放学习：
  1. 对 [start, end] 每个交易日：
     - 用 as_of_date 生成预测
     - 评估预测结果
  2. 积累足够评估样本后调用 learn_from_evaluations()
  3. 返回回放统计

build_daily_report() -> dict:
  生成每日学习报告：
  {
    "date": "2026-03-05",
    "evaluations": { ... 评估结果 ... },
    "param_changes": [ ... 参数变更 ... ],
    "paper_account": { ... 纸面账户状态 ... },
    "system_health": { "data_quality": 0.95, "forecast_count": 15, "issues": [] }
  }
```

### 4.6 `app/core/replayer.py` — 历史回放

```
职责：选择历史日期区间，重新生成预测并对比实际走势

replay(start_date, end_date, symbols=None) -> dict:
  输入：起止日期，可选标的（默认全部）
  流程：
    for each trading_day in [start, end]:
      forecaster.forecast_all(as_of_date=trading_day)   # 只用当天及之前的数据
    evaluator.evaluate_due_forecasts()                    # 评估所有到期预测
  输出：
  {
    "session_id": 42,
    "period": "2025-01-01 ~ 2025-06-30",
    "total_forecasts": 450,
    "hit_rate": 0.62,
    "by_symbol": { ... },
    "by_window": { ... },
    "equity_curve": [ ... ],        # 如果跟踪虚拟交易
    "sharpe": 0.85,
    "max_drawdown": -0.12
  }

  写入 replay_sessions 表，前端可查看历史回放记录

get_replay_list() -> List[dict]:
  查询历史回放会话列表
```

### 4.7 `app/core/advisor_panel.py` — 人物 Skill 交叉分析

```
职责：多个 advisor 独立分析同一标的，投票得出共识

analyze(symbol) -> dict:
  1. 获取标的的分析数据（from analyzer.py）
  2. 对每个 advisor（config/profiles.yaml）：
     - 构造 prompt: advisor.prompt_prefix + 标的数据 + "请给出方向和理由"
     - 调用 LLM，要求返回 JSON:
       {direction, confidence, key_factors: [], reasoning}
     - 写入 advisor_analyses 表
  3. 投票共识：
     - 统计 bullish / bearish / neutral 数量
     - agreement_ratio = max_count / total_advisors
     - 满足 min_agreement → 采纳多数方向
     - 不满足 → fallback 为 "hold"
  4. 写入 advisor_consensus 表
  5. 返回:
  {
    "symbol": "600519.SH",
    "date": "2026-03-05",
    "advisors": [
      {"id": "fundamental", "name": "基本面分析师",
       "direction": "bullish", "confidence": 0.75,
       "key_factors": ["ROE持续>30%", "PE百分位低"],
       "reasoning": "..."},
      {"id": "technical", ...},
      {"id": "policy", ...},
      {"id": "risk", ...}
    ],
    "consensus": {
      "direction": "bullish",
      "agreement": 0.75,
      "suggestion": "3个看多1个中性，共识偏多，可考虑建仓"
    }
  }
```

### 4.8 `app/core/paper_trader.py` — 纸面交易

```
职责：用虚拟资金跟踪系统建议的执行效果

初始: cash=1,000,000, positions={}

execute_daily(candidates, current_prices) -> dict:
  1. 检查止损：遍历持仓，跌幅>stop_loss_pct的卖出
  2. 检查买入条件：
     - 总仓位 < max_total_pct
     - 大盘未跌破 MA20（如启用）
  3. 对每个 candidate:
     - 单只 < max_single_pct
     - 当日买入总额 < max_daily_buy_pct
     - 计算可买股数（向下取整到 lot_size=100）
     - 扣除佣金
  4. 记录 paper_trades，更新 paper_snapshots
  5. 返回今日交易摘要和账户状态

get_status() -> dict:
  当前持仓、现金、总市值、累计收益、最大回撤
```

---

## 五、网页路由与模板

### 5.1 `app/web/router.py` — 页面路由

```python
"""
所有网页路由。使用 Jinja2 模板 + HTMX 局部刷新。
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")

@router.get("/")
async def index(request: Request):
    """首页：今日预测 + 学习报告 + 重要新闻"""
    # 获取今日预测摘要（个股TOP5 + 板块 + 大盘）
    # 获取最新学习报告
    # 获取今日重要新闻 TOP5
    # 获取纸面账户摘要
    return templates.TemplateResponse("index.html", {
        "request": request,
        "forecast_summary": ...,
        "learning_report": ...,
        "top_news": ...,
        "paper_status": ...
    })

@router.get("/stock/{symbol}")
async def stock_detail(request: Request, symbol: str):
    """个股详情：完整分析 + 历史预测 + advisor 观点"""
    # analyzer.analyze(symbol)
    # forecaster 最近预测
    # advisor_panel 最近分析
    # 预测命中率历史
    ...

@router.get("/sector/{name}")
async def sector_detail(request: Request, name: str):
    """板块分析：板块预测 + 成员表现 + 资金流向"""
    ...

@router.get("/news")
async def news_center(request: Request):
    """新闻中心：按时间/重要性/标的筛选"""
    ...

@router.get("/replay")
async def replay_page(request: Request):
    """历史回放：选择日期范围触发回放，查看结果"""
    ...

@router.get("/forecast-log")
async def forecast_log(request: Request):
    """预测记录：所有历史预测及其评估结果"""
    ...

@router.get("/learning")
async def learning_page(request: Request):
    """学习报告：命中率趋势、参数变更历史、模型表现"""
    ...

@router.get("/paper")
async def paper_page(request: Request):
    """纸面账户：持仓、交易记录、收益曲线"""
    ...

@router.get("/advisor/{symbol}")
async def advisor_page(request: Request, symbol: str):
    """人物Skill分析：各advisor观点对比"""
    ...

@router.get("/settings")
async def settings_page(request: Request):
    """系统设置：标的管理、功能开关、LLM配置"""
    ...
```

### 5.2 `app/web/templates/base.html` — 基础模板

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}A股智能投研系统{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@2.0.4"></script>
    <link rel="stylesheet" href="/static/css/app.css">
</head>
<body class="bg-gray-950 text-gray-200 min-h-screen">
    <!-- 顶部导航 -->
    <nav class="border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <a href="/" class="text-lg font-bold text-white">📊 A股智能投研</a>
        <div class="flex gap-4 text-sm">
            <a href="/" class="hover:text-white">首页</a>
            <a href="/news" class="hover:text-white">新闻</a>
            <a href="/replay" class="hover:text-white">回放</a>
            <a href="/forecast-log" class="hover:text-white">预测</a>
            <a href="/learning" class="hover:text-white">学习</a>
            <a href="/paper" class="hover:text-white">纸面</a>
            <a href="/settings" class="hover:text-white">设置</a>
        </div>
    </nav>

    <!-- 主内容 -->
    <main class="max-w-6xl mx-auto px-6 py-6">
        {% block content %}{% endblock %}
    </main>

    <!-- HTMX 加载指示器 -->
    <div id="loading" class="htmx-indicator fixed top-0 left-0 w-full h-1 bg-blue-500"></div>
</body>
</html>
```

### 5.3 首页模板要点 `index.html`

```
首页分为 5 个卡片区域（从上到下）：

1. 大盘预测卡片
   - 沪深300方向、置信度、预测收益
   - 北向资金、成交额、市场情绪
   - 大盘MA20状态指示

2. 个股预测 TOP5 表格
   - 按置信度排序的前5个预测
   - 列: 标的、方向(↑↓→)、置信度、5日预测收益、关键理由
   - 点击标的名跳转到个股详情页

3. 板块预测卡片
   - 看好/看空板块各2-3个
   - 附带板块预测置信度

4. 今日重要新闻（3-5条）
   - [利好/利空/中性] 标签 + 标题 + 影响标的
   - 点击展开 LLM 分析摘要

5. 系统学习报告摘要
   - 命中率：昨日/本周/本月
   - 最近一次参数调整
   - 纸面账户：累计收益、最大回撤
   - 链接到详细学习报告页

HTMX 用法：
  首页加载时渲染服务端数据（SSR）
  "刷新预测" 按钮用 hx-get="/api/forecast/refresh" hx-target="#forecast-section"
  新闻展开用 hx-get="/api/news/{id}/detail" hx-target="this"
```

---

## 六、JSON API

```python
# app/api/forecast.py
GET  /api/forecast/today              # 今日所有预测摘要
GET  /api/forecast/stock/{symbol}     # 个股预测详情
GET  /api/forecast/sector/{name}      # 板块预测
GET  /api/forecast/market             # 大盘预测
POST /api/forecast/refresh            # 手动触发重新预测

# app/api/news.py
GET  /api/news/today                  # 今日新闻（含LLM评分）
GET  /api/news/{id}                   # 新闻详情
GET  /api/news/by-symbol/{symbol}     # 按标的筛选

# app/api/analysis.py
GET  /api/analysis/stock/{symbol}     # 个股完整分析
GET  /api/analysis/sector/{name}      # 板块分析
GET  /api/analysis/market             # 大盘分析

# app/api/replay.py
POST /api/replay/run                  # 触发历史回放 {start, end, symbols}
GET  /api/replay/sessions             # 回放会话列表
GET  /api/replay/{session_id}         # 回放结果详情

# app/api/learning.py
GET  /api/learning/today              # 今日学习报告
GET  /api/learning/history?days=30    # 学习趋势
GET  /api/learning/params             # 参数变更历史

# app/api/paper.py
GET  /api/paper/status                # 账户状态
GET  /api/paper/trades?days=30        # 交易记录
GET  /api/paper/equity-curve          # 收益曲线数据

# app/api/advisor.py
GET  /api/advisor/{symbol}            # 最新 advisor 分析
POST /api/advisor/{symbol}/refresh    # 重新触发分析

# app/api/system.py
GET  /api/system/health               # 系统健康（数据新鲜度、LLM状态）
GET  /api/system/config               # 当前配置摘要
POST /api/system/config               # 更新配置（仅非硬性规则部分）
```

---

## 七、后台调度

### 7.1 `app/scheduler/jobs.py`

```python
"""
所有后台定时任务。由 main.py 的 APScheduler 调度。
"""

async def daily_pipeline():
    """
    每日流水线（工作日 18:30 自动执行）。
    也可通过 API 手动触发。
    """
    from app.core import data_manager, analyzer, forecaster, evaluator, learner
    from app.core import candidate_picker, paper_trader, alerter, advisor_panel
    from app.crawler import news_crawler

    log = {"date": today(), "steps": []}

    # 1. 数据刷新
    step("refresh_data", data_manager.refresh_all(get_symbols()))

    # 2. 新闻抓取 + LLM 打分
    step("crawl_news", news_crawler.crawl_today())

    # 3. 生成预测（个股+板块+大盘）
    step("forecast", forecaster.forecast_all())

    # 4. 评估到期预测
    step("evaluate", evaluator.evaluate_due_forecasts())

    # 5. 自动学习调参
    if ENABLE_AUTO_LEARN:
        step("learn", learner.learn_from_evaluations())

    # 6. 人物Skill交叉分析（对候选标的）
    if ENABLE_ADVISOR_PANEL:
        for symbol in get_top_candidates():
            step(f"advisor_{symbol}", advisor_panel.analyze(symbol))

    # 7. 买入候选筛选
    step("candidates", candidate_picker.pick())

    # 8. 纸面交易执行
    if ENABLE_PAPER_TRADING:
        step("paper_trade", paper_trader.execute_daily(...))

    # 9. 生成学习报告
    step("learning_report", learner.build_daily_report())

    # 10. 告警推送（可选）
    if ENABLE_PUSH:
        step("alert", alerter.check_and_push())

    # 写入 learning_log
    save_pipeline_log(log)


async def crawl_news_job():
    """定时抓取新闻（每 N 小时）"""
    from app.crawler import news_crawler
    news_crawler.crawl_latest()


async def history_learning_job():
    """
    历史回放学习（每周末执行一次）。
    用历史数据补充训练样本。
    """
    from app.core.learner import learn_from_history
    # 回放最近未覆盖的日期区间
    learn_from_history(start_date=..., end_date=...)
```

### 7.2 `main.py`

```python
"""
应用入口。
启动: uvicorn main:app --host 0.0.0.0 --port 1236
或:   python main.py
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

load_dotenv()

from app.db.database import ensure_tables
from app.web.router import router as web_router
from app.api import forecast, news, analysis, replay, learning, paper, advisor, system
from app.scheduler.jobs import daily_pipeline, crawl_news_job, history_learning_job

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_tables()

    scheduler = AsyncIOScheduler()

    # 每日流水线（工作日）
    h, m = os.getenv("PIPELINE_TIME", "18:30").split(":")
    scheduler.add_job(daily_pipeline, "cron",
                      hour=int(h), minute=int(m),
                      day_of_week=os.getenv("PIPELINE_WEEKDAYS", "mon-fri"),
                      id="daily_pipeline")

    # 新闻抓取
    scheduler.add_job(crawl_news_job, "interval",
                      hours=int(os.getenv("CRAWL_INTERVAL_HOURS", "4")),
                      id="crawl_news")

    # 历史学习（每周六）
    if os.getenv("ENABLE_AUTO_LEARN") == "true":
        scheduler.add_job(history_learning_job, "cron",
                          day_of_week="sat", hour=10,
                          id="history_learning")

    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title=os.getenv("APP_TITLE", "A股智能投研系统"), lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(web_router)                          # 网页
app.include_router(forecast.router, prefix="/api")      # API
app.include_router(news.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(replay.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(paper.router, prefix="/api")
app.include_router(advisor.router, prefix="/api")
app.include_router(system.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,
                host=os.getenv("APP_HOST", "0.0.0.0"),
                port=int(os.getenv("APP_PORT", "1236")))
```

---

## 八、CLI（仅运维用，3个命令）

### `cli.py`

```python
"""
运维命令行。日常使用不需要，只在初始化和手动运维时用。

用法:
  python cli.py init                    # 初始化数据库+拉取初始数据
  python cli.py backfill --start 2023-01-01 --end 2025-12-31   # 回填历史数据
  python cli.py pipeline                # 手动触发一次流水线
  python cli.py replay --start 2025-01-01 --end 2025-06-30     # 手动历史回放
"""
import argparse

def cmd_init():
    """初始化：建表 + 拉取所有标的的历史数据"""
    ...

def cmd_backfill(start, end):
    """回填：历史行情+新闻+基本面"""
    ...

def cmd_pipeline():
    """手动执行一次每日流水线"""
    import asyncio
    from app.scheduler.jobs import daily_pipeline
    asyncio.run(daily_pipeline())

def cmd_replay(start, end, symbols=None):
    """手动历史回放"""
    ...

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A股投研系统 CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("init", help="初始化数据库和数据")

    bf = sub.add_parser("backfill", help="回填历史数据")
    bf.add_argument("--start", required=True)
    bf.add_argument("--end", required=True)

    sub.add_parser("pipeline", help="手动触发流水线")

    rp = sub.add_parser("replay", help="历史回放")
    rp.add_argument("--start", required=True)
    rp.add_argument("--end", required=True)
    rp.add_argument("--symbols", default=None)

    args = parser.parse_args()
    # dispatch...
```

---

## 九、开发顺序

```
Phase 1: 骨架（1天）
  main.py + 目录结构 + config/ 所有配置文件
  app/db/ 建表
  base.html 模板 + 空白首页
  → 验证: 启动后能打开空白首页

Phase 2: 数据层（2天）
  app/core/data_manager.py
  app/crawler/news_crawler.py
  cli.py init + backfill
  → 验证: python cli.py init 后 DB 有数据

Phase 3: 分析与预测（3天）
  app/core/analyzer.py
  app/core/forecaster.py
  app/api/forecast.py + analysis.py
  → 验证: GET /api/forecast/today 返回预测 JSON

Phase 4: LLM 集成（2天）
  app/llm/ 全部
  新闻打分、政策评级集成到 crawler 和 signal 流程
  → 验证: 新闻列表带 llm_score

Phase 5: 首页与核心页面（2天）
  index.html 完整实现
  stock.html + sector.html
  news.html
  → 验证: 首页展示今日预测和新闻

Phase 6: 评估与学习（2天）
  app/core/evaluator.py
  app/core/learner.py
  learning.html + forecast_log.html
  → 验证: 学习页面展示命中率趋势

Phase 7: 历史回放（2天）
  app/core/replayer.py
  replay.html
  app/api/replay.py
  → 验证: 选日期范围执行回放，页面展示结果

Phase 8: Advisor + 纸面交易（2天）
  app/core/advisor_panel.py
  app/core/paper_trader.py
  advisor.html + paper.html
  → 验证: advisor 页面展示4个角色观点，纸面有交易记录

Phase 9: 调度与自动化（1天）
  app/scheduler/jobs.py
  daily_pipeline 完整串联
  settings.html
  → 验证: 手动 python cli.py pipeline 完整跑通

Phase 10: 收尾（1天）
  告警推送（可选）
  错误处理与日志
  README.md
  → 验证: 连续运行3天无报错
```

---

## 十、验证清单

```
□ python main.py 启动无报错，访问 http://localhost:1236 看到首页
□ 首页展示今日大盘预测、个股TOP5、板块预测、重要新闻、学习摘要
□ 点击个股名跳转到详情页，展示完整分析和advisor观点
□ /news 页面展示带 LLM 评分的新闻列表
□ /replay 页面选择日期范围后执行回放，展示命中率和收益曲线
□ /learning 页面展示命中率趋势图和参数变更历史
□ /paper 页面展示纸面账户收益曲线和交易记录
□ python cli.py pipeline 手动执行流水线完整跑通
□ 调度器到 18:30 自动执行流水线
□ LLM 缓存生效（相同新闻不重复调用）
□ 自动学习后 forecast_model.yaml 的权重有合理变化
□ parameter_audit 表记录了所有自动参数变更
```
