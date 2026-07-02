# 模拟交易模块（Paper Trading）实施计划

> 基于 `docs/requerment/模拟交易模块（Paper Trading）实现计划.md` 与 `详细设计方案.md`
> 制定日期：2026-07-02

---

## 0. 现状核实与关键决策

### 0.1 文档假设 vs 代码现状

经实地核查，两份设计文档假设的若干基础设施在当前代码库中**并不存在**，需先补齐：

| 文档假设 | 现状 | 处置 |
|---|---|---|
| `init_database` 函数（database.py） | 不存在；表创建分散在各模块 `_get_conn()` | 新建 `quantlab/database.py` 集中入口 |
| `DataLoader` 类 + `get_price_data` | 不存在；用 `pd.read_csv` 裸调用 | 新建 `quantlab/data/loader.py` |
| `BaseStrategy`（on_init/on_bar/exit_checker） | 不存在；现有 `SignalStrategy` 只有 `signal()` | 新建 `quantlab/strategy/base.py`，与 SignalStrategy 并存 |
| CLI 主入口（main.py 子命令） | 不存在；main.py 是演示脚本，真入口是 FastAPI | 改造 main.py 为 argparse CLI，演示代码移至 `demo` 子命令 |
| `stock_daily` 表 | 不存在 | 在 init_database 中新建 |
| strategies 表 `is_active` 字段 | 不存在 | ALTER TABLE 补字段 |
| A股策略示例 | 不存在 | 新建小市值策略示例 |

### 0.2 与现有体系的关系

- **BaseStrategy vs SignalStrategy**：两套并存。BaseStrategy 面向"每日收盘批量撮合"模型（on_bar 返回目标订单，exit_checker 判断出场）；SignalStrategy 面向"信号面板+截面选股"模型。互不干扰。
- **CLI vs FastAPI**：两套并存。CLI 用于每日定时任务和命令行查看状态；FastAPI + Vue 用于交互式界面。目的不同。
- **paper_trading 撮合 vs execution/paper**：独立实现。execution/paper 是 tick/bar 级实时事件驱动撮合；paper_trading 是每日收盘批量撮合（close 价成交 + next_open 次日开盘成交）。模型不同，不复用。
- **数据规则**：遵循 AGENTS.md 规则——数据库中的市场数据必须干净可信，模拟数据绝不写入数据库。测试时使用真实数据或从现有 HS300 数据集加载。

### 0.3 模块结构

```
quantlab/
  ├── database.py                 # [NEW] init_database 集中入口（含 stock_daily + paper_* 表）
  ├── data/
  │   ├── __init__.py             # [NEW]
  │   └── loader.py               # [NEW] DataLoader（get_price_data 从 stock_daily 读K线）
  ├── strategy/
  │   ├── __init__.py             # [NEW]
  │   ├── base.py                 # [NEW] BaseStrategy 抽象基类（on_init/on_bar/exit_checker）
  │   ├── context.py              # [NEW] StrategyContext（资金/持仓/K线缓冲区）
  │   └── examples/
  │       ├── __init__.py         # [NEW]
  │       └── small_cap.py        # [NEW] 小市值策略示例（用于测试）
  ├── paper_trading/
  │   ├── __init__.py             # [NEW]
  │   ├── config.py               # [NEW] 模拟交易参数（初始资金/费率/撮合模式）
  │   ├── engine.py               # [NEW] PaperTradingEngine（撮合/费用/持仓/冻结资金）
  │   └── orchestrator.py         # [NEW] PaperTradingOrchestrator（编排流程）
  └── cli/
      ├── __init__.py             # [NEW]
      ├── main.py                 # [NEW] CLI 主入口（argparse，挂载子命令）
      └── paper_cli.py            # [NEW] paper 子命令（--run/--status/--positions/--reset）

tests/
  └── test_paper_trading.py       # [NEW] 单元测试

main.py                           # [MODIFY] 改造为 argparse CLI 入口，原演示代码移至 demo 子命令
```

---

## 1. 分阶段任务分解

### 阶段0：补齐基础设施

#### 任务 0.1 创建 BaseStrategy 抽象基类
- **文件**：`quantlab/strategy/base.py`、`quantlab/strategy/__init__.py`
- **内容**：
  - `BaseStrategy(ABC)` 抽象基类
  - `on_init(self) -> None`：策略初始化（可选实现，默认空）
  - `on_bar(self, ctx: StrategyContext) -> List[Order]`：每根K线调用，返回目标订单列表
  - `exit_checker(self, ctx: StrategyContext) -> List[Order]`：检查持仓出场，返回出场订单列表
  - `name`、`version` 属性（用于策略标识）
- **验证**：可被实例化的子类能调用各方法

#### 任务 0.2 创建 StrategyContext
- **文件**：`quantlab/strategy/context.py`
- **内容**：
  - `StrategyContext` dataclass：包含 trade_date、cash、frozen_cash、positions（Dict[code, Position]）、bar_data（Dict[code, DataFrame] 历史K线缓冲区）、universe（候选标的列表）
  - `Position` dataclass：stock_code、quantity、entry_price、entry_date、current_price、direction

#### 任务 0.3 创建 DataLoader
- **文件**：`quantlab/data/__init__.py`、`quantlab/data/loader.py`
- **内容**：
  - `DataLoader` 类，封装从 SQLite `stock_daily` 表读取K线数据
  - `get_price_data(stock_code, start_date, end_date) -> DataFrame`：读取单标的K线
  - `get_price_panel(stock_codes, start_date, end_date) -> Dict[code, DataFrame]`：批量读取
  - `get_close_prices(date) -> Dict[code, float]`：读取某日全市场收盘价
  - `get_open_prices(date) -> Dict[code, float]`：读取某日全市场开盘价

#### 任务 0.4 创建 init_database 集中入口
- **文件**：`quantlab/database.py`
- **内容**：
  - `init_database(db_path=None)` 函数：创建所有必要的表
  - `stock_daily` 表：trade_date、stock_code、open、high、low、close、volume、amount、pct_change、adj_factor（后复权因子）
  - `strategies` 表 is_active 字段：ALTER TABLE 补字段（兼容现有 storage/strategies.db）
  - 索引：stock_daily(trade_date, stock_code)
  - 同时创建 5 张 paper_* 表（见阶段1）

#### 任务 0.5 创建 A股策略示例（小市值策略）
- **文件**：`quantlab/strategy/examples/small_cap.py`
- **内容**：
  - `SmallCapStrategy(BaseStrategy)`：选市值最小的 N 只股票开仓
  - `on_bar`：返回买入订单（小市值前N名）
  - `exit_checker`：持有满 N 天出场
  - 用于测试 PaperTradingOrchestrator

#### 任务 0.6 创建 CLI 框架
- **文件**：`quantlab/cli/__init__.py`、`quantlab/cli/main.py`
- **内容**：
  - argparse 主解析器，支持子命令挂载
  - `demo` 子命令：保留原 main.py 演示功能（迁移）
  - `paper` 子命令：挂载 paper_cli（阶段3实现）
  - 入口：`python main.py <subcommand> [args]`

#### 任务 0.7 改造根目录 main.py
- **文件**：`main.py`（根目录）
- **内容**：
  - 改造为 argparse CLI 入口
  - 原演示代码迁移至 `quantlab/cli/demo.py` 或保留为 `demo` 子命令
  - 挂载 `paper` 子命令

**阶段0验证**：
- `python main.py --help` 显示子命令列表
- `python -c "from quantlab.strategy import BaseStrategy"` 可导入
- `python -c "from quantlab.data import DataLoader"` 可导入
- `python -c "from quantlab.database import init_database; init_database()"` 可执行

---

### 阶段1：数据库层（Component 1）

#### 任务 1.1 创建 5 张 paper_* 表
- **文件**：`quantlab/database.py`（在 init_database 中）
- **表结构**：严格按详细设计方案 §3.1-3.5
  - `paper_accounts`：strategy_id PK、strategy_name、version、initial_capital、cash、frozen_cash、total_value、peak_value、updated_at
  - `paper_positions`：strategy_id+stock_code PK、direction、quantity、entry_price、entry_date、current_price、value、updated_at
  - `paper_orders`：order_id AUTOINCREMENT PK、strategy_id、stock_code、direction、quantity、price_type、reason、status、created_date、updated_at
  - `paper_trades`：trade_id AUTOINCREMENT PK、order_id、strategy_id、stock_code、direction、quantity、price、amount、commission、slippage、trade_date、created_at
  - `paper_snapshots`：id AUTOINCREMENT PK、strategy_id、trade_date、cash、position_value、total_value、daily_return、max_drawdown、created_at，UNIQUE(strategy_id, trade_date)
  - 索引：idx_paper_orders_strategy、idx_paper_trades_strategy、idx_paper_snapshots_strategy

#### 任务 1.2 封装 CRUD 接口
- **文件**：`quantlab/database.py`（或 `quantlab/paper_trading/db_ops.py`）
- **接口**：
  - `get_paper_account(strategy_id)` / `save_paper_account(account)`
  - `get_paper_positions(strategy_id)` / `save_paper_position(pos)` / `delete_paper_position(strategy_id, stock_code)`
  - `insert_paper_order(order)` / `get_pending_orders(strategy_id)` / `update_order_status(order_id, status)`
  - `insert_paper_trade(trade)`
  - `insert_paper_snapshot(snapshot)` / `get_snapshots(strategy_id, start_date, end_date)`
  - `reset_paper_trading(strategy_id=None)`：清空历史
  - `get_active_strategies()`：查询 is_active=1 的策略

**阶段1验证**：
- 单元测试：CRUD 各接口可正确读写
- 表结构与文档 §3 完全一致

---

### 阶段2：撮合引擎（Component 2）

#### 任务 2.1 实现 PaperTradingEngine
- **文件**：`quantlab/paper_trading/engine.py`
- **内容**：
  - `PaperTradingEngine` 类
  - `load_account(strategy_id)`：从DB读取账户与持仓
  - `execute_order(order, price, date)`：撮合单笔成交
    - 计算费用：佣金（万三，最低5元）、印花税（卖出千一）、过户费
    - 买入：扣现金、增持仓、更新开仓均价
    - 卖出：增现金、减持仓、计算盈亏
    - 写入 paper_trades 和 paper_positions
  - `freeze_capital(strategy_id, amount)`：冻结买单资金（cash → frozen_cash）
  - `unfreeze_capital(strategy_id, amount)`：解冻资金
  - `settle_daily(date, day_close_prices)`：收盘结算
    - 重算持仓市值（quantity × close）
    - 计算总资产 = cash + frozen_cash + 持仓市值
    - 计算日收益率、最大回撤
    - 写入 paper_snapshots

#### 任务 2.2 实现 PaperTradingOrchestrator
- **文件**：`quantlab/paper_trading/orchestrator.py`
- **内容**：
  - `PaperTradingOrchestrator` 类
  - `run_daily_process(trade_date)`：主流程
    1. 加载所有 is_active=1 的策略，初始化缺失的 paper_accounts
    2. 检查 stock_daily 是否有今日数据
    3. 撮合昨日 Pending 的 next_open 订单（用今日 open 价）
    4. 调用 `strategy.exit_checker(ctx)` 检查出场，生成出场订单
       - close 模式：当日收盘价成交
       - next_open 模式：存入 Pending
    5. 调用 `strategy.on_bar(ctx)` 获取开仓目标，生成入场订单
       - 过滤 ST、涨跌停、停牌
       - 检查资金是否足够
       - close 模式：当日成交扣现金
       - next_open 模式：冻结资金存入 Pending
    6. 收盘结算：settle_daily 写入快照

#### 任务 2.3 配置文件
- **文件**：`quantlab/paper_trading/config.py`
- **内容**：
  - `PaperTradingConfig` dataclass
  - initial_capital: float = 1_000_000
  - commission_rate: float = 0.0003（万三）
  - commission_min: float = 5.0（最低5元）
  - stamp_tax_rate: float = 0.001（卖出千一）
  - transfer_fee_rate: float = 0.00002（过户费万零点二）
  - lot_size: int = 100（A股一手100股）
  - default_price_type: str = "close"

**阶段2验证**：
- 单元测试：手续费计算准确（佣金万三最低5元、印花税卖出千一）
- 单元测试：买入扣现金增持仓、卖出增现金减持仓
- 单元测试：Pending 订单次日 open 价撮合
- 单元测试：日收益率和最大回撤计算正确

---

### 阶段3：CLI（Component 3）

#### 任务 3.1 实现 paper_cli
- **文件**：`quantlab/cli/paper_cli.py`
- **子命令**：
  - `paper --run [--date YYYY-MM-DD]`：执行每日模拟交易计算流
  - `paper --status`：Rich 表格展示所有活跃策略账户（总资产/现金/持仓市值/日收益/最大回撤）
  - `paper --positions <strategy_id>`：查看特定策略持仓明细（代码/股数/成本/现价/浮盈）
  - `paper --reset [--strategy <id>]`：清空模拟交易历史
  - `paper --adjust-cash <strategy_id> --amount <金额>`：手动调整现金

#### 任务 3.2 挂载到主 CLI
- **文件**：`quantlab/cli/main.py`、根目录 `main.py`
- **内容**：绑定 paper 子命令到主入口

**阶段3验证**：
- `python main.py paper --help` 显示子命令帮助
- `python main.py paper --status` 显示初始账户（1,000,000元）
- `python main.py paper --run --date 2024-01-02` 执行模拟交易
- `python main.py paper --positions <id>` 显示持仓

---

### 阶段4：测试验证

#### 任务 4.1 单元测试
- **文件**：`tests/test_paper_trading.py`
- **测试内容**：
  - `PaperTradingEngine` 手续费计算（佣金/印花税/过户费）
  - 买入/卖出撮合逻辑（现金/持仓/开仓均价）
  - Pending 订单次日撮合
  - 日收益率和最大回撤计算
  - `PaperTradingOrchestrator` 驱动小市值策略生成开仓
  - CRUD 接口读写正确性
- **测试命令**：`python -X utf8 -m pytest tests/test_paper_trading.py`

#### 任务 4.2 手动验证
- 运行 `python main.py paper --status` 显示初始 1,000,000 元账户
- 运行 `python main.py paper --run --date 2024-01-02` 和 `--date 2024-01-03` 执行模拟交易
- 运行 `python main.py paper --status` 确认资产扣减及手续费计算无误

**数据说明**：测试需真实A股K线数据写入 `stock_daily` 表。遵循 AGENTS.md 规则"模拟数据绝不写入数据库"，将使用真实数据源（现有 HS300 数据集或外部数据同步）。测试前需确认数据源可用性。

---

## 2. 依赖关系

```
阶段0（基础设施）→ 阶段1（数据库层）→ 阶段2（撮合引擎）→ 阶段3（CLI）→ 阶段4（测试）
```

阶段0内部依赖：
- 0.1 BaseStrategy ← 0.2 StrategyContext（Context 被 BaseStrategy 方法签名引用）
- 0.4 init_database ← 0.3 DataLoader（Loader 依赖 stock_daily 表）
- 0.5 小市值策略 ← 0.1 BaseStrategy + 0.2 StrategyContext
- 0.6 CLI框架 ← 0.7 main.py改造

阶段2依赖阶段0+1：
- 2.1 Engine ← 1.2 CRUD
- 2.2 Orchestrator ← 2.1 Engine + 0.3 DataLoader + 0.1 BaseStrategy

---

## 3. 风险与注意事项

1. **main.py 改造风险**：根目录 main.py 当前是演示脚本，改造为 CLI 会改变其行为。方案：原演示代码迁移至 `demo` 子命令，保持向后兼容。
2. **strategies 表 is_active 字段**：现有 storage/strategies.db 无此字段，需 ALTER TABLE 补充。init_database 中用 `ALTER TABLE ... ADD COLUMN ... IF NOT EXISTS`（SQLite 用 PRAGMA 检查列存在性兼容处理）。
3. **测试数据来源**：AGENTS.md 规则"模拟数据绝不写入数据库"。测试需要真实A股K线数据。若现有 HS300 数据集可用则加载；否则需确认数据同步方案。文档"手动验证"提到的"生成模拟历史数据"与 AGENTS.md 冲突，将以 AGENTS.md 为准。
4. **两套策略体系并存**：BaseStrategy（on_bar/exit_checker）与 SignalStrategy（signal）并存，需在文档中明确说明适用场景，避免混淆。
5. **stock_daily 表数据同步**：本计划只建表结构和 DataLoader 读取接口，数据同步（从QMT/东财等数据源写入 stock_daily）不在本次范围内，需单独任务。

---

## 4. 验收标准（Checklist）

- [ ] `python main.py --help` 显示 demo 和 paper 子命令
- [ ] `python main.py paper --status` 显示初始账户
- [ ] `python main.py paper --run --date YYYY-MM-DD` 执行模拟交易
- [ ] 5 张 paper_* 表结构与文档 §3 完全一致
- [ ] 手续费计算：佣金万三最低5元、印花税卖出千一、过户费
- [ ] Pending 订单次日 open 价撮合正确
- [ ] 日收益率和最大回撤计算正确
- [ ] 单元测试全部通过：`python -X utf8 -m pytest tests/test_paper_trading.py`
- [ ] 小市值策略可被 Orchestrator 驱动生成开仓
- [ ] BaseStrategy 抽象基类含 on_init/on_bar/exit_checker
- [ ] DataLoader.get_price_data 可从 stock_daily 读K线
- [ ] init_database 可创建所有表
