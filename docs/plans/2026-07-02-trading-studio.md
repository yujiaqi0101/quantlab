# Trading Studio 统一交易工作室 实施计划

> 日期：2026-07-02  
> 状态：待实施  
> 范围：将 Paper Trading / Live Trading / Replay 三模式统一为 Trading Studio，前后端一次性全量交付

---

## 一、总体目标

### 1.1 产品定位

```
Research
│
├── Observe Studio（研究观察）
├── ML Lab（模型研究）
└── Alpha Lab（因子研究）

Trading
│
└── Trading Studio（统一交易工作室）
      ├── Paper Mode   模拟交易
      ├── Live Mode    实盘交易
      └── Replay Mode  时间机器回放
```

### 1.2 核心原则

1. **Paper / Live / Replay 共用同一套 UI**，仅 Broker 不同，零学习成本
2. **Bloomberg / QuantDinger 暗色风格**，与 Observe Studio 视觉一致
3. **边界清晰**：Observe 负责研究观察，Trading Studio 负责运行执行，互不越界
4. **TradingCore 为唯一引擎**：前端所有操作经 `/api/v1/trading/*` → `TradingCore`，废弃 `DeploymentManager` 路径

### 1.3 九个 Workspace

| 序号 | Workspace | 职责 |
|---|---|---|
| 1 | Overview | 首页 Dashboard：Today's Return/PnL/Cash/Exposure/Sharpe/Drawdown |
| 2 | Market | 实时行情：Watchlist + Chart（Depth/Tick 后续增强） |
| 3 | Signals | Signal Engine 输出：Time/Symbol/Score/Confidence/Reason/Status |
| 4 | Orders | 订单全生命周期：Submitted/Accepted/Filled/Rejected |
| 5 | Positions | 实时持仓：Symbol/Qty/Cost/PnL/Holding Days |
| 6 | Portfolio | 组合分析：Exposure/Sector/Cash/Weights/Risk |
| 7 | Risk | 风险监控：VaR/Drawdown/Turnover/Concentration/Factor Exposure |
| 8 | Journal | 交易日志：每笔交易自动生成 Journal 供研究 |
| 9 | Replay | 时间机器：Timeline 点击恢复全部状态 |

---

## 二、架构设计

### 2.1 整体数据流

```
前端 TradingStudio.vue
   │  (Mode 切换: Paper / Live / Replay)
   ▼
api/trading.ts  ──HTTP──►  /api/v1/trading/*
                              │
                              ▼
                       TradingStudioService
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        TradingCore      ReplayEngine    Persistence
         (内存引擎)       (时间机器)      (paper_* 表)
              │
   ┌──────────┼──────────┐
   ▼          ▼          ▼
 PaperBroker  OMS    PortfolioBook
   │
   ▼
 (Mode 区分: Paper=模拟成交 / Live=对接实盘交易所)
```

### 2.2 三模式差异点

| 维度 | Paper Mode | Live Mode | Replay Mode |
|---|---|---|---|
| Broker | PaperBroker（模拟成交+滑点） | LiveBroker（对接 QMT/Binance） | 无 Broker，从 checkpoint 恢复 |
| 行情源 | 历史数据回放 / 实时订阅 | 实时订阅 | checkpoint 快照 |
| 持久化 | paper_* 表 + checkpoint | paper_* 表 + checkpoint | 只读 checkpoint |
| 下单 | 模拟立即成交 | 真实交易所 | 禁止下单 |
| UI 差异 | 顶部显示 "Paper Session" | 顶部显示 "Broker + Account" | 左侧显示 Timeline |

### 2.3 与现有模块的关系

| 现有模块 | 处理方式 |
|---|---|
| `api/live.py` + `api/live.ts` + `LiveStudio.vue` | **删除**，功能由 Trading Studio 替代 |
| `api/production.py` + `ProductionStudio.vue` | **保留**，Production Studio 仍负责运行时健康监控（Kill Switch/Self-Healing/Recovery），与 Trading Studio 互补 |
| `api/observe.py` + `views/observe/*` | **保留**，Observe Studio 负责研究观察，不下单 |
| `trading_core/` | **复用并增强**，新增 persistence + replay 子模块 |
| `execution/broker/paper.py` | **复用**，PaperMode 已对接 |
| `execution/core/oms/` | **复用** |
| `execution/capital/portfolio.py` | **复用** |
| `execution/paper/upgraded_broker.py` | **保留**（Bug 已修复），暂不在主路径使用 |

---

## 三、数据库设计

### 3.1 新建 5 张 paper_* 表

> 注：此处的"模拟数据"指交易状态（订单/持仓/PnL），非市场数据。市场数据仍由现有 K 线表管理，不污染。

#### 3.1.1 paper_accounts（模拟账户）

```sql
CREATE TABLE IF NOT EXISTS paper_accounts (
    strategy_id      TEXT PRIMARY KEY,
    strategy_name    TEXT NOT NULL,
    version          TEXT DEFAULT '1.0',
    mode             TEXT NOT NULL DEFAULT 'paper',  -- paper / live / replay
    initial_capital  REAL NOT NULL,
    cash             REAL NOT NULL,
    frozen_cash      REAL DEFAULT 0,
    total_value      REAL NOT NULL,
    peak_value       REAL NOT NULL,
    status           TEXT DEFAULT 'running',  -- running / paused / stopped
    started_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

#### 3.1.2 paper_positions（持仓快照）

```sql
CREATE TABLE IF NOT EXISTS paper_positions (
    strategy_id  TEXT NOT NULL,
    symbol       TEXT NOT NULL,
    direction    TEXT NOT NULL DEFAULT 'long',  -- long / short
    quantity     REAL NOT NULL,
    entry_price  REAL NOT NULL,
    entry_date   TEXT NOT NULL,
    current_price REAL DEFAULT 0,
    market_value REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    realized_pnl REAL DEFAULT 0,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (strategy_id, symbol)
);
```

#### 3.1.3 paper_orders（订单）

```sql
CREATE TABLE IF NOT EXISTS paper_orders (
    order_id      TEXT PRIMARY KEY,
    strategy_id   TEXT NOT NULL,
    symbol        TEXT NOT NULL,
    side          TEXT NOT NULL,  -- buy / sell
    order_type    TEXT DEFAULT 'market',  -- market / limit
    quantity      REAL NOT NULL,
    price         REAL,
    signal_id     TEXT,
    client_order_id TEXT,
    broker_order_id TEXT,
    status        TEXT NOT NULL,  -- new/pending_submit/submitted/partial/filled/cancelled/rejected/expired
    filled_qty    REAL DEFAULT 0,
    filled_price  REAL DEFAULT 0,
    reason        TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_paper_orders_strategy ON paper_orders(strategy_id);
CREATE INDEX IF NOT EXISTS idx_paper_orders_status ON paper_orders(status);
CREATE INDEX IF NOT EXISTS idx_paper_orders_symbol ON paper_orders(symbol);
```

#### 3.1.4 paper_trades（成交）

```sql
CREATE TABLE IF NOT EXISTS paper_trades (
    trade_id    TEXT PRIMARY KEY,
    order_id    TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    quantity    REAL NOT NULL,
    price       REAL NOT NULL,
    amount      REAL NOT NULL,
    commission  REAL DEFAULT 0,
    slippage    REAL DEFAULT 0,
    trade_date  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (order_id) REFERENCES paper_orders(order_id)
);
CREATE INDEX IF NOT EXISTS idx_paper_trades_strategy ON paper_trades(strategy_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_date ON paper_trades(trade_date);
CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);
```

#### 3.1.5 paper_snapshots（净值快照，用于 Replay + Equity Curve）

```sql
CREATE TABLE IF NOT EXISTS paper_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id   TEXT NOT NULL,
    snapshot_time TEXT NOT NULL,
    cash          REAL NOT NULL,
    position_value REAL NOT NULL,
    total_value   REAL NOT NULL,
    daily_return  REAL DEFAULT 0,
    realized_pnl  REAL DEFAULT 0,
    unrealized_pnl REAL DEFAULT 0,
    max_drawdown  REAL DEFAULT 0,
    bar_timestamp TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE(strategy_id, snapshot_time)
);
CREATE INDEX IF NOT EXISTS idx_paper_snapshots_strategy ON paper_snapshots(strategy_id);
CREATE INDEX IF NOT EXISTS idx_paper_snapshots_time ON paper_snapshots(snapshot_time);
```

### 3.2 持久化模块

新建 `quantlab/trading_core/persistence.py`：

```python
class TradingPersistence:
    """TradingCore 状态持久化到 paper_* 表"""
    def __init__(self, db_path: str): ...
    def save_account(self, strategy_id, account_dict): ...
    def load_account(self, strategy_id) -> dict: ...
    def upsert_position(self, strategy_id, symbol, position_dict): ...
    def load_positions(self, strategy_id) -> list: ...
    def insert_order(self, order_dict): ...
    def update_order_status(self, order_id, status, filled_qty, filled_price): ...
    def load_orders(self, strategy_id, active_only=False) -> list: ...
    def insert_trade(self, trade_dict): ...
    def load_trades(self, strategy_id, limit=100) -> list: ...
    def insert_snapshot(self, snapshot_dict): ...
    def load_snapshots(self, strategy_id, start_time=None, end_time=None) -> list: ...
    def list_strategies(self, mode=None) -> list: ...
    def delete_strategy(self, strategy_id): ...
```

---

## 四、后端 API 设计

### 4.1 新建 `quantlab/api/trading.py`

前缀：`/api/v1/trading`

#### 4.1.1 会话与 Mode 管理

| Method | Path | 说明 |
|---|---|---|
| GET | `/sessions` | 列出所有交易会话（含 mode 过滤） |
| POST | `/sessions` | 创建新会话（指定 mode/strategy/capital/symbols） |
| GET | `/sessions/{sid}` | 会话详情 |
| DELETE | `/sessions/{sid}` | 删除会话（停止+清理） |
| POST | `/sessions/{sid}/start` | 启动会话 |
| POST | `/sessions/{sid}/pause` | 暂停 |
| POST | `/sessions/{sid}/resume` | 恢复 |
| POST | `/sessions/{sid}/stop` | 停止 |
| GET | `/sessions/{sid}/status` | 运行时状态 |

#### 4.1.2 数据查询（9 个 Workspace 对应）

| Method | Path | Workspace |
|---|---|---|
| GET | `/sessions/{sid}/overview` | Overview |
| GET | `/sessions/{sid}/market?symbols=` | Market |
| GET | `/sessions/{sid}/signals?limit=` | Signals |
| GET | `/sessions/{sid}/orders?status=&limit=` | Orders |
| GET | `/sessions/{sid}/positions` | Positions |
| GET | `/sessions/{sid}/portfolio` | Portfolio |
| GET | `/sessions/{sid}/risk` | Risk |
| GET | `/sessions/{sid}/journal?limit=` | Journal |
| GET | `/sessions/{sid}/equity-curve?points=` | Equity Curve |

#### 4.1.3 操作

| Method | Path | 说明 |
|---|---|---|
| POST | `/sessions/{sid}/order` | 手动下单 |
| POST | `/sessions/{sid}/cancel/{order_id}` | 撤单 |
| POST | `/sessions/{sid}/kill-switch` | 触发 Kill Switch |

#### 4.1.4 Replay

| Method | Path | 说明 |
|---|---|---|
| GET | `/sessions/{sid}/replay/timeline` | 获取时间线节点 |
| GET | `/sessions/{sid}/replay/snapshot?time=` | 获取指定时间快照 |
| POST | `/sessions/{sid}/replay/restore` | 恢复到指定时间点 |

#### 4.1.5 策略库

| Method | Path | 说明 |
|---|---|---|
| GET | `/strategies` | 可用策略列表（从 StrategyRegistry） |
| GET | `/strategies/{strategy_id}` | 策略详情 |

### 4.2 TradingStudioService

新建 `quantlab/api/trading_service.py`：

```python
class TradingStudioService:
    """对接 TradingCore + Persistence + Replay"""
    def __init__(self): 
        self._sessions: Dict[str, TradingCore] = {}  # 内存中的活跃会话
        self._persistence = TradingPersistence(...)
        self._replay = ReplayEngine(...)
    
    def create_session(self, mode, strategy_id, ...): ...
    def start_session(self, sid): ...
    def get_overview(self, sid) -> dict: ...
    def get_signals(self, sid, limit) -> list: ...
    # ... 其他方法对应 API
```

### 4.3 ReplayEngine

新建 `quantlab/trading_core/replay.py`：

```python
class ReplayEngine:
    """时间机器：从 paper_snapshots + paper_orders + paper_trades 重建任意时间点状态"""
    def get_timeline(self, strategy_id) -> list[dict]:
        """返回所有事件时间点（订单/成交/快照）"""
    def get_snapshot(self, strategy_id, time) -> dict:
        """返回指定时间的完整状态：账户/持仓/订单/成交/PnL"""
    def restore_to(self, strategy_id, time) -> dict:
        """恢复到指定时间，返回重建后的状态"""
```

### 4.4 删除清单

- `quantlab/api/live.py`（删除整个文件）
- `quantlab/api/app.py` 中移除 `live_router` 注册
- `frontend/src/api/live.ts`（删除）
- `frontend/src/views/live/LiveStudio.vue`（删除）

---

## 五、前端架构设计

### 5.1 路由改造

`frontend/src/router/index.ts`：

```typescript
// 删除
{ path: '/live', name: 'LiveStudio', component: ... }

// 新增
{
  path: '/trading',
  name: 'TradingStudio',
  component: () => import('@/views/trading/TradingStudio.vue'),
  children: [
    { path: '', redirect: '/trading/overview' },
    { path: 'overview', name: 'TradingOverview', component: () => import('@/views/trading/workspaces/OverviewWorkspace.vue') },
    { path: 'market', name: 'TradingMarket', component: () => import('@/views/trading/workspaces/MarketWorkspace.vue') },
    { path: 'signals', name: 'TradingSignals', component: () => import('@/views/trading/workspaces/SignalsWorkspace.vue') },
    { path: 'orders', name: 'TradingOrders', component: () => import('@/views/trading/workspaces/OrdersWorkspace.vue') },
    { path: 'positions', name: 'TradingPositions', component: () => import('@/views/trading/workspaces/PositionsWorkspace.vue') },
    { path: 'portfolio', name: 'TradingPortfolio', component: () => import('@/views/trading/workspaces/PortfolioWorkspace.vue') },
    { path: 'risk', name: 'TradingRisk', component: () => import('@/views/trading/workspaces/RiskWorkspace.vue') },
    { path: 'journal', name: 'TradingJournal', component: () => import('@/views/trading/workspaces/JournalWorkspace.vue') },
    { path: 'replay', name: 'TradingReplay', component: () => import('@/views/trading/workspaces/ReplayWorkspace.vue') },
  ]
}

// 旧路径重定向
{ path: '/live', redirect: '/trading' }
```

### 5.2 文件清单

```
frontend/src/
├── api/
│   └── trading.ts                    # 新建：Trading API 封装
├── stores/
│   └── trading.ts                    # 新建：Pinia store（会话/Mode/当前Workspace）
├── views/trading/
│   ├── TradingStudio.vue             # 新建：主框架（顶部Mode+左侧导航+Workspace容器）
│   ├── components/
│   │   ├── ModeSwitcher.vue          # 顶部 Paper/Live/Replay 切换器
│   │   ├── SessionHeader.vue         # 顶部状态栏（PnL/Cash/Exposure/Risk/Latency）
│   │   ├── WorkspaceNav.vue          # 左侧 9 Workspace 导航
│   │   └── StatusBar.vue             # 底部状态栏（Connected/Latency/Mode）
│   └── workspaces/
│       ├── OverviewWorkspace.vue     # 1 首页 Dashboard
│       ├── MarketWorkspace.vue       # 2 行情
│       ├── SignalsWorkspace.vue      # 3 信号
│       ├── OrdersWorkspace.vue       # 4 订单
│       ├── PositionsWorkspace.vue    # 5 持仓
│       ├── PortfolioWorkspace.vue    # 6 组合
│       ├── RiskWorkspace.vue         # 7 风险
│       ├── JournalWorkspace.vue      # 8 日志
│       └── ReplayWorkspace.vue       # 9 时间机器
```

### 5.3 TradingStudio.vue 主框架布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Logo  QuantLab   [Paper● Live○ Replay○]   Account  Notification    │ 顶部
├──────────────┬─────────────────────────────────────────────────────┤
│              │ Session: PAPER-0001  |  PnL +1,234  Cash 98,766      │ 状态栏
│ Navigation   │ Exposure 12%  Risk Low  Latency 8ms                  │
│              ├─────────────────────────────────────────────────────┤
│ Overview  ▼  │                                                     │
│ Market       │                                                     │
│ Signals      │            Main Workspace                           │
│ Orders       │            (router-view)                            │
│ Positions    │                                                     │
│ Portfolio    │                                                     │
│ Risk         │                                                     │
│ Journal      │                                                     │
│ Replay       │                                                     │
│              │                                                     │
├──────────────┴─────────────────────────────────────────────────────┤
│ ● Connected   Mode: Paper   Session: PAPER-0001   Latency: 8ms     │ 底部
└────────────────────────────────────────────────────────────────────┘
```

### 5.4 Pinia Store 设计

`frontend/src/stores/trading.ts`：

```typescript
export const useTradingStore = defineStore('trading', {
  state: () => ({
    mode: 'paper' as 'paper' | 'live' | 'replay',
    sessions: [] as TradingSession[],
    currentSessionId: '' as string,
    currentWorkspace: 'overview' as WorkspaceName,
    overview: null as OverviewData | null,
    sessionStatus: null as SessionStatus | null,
  }),
  actions: {
    async fetchSessions() {...},
    async createSession(req) {...},
    async switchMode(mode) {...},
    async startSession(sid) {...},
    async pauseSession(sid) {...},
    async stopSession(sid) {...},
    async fetchOverview(sid) {...},
    async fetchOrders(sid, status?) {...},
    // ... 每个 Workspace 一个 fetch
    async manualOrder(sid, req) {...},
    async cancelOrder(sid, orderId) {...},
  }
})
```

### 5.5 API 模块设计

`frontend/src/api/trading.ts`：

```typescript
export class TradingAPI {
  // 会话
  listSessions(mode?) → GET /trading/sessions
  createSession(req) → POST /trading/sessions
  getSession(sid) → GET /trading/sessions/{sid}
  deleteSession(sid) → DELETE /trading/sessions/{sid}
  startSession(sid) → POST /trading/sessions/{sid}/start
  pauseSession(sid) → POST /trading/sessions/{sid}/pause
  resumeSession(sid) → POST /trading/sessions/{sid}/resume
  stopSession(sid) → POST /trading/sessions/{sid}/stop
  getSessionStatus(sid) → GET /trading/sessions/{sid}/status
  
  // 数据
  getOverview(sid) → GET /trading/sessions/{sid}/overview
  getMarket(sid, symbols?) → GET /trading/sessions/{sid}/market
  getSignals(sid, limit?) → GET /trading/sessions/{sid}/signals
  getOrders(sid, status?, limit?) → GET /trading/sessions/{sid}/orders
  getPositions(sid) → GET /trading/sessions/{sid}/positions
  getPortfolio(sid) → GET /trading/sessions/{sid}/portfolio
  getRisk(sid) → GET /trading/sessions/{sid}/risk
  getJournal(sid, limit?) → GET /trading/sessions/{sid}/journal
  getEquityCurve(sid, points?) → GET /trading/sessions/{sid}/equity-curve
  
  // 操作
  manualOrder(sid, req) → POST /trading/sessions/{sid}/order
  cancelOrder(sid, orderId) → POST /trading/sessions/{sid}/cancel/{orderId}
  killSwitch(sid) → POST /trading/sessions/{sid}/kill-switch
  
  // Replay
  getReplayTimeline(sid) → GET /trading/sessions/{sid}/replay/timeline
  getReplaySnapshot(sid, time) → GET /trading/sessions/{sid}/replay/snapshot?time=
  restoreReplay(sid, time) → POST /trading/sessions/{sid}/replay/restore
  
  // 策略库
  listStrategies() → GET /trading/strategies
  getStrategy(id) → GET /trading/strategies/{id}
}
export const tradingApi = new TradingAPI()
```

---

## 六、各 Workspace 详细设计

### 6.1 Overview（首页 Dashboard）

**指标卡（2行3列）**：
- 第一行：Today's Return / Today's PnL / Cash
- 第二行：Exposure / Sharpe / Drawdown

**图表**：
- Equity Curve（ECharts 折线图，实时更新）
- 今日 PnL 构成（已实现/未实现饼图）

### 6.2 Market（行情）

**Watchlist 表格**：Symbol / Last / Change% / Volume / Bid / Ask
**Chart 区**：K线图（复用 CandlestickChart.vue）+ 技术指标

### 6.3 Signals（信号）

**表格列**：Time / Symbol / Direction / Score / Confidence / Reason / Status
**交互**：点击行展开详情（因子贡献、预测值、历史命中率）

### 6.4 Orders（订单）

**状态分组 Tabs**：All / Submitted / Filled / Cancelled / Rejected
**表格列**：Time / Order ID / Symbol / Side / Type / Qty / Price / Filled Qty / Filled Price / Status
**操作**：未成交订单可撤单

### 6.5 Positions（持仓）

**表格列**：Symbol / Direction / Qty / Cost / Current / Market Value / Unrealized PnL / PnL% / Holding Days
**汇总栏**：总市值 / 总 PnL / 多空敞口

### 6.6 Portfolio（组合）

**指标卡**：Total Equity / Cash / Invested / Exposure / Leverage
**图表**：
- 持仓权重饼图
- 行业/标的分布柱状图
- 净值曲线

### 6.7 Risk（风险）

**指标卡**：VaR(95%) / Max Drawdown / Turnover / Concentration / Beta / Factor Exposure
**图表**：Drawdown 曲线 / 风险指标雷达图

### 6.8 Journal（交易日志）

**表格列**：Time / Type / Symbol / Side / Qty / Price / Reason / Prediction / Confidence / PnL
**特性**：每笔成交自动生成 Journal 条目，支持按策略/标的/时间筛选

### 6.9 Replay（时间机器）

**左侧 Timeline**：垂直时间轴，每个节点是一个事件（订单/成交/快照）
**右侧恢复区**：点击 Timeline 节点后，显示该时间点的：
- 账户状态
- 持仓快照
- 订单状态
- 成交明细
- Equity Curve（截至该时间点）

---

## 七、实施步骤

### 阶段 1：后端基础（数据库 + 引擎 + API）

1. 新建 `quantlab/trading_core/persistence.py`（5 张表 CRUD）
2. 新建 `quantlab/trading_core/replay.py`（ReplayEngine）
3. 新建 `quantlab/api/trading_service.py`（对接 TradingCore + Persistence + Replay）
4. 新建 `quantlab/api/trading.py`（FastAPI 路由）
5. 修改 `quantlab/api/app.py`（注册 trading_router，移除 live_router）
6. 删除 `quantlab/api/live.py`
7. 单元测试：`tests/test_trading_persistence.py` + `tests/test_trading_api.py`

### 阶段 2：前端基础（路由 + Store + API + 主框架）

1. 新建 `frontend/src/api/trading.ts`
2. 新建 `frontend/src/stores/trading.ts`
3. 修改 `frontend/src/router/index.ts`（/live → /trading + 9 子路由）
4. 新建 `frontend/src/views/trading/TradingStudio.vue`
5. 新建 4 个组件：ModeSwitcher / SessionHeader / WorkspaceNav / StatusBar
6. 修改 `frontend/src/components/SidebarMenu.vue`

### 阶段 3：前端 9 个 Workspace 页面

按依赖顺序实现：
1. OverviewWorkspace（基础指标 + Equity Curve）
2. SignalsWorkspace（信号表格）
3. OrdersWorkspace（订单表格 + 撤单）
4. PositionsWorkspace（持仓表格）
5. PortfolioWorkspace（组合图表）
6. RiskWorkspace（风险指标）
7. JournalWorkspace（交易日志）
8. MarketWorkspace（行情 + K线）
9. ReplayWorkspace（时间机器）

### 阶段 4：清理与测试

1. 删除 `frontend/src/views/live/LiveStudio.vue`
2. 删除 `frontend/src/api/live.ts`
3. 前端构建验证：`npm run build`
4. 后端启动验证：`uvicorn quantlab.api.app:app`
5. 端到端联调：创建 Paper 会话 → 下单 → 查看各 Workspace → Replay

---

## 八、验收标准

### 8.1 后端

- [ ] 5 张 paper_* 表自动创建
- [ ] `POST /api/v1/trading/sessions` 可创建 Paper 会话并启动
- [ ] `GET /api/v1/trading/sessions/{sid}/overview` 返回正确指标
- [ ] `POST /api/v1/trading/sessions/{sid}/order` 可下单并落库
- [ ] `GET /api/v1/trading/sessions/{sid}/replay/timeline` 返回时间线
- [ ] 旧 `/api/v1/live/*` 端点已移除
- [ ] 单元测试全部通过

### 8.2 前端

- [ ] 访问 `/trading` 进入 Trading Studio，默认 Overview
- [ ] 顶部 Mode 切换器可切换 Paper/Live/Replay
- [ ] 左侧 9 个 Workspace 导航可切换
- [ ] 创建 Paper 会话后，Overview 显示实时指标
- [ ] Equity Curve 实时更新
- [ ] Orders/Positions/Journal 数据正确显示
- [ ] Replay Timeline 可点击恢复状态
- [ ] 访问 `/live` 自动重定向到 `/trading`
- [ ] `npm run build` 无错误

### 8.3 视觉

- [ ] Bloomberg 暗色风格，等宽字体
- [ ] 与 Observe Studio 视觉一致
- [ ] 状态栏颜色语义：绿(success)/红(danger)/黄(warning)
- [ ] 响应式布局适配

---

## 九、风险与约束

1. **TradingCore 内存态与持久化同步**：每次 on_bar 后异步落库，避免阻塞行情驱动
2. **Replay 数据完整性**：依赖 paper_snapshots 表的快照频率，建议每笔成交+每分钟各一份快照
3. **Live Mode 安全性**：本次 Live Mode 仅做 UI 框架，实际下单暂不接入真实交易所（保留接口）
4. **市场数据来源**：Paper Mode 行情暂用历史数据回放，后续接入实时订阅
5. **不污染市场数据库**：paper_* 表与市场数据表物理隔离（同库不同表前缀）
