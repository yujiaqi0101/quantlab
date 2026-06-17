# QuantLab Studio — 前端用户使用手册

> 适用对象：量化研究员 / 策略开发者 / 运维人员
> 适用版本：QuantLab V3.6+（含 V3.5 Execution Fidelity、V3.6 Execution-Aware Alpha）
> 入口地址（默认）：`http://localhost:5173`

---

## 目录

- [1. 快速开始](#1-快速开始)
- [2. 全局界面布局](#2-全局界面布局)
- [3. Research Dashboard（首页）](#3-research-dashboard首页)
- [4. Strategies（策略管理）](#4-strategies策略管理)
- [5. Strategy Builder（策略构建器）](#5-strategy-builder策略构建器)
- [6. Datasets（数据集）](#6-datasets数据集)
- [7. Backtest Workspace（回测工作台）](#7-backtest-workspace回测工作台)
- [8. Factors（因子）](#8-factors因子)
- [9. Signal Research（信号研究）](#9-signal-research信号研究)
- [10. Research Lab（实验流水线）](#10-research-lab实验流水线)
- [11. Experiments（实验管理）](#11-experiments实验管理)
- [12. Compare（实验对比）](#12-compare实验对比)
- [13. Leaderboard（排行榜）](#13-leaderboard排行榜)
- [14. Production Studio（生产运行时）](#14-production-studio生产运行时)
- [15. Execution Fidelity Studio（V3.5）](#15-execution-fidelity-studiov35)
- [16. Alpha-Aware Studio（V3.6）](#16-alpha-aware-studiov36)
- [17. 通用操作](#17-通用操作)
- [18. 常见问题 FAQ](#18-常见问题-faq)

---

## 1. 快速开始

### 1.1 启动后端 API
```bash
# 在项目根目录
python -m quantlab.api.app
# 默认监听 http://127.0.0.1:8000
```
启动后访问 `http://127.0.0.1:8000/docs` 可看到 FastAPI 自动生成的接口文档。

### 1.2 启动前端
```bash
cd frontend
npm install         # 首次需要
npm run dev         # 启动 Vite，默认 5173
```
浏览器访问 `http://localhost:5173`，自动重定向到 `/studio`（Research Dashboard）。

### 1.3 关键概念
| 术语 | 含义 |
|------|------|
| **Strategy** | 一个可序列化的策略类（含信号 + 组合构建 + 参数网格） |
| **Dataset** | 多标的 OHLCV 数据集 + 时间区间 + 标的池 |
| **Experiment** | 一次回测的完整快照：策略 + 数据 + 引擎 + 结果指标 |
| **Backtest** | 在 BacktestWorkspace 中"跑一次"回测 |
| **Production** | 已注册到 Supervisor 的运行时策略（多策略 × 多账户） |
| **Fidelity** | 真实交易模拟（订单簿、冲击、成本、对账、影子模式） |
| **Alpha-Aware** | 策略"可交易性"评估（10 个模块，最终给出 S~F 评级） |

---

## 2. 全局界面布局

```
┌──────────────────────────────────────────────────────────┐
│ TopBar（顶部）:  系统状态 / 主题切换 / 用户菜单            │
├────────┬─────────────────────────────────────────────────┤
│        │                                                 │
│  侧边  │                                                 │
│  导航  │            路由视图（页面主体）                  │
│  菜单  │                                                 │
│        │                                                 │
│        │                                                 │
└────────┴─────────────────────────────────────────────────┘
```

- **TopBar**：展示当前页面标题、API 连接状态、主题切换。
- **侧边菜单**：分组的 16 个功能页面（见下表）。
- **主体**：每个功能页面是一个独立 Vue 组件，多数用 **Element Plus Tabs / 卡片** 组织子功能。

### 2.1 侧边菜单导航

| 路径 | 名称 | 用途 |
|------|------|------|
| `/studio` | Research Dashboard | 首页 / 总体概览 |
| `/strategies` | Strategies | 策略列表 |
| `/strategy-builder` | **Builder**（侧边栏显示名为 "Builder"，不是 "Strategy Builder"） | 拖拽式构建策略 |
| `/strategies/:id` | Strategy Detail | 策略详情 |
| `/datasets` | Datasets | 数据集列表 |
| `/datasets/:id` | Dataset Detail | 数据集详情 |
| `/backtests` | Backtest Workspace | 单次回测工作台 |
| `/factors` | Factor Studio | 因子研究 |
| `/signals` | Signal Research | 信号研究 |
| `/research` | Research Lab | 自动研究流水线 |
| `/experiments` | Experiments | 实验记录 |
| `/experiments/:id` | Experiment Detail | 单个实验详情 |
| `/compare` | Compare | 实验对比 |
| `/leaderboard` | Leaderboard | 实验排行榜 |
| `/production` | Production Studio | 运行时 / 多账户 |
| `/fidelity` | Execution Fidelity | 真实化模拟（V3.5） |
| `/alpha-aware` | Alpha-Aware | 可交易性评估（V3.6） |

---

## 3. Research Dashboard（首页）

**路径**：`/studio`  （`/`，自动重定向）

进入系统的"门面"。展示：
- **系统状态总览**：后端连通性、策略数、数据集数、Experiment 数、Production 实例数
- **最近实验**：倒序列出最近 5~10 个 Experiment，点击跳转 `/experiments/:id`
- **快速入口**：跳转到各常用功能（新建 Backtest / 打开 Leaderboard / 启动 Production）
- **KPI 卡片**：全局回测 Sharpe 平均、最大回撤平均、胜率

### 3.1 操作
- **点击 KPI 卡片**：跳转对应详情页
- **点击最近实验行**：跳转到 `/experiments/:id`
- **快速入口按钮**：直接打开对应页面

### 3.2 何时使用
- 每天上班第一眼：看后端是否在跑、昨日实验是否完成
- 给老板/合作方汇报：截首页图

---

## 4. Strategies（策略管理）

**路径**：`/strategies`

**作用**：管理所有"策略资产"——代码 + 参数 + 元信息 + 版本。

### 4.1 列表视图
| 列 | 含义 |
|----|------|
| ID | UUID 短码 |
| Name | 策略名 |
| Version | 版本号（el-tag 灰色） |
| Tags | 标签（最多显示 3 个，dark 风格） |
| Params | 参数数量 |
| （尾列） | `→` 箭头，提示可点击进入 |

> 备注：当前版本**未显示** Author / Created At / Description 摘要列；这些信息需要进 `/strategies/:id` 查看。

### 4.2 顶部操作栏
- **搜索框**：按 ID / Name / Tag 模糊搜索（客户端过滤）
- **刷新按钮**：重新拉取策略列表

> 备注：当前版本**未提供**导入 `.py`、导出 ZIP、复制、删除等批量操作；行级操作也仅支持"点击进入详情"（跳到 `/strategies/:id`）。如需这些能力，请走 `Strategy Builder`（§5）新建策略，并通过 Strategy Detail 修改参数后入库（V3.5+ 计划补"复制版本"功能）。

### 4.3 行内操作
- **点击行**：跳到 `/strategies/:id`
- （**无**"复制 / 删除 / 立即回测"等行内按钮）

---

## 5. Strategy Builder（构建器）

**侧边栏显示名**：**Builder**（不是 "Strategy Builder"）
**路径**：`/strategy-builder`

**作用**：通过表单配置"信号规则 + 仓位 + 风险控制"，不写 Python 代码也能创建策略（编译为后端 spec）。

### 5.1 实际页面结构（核查 `StrategyBuilder.vue`）

只有 **2 个 Tab**：

#### Tab 1: Builder
表单分三块：

| 区块 | 字段 | 说明 |
|------|------|------|
| **基础** | Name | 英文下划线（如 `RSI_Momentum_Strategy`） |
| | Description | 备注 |
| **信号规则**（多信号 + 组合） | `type` | `threshold` / `crossover` / `zero_cross` |
| | | `threshold`：`factor + op(</<=/>/>=/==) + value + direction(long/short/both)` |
| | | `crossover`：`fast_factor + slow_factor`（如 MA5 crosses MA20） |
| | | `zero_cross`：`factor`（因子过 0 时触发） |
| | `signalLogic` | `AND` / `OR` / `MAJORITY`（多信号如何组合） |
| **仓位** | `position.type` | `target`（目标权重）或 `equal_weight`（等权） |
| | `position.value` | 0~2 数值（杠杆/权重） |
| **风险** | `stop_loss` | 0~1 比例 |
| | `take_profit` | 0~1 比例 |
| | `max_dd` | 最大回撤阈值 |

底部按钮：**Create Strategy**（提交到后端，生成 spec），成功后自动 Preview。

#### Tab 2: Preview
- 显示**最近一次 Preview 的数据**（来自 `previewData`）
- 包括信号、信号触发统计、回测预览
- 切换 Tab 不会自动刷新，需要在已创建的策略上点 **Preview** 按钮

### 5.2 策略列表（页面下半部分）
- 显示已创建的 spec 列表
- 行内按钮：
  - **Preview** —— 触发回测预览
  - **Compile** —— 编译 spec
  - **Delete** —— 删除（**真删**，无软删除）

### 5.3 适用人群
- 不会写 Python 的研究员
- 快速验证想法（PM 模式）

> 备注：当前版本的 Builder **没有**内置"参数网格生成"和"流动性 / 滑点 / 换手 Constraints"专区；这些约束请直接编辑生成的 Python spec 或用 STRATEGY_DEV_GUIDE §21 的硬编码清单。

---

## 6. Datasets（数据集）

**路径**：`/datasets`

**作用**：管理回测所用的历史数据（OHLCV）。

### 6.1 列表视图（核查 `DatasetList.vue`）

**实际列**：

| 列 | 含义 |
|----|------|
| Name | 数据集名（点击可进入详情） |
| Symbol | 主 symbol（**单 symbol**，不是"标的列表"） |
| Freq | `1m` / `5m` / `1h` / `1d`（el-tag dark 风格） |
| Type | asset_type（`stock` / `crypto` / `future` 等） |
| Start | 起始日期 |
| End | 结束日期 |
| Rows | 行数（右对齐，千分位 K/M 格式化） |
| OHLCV | 勾（绿色 ✓）/-（灰色）表示是否完整 OHLCV |
| （尾列） | `→` 箭头，提示可点击进入 |

> 备注：当前版本**没有**多 symbol 标的池列、Tags 标签列、ID 列（ID 在 URL 中）、也没有行内的"查看 / 详情 / 删除"操作按钮。每行只支持"点击进入详情"。

### 6.2 顶部操作栏
- **搜索框**：按 Name / Symbol / Dataset ID / Tag 模糊搜索（客户端过滤）
- **刷新按钮**：重新拉取列表

> 备注：当前版本**没有**"新建数据集 / 上传 CSV / Parquet"入口按钮；如需新增数据集，请走后端 API 或 Python 脚本。

### 6.3 行内操作
- **点击行**：跳到 `/datasets/:dataset_id`
- （**无**"删除 / 编辑"等行内按钮）

### 6.4 Dataset Detail（`/datasets/:id`）
> 备注：手册此小节先前描述的"价格预览图 / 数据质量报告 / 标的列表 / 启用禁用"等是凭推测写的，**未核查 Detail 页**实际功能。实际页面内容请直接看 [`DatasetDetail.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/datasets/DatasetDetail.vue)。

---

## 7. Backtest Workspace（回测工作台）

**路径**：`/backtests`

**作用**：单次回测的"驾驶舱"。选策略 + 选数据 + 配参数 → 一键跑。

> ⚠️ **本节经过 2026-06-18 实际核查** [`BacktestWorkspace.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/backtests/BacktestWorkspace.vue)，下述字段为**真实存在的 UI**。手填 Date Range / 多 Symbols 选择 / Engine 选择 / Paper 模式切换 等常见能力**当前均未提供**。

### 7.1 页面分区

#### 7.1.1 左侧：配置面板（实际字段）
| 区块 | 字段 | 控件 | 备注 |
|------|------|------|------|
| **Strategy** | `selectedStrategyId` | el-select | 从 strategyStore.items 中选；触发 onStrategyChange |
| **Dataset** | `selectedDatasetId` | el-select | 从 datasetStore.items 中选；触发 onDatasetChange |
| **Parameters**（动态） | 来自策略 spec 的 `param` 列表 | el-switch / el-select / el-input-number / el-input | 按 `param.type` 选控件；bool→switch、有 choices→select、int/float→number、其他→string |
| **Advanced**（可折叠，点击 section-label 展开/收起） | Initial Cash | el-input-number | 默认 1000，步长 10000 |
| | Commission (bps) | el-input-number | 步长 0.5，精度 1 位 |
| | Slippage (bps) | el-input-number | 步长 0.5，精度 1 位 |
| **Run** | Run Backtest | el-button（type=primary，size=large） | 禁用条件：`!canRun`（策略/数据集都没选则不能跑） |
| | 进度条 | el-progress | 跑起来后显示，绑定 `btStore.taskProgress` |
| | 当前阶段文案 | text | 跑起来后显示 `btStore.taskStatus` |
| | 错误提示 | text | 跑失败时显示 `btStore.error` |
| | 成功跳转 | el-button (link) | 跑完显示 "Backtest completed!" + "View Experiment →" 跳转到 Experiment Detail |

#### 7.1.2 右侧：预览面板
- **空态**（未选 dataset）：显示 DataLine 图标 + "Select a dataset to preview"
- **K 线图**（仅当选中 dataset 且 `is_ohlcv=true`）：CandlestickChart 组件
- **Dataset Info**（小卡片网格）：
  - Symbol
  - Rows（千分位格式化）
  - Range（`formatDate(start) ~ formatDate(end)`，**只读不可改**）

### 7.2 ❌ 当前版本**不提供**的字段（与你的预期对照）

- ❌ **Date Range 输入框**——时间范围**完全由所选 Dataset 决定**，右侧只读显示
- ❌ **Symbols 多选**——Dataset 单 symbol（前面 §6.1 已说明）
- ❌ **Engine 切换**（bar / event / vectorbt）——无
- ❌ **Execution Mode**（backtest / paper）——无
- ❌ **取消按钮**——进度跑起来后无取消入口
- ❌ **保存为 Experiment 按钮**（带备注）——回测**自动**写入 Experiment，**通过** "View Experiment →" 进入详情
- ❌ **Walk-Forward / 双引擎校验 / 并行优化 / Tick 模式**——配置面板**没有这些折叠区**

### 7.3 典型操作流程（实际可走通）
1. 选 **Strategy**（左侧第一个下拉）
2. 选 **Dataset**（左侧第二个下拉）
3. **Parameters 区块**自动出现（来自策略 spec 的所有 param 字段）
4. （可选）展开 **Advanced** → 调 cash / commission / slippage
5. 点 **Run Backtest**
6. 进度条出现，等跑完
7. 成功后点 **View Experiment →** 跳到 `/experiments/:id` 看完整结果（含 Equity Curve / Metrics / Trades，由 ExperimentDetail 渲染）

### 7.4 适用场景
- 快速跑**单次**回测（不是参数扫描/网格优化）
- 拿到一个 experiment_id 之后跳去 **Compare** 页面跟其他实验对比
- 时间范围需求**只通过换 Dataset 实现**（需要新数据请在 `data/` 准备新 CSV 重启后端，或写脚本 `registry.register_from_dataframe`）

---

## 8. Factors（因子）

**路径**：`/factors`（侧边栏 "Factors"）

**作用**：因子库的"实验室"——可视化因子曲线 + 算 IC + 算相关性。

> ⚠️ **本节经过 2026-06-18 实际核查** [`FactorStudio.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/factors/FactorStudio.vue)，下述功能为**真实存在的 UI**。多选 Symbol / 选时间区间 / 调因子参数 N / 分层回测 当前均**未提供**。

### 8.1 页面顶部：4 个筛选器（横向）
| # | 控件 | 字段 | 备注 |
|---|------|------|------|
| 1 | el-select（**单选**，clearable） | `selectedCategory` | 因子分类（momentum / volatility / volume / liquidity …），改了调 `loadFactors` |
| 2 | el-select（**单选**，非 clearable） | `selectedDataset` | 数据集，改了调 `onDatasetChange` 拉 `symbols` |
| 3 | el-select（**单选**，clearable，width=140px） | `selectedSymbol` | 标的，**只能选一个** |
| 4 | el-button (icon=Refresh, circle) | — | 重新拉因子列表 |

### 8.2 因子列表（卡片网格）
- 每个因子是一个 `.factor-card`，点击 → `selectFactor(name)` 切到详情面板
- 卡片显示：`name` + `category` 标签（dark 风格） + `description`
- 选中状态：`.active` 高亮

### 8.3 因子详情面板：3 个 Tab

#### Tab 1: Visualization
- 工具栏：**Load Chart** 按钮（type=primary, size=small）
- 加载后渲染 **2 个 echarts 图表**：
  - **Price Chart**（`priceChartRef`）—— 价格时序
  - **Factor Chart**（`factorChartRef`）—— 因子值时序
- 空态：提示 "Select a dataset and click Load Chart to visualize the factor."

#### Tab 2: IC Analysis
- 工具栏：
  - `el-select`：Forward period 1 / 5 / 10 / 20 bars
  - **Run IC Analysis** 按钮
- 加载后渲染 **8 张指标卡**（`.ic-stats-grid`）+ IC 时序图（`icChartRef`）：

| 卡片 | 含义 |
|------|------|
| Mean IC | 皮尔森 IC 均值 |
| IC IR | IC 信息比（mean / std） |
| IC > 0 | IC 为正的占比（%） |
| Mean Rank IC | 斯皮尔曼 Rank IC 均值 |
| Rank IC IR | Rank IC 信息比 |
| Turnover | 因子换手率 |
| Coverage | 覆盖率（%） |
| Periods | 样本数 |

#### Tab 3: Correlation
- 工具栏：
  - `el-select multiple`：选**多个因子**（不是标的多选）
  - **Compute Correlation** 按钮（至少选 2 个才能点）
- 加载后渲染：**相关性矩阵**（`corrChartRef`）

### 8.4 ❌ 当前版本**不提供**的能力（与你的预期对照）
- ❌ **多选 symbol** —— Symbol 是单选
- ❌ **选时间区间** —— 整个页面没有 el-date-picker / start / end
- ❌ **调因子参数 N**（如 MA 周期）—— 各因子参数**硬编码**，UI 不可改
- ❌ **分层回测**（按因子分 5/10 桶的收益曲线）—— 当前**无此 Tab**
- ❌ **IC decay**（半衰期）—— 指标卡里**没有 decay 这一项**

### 8.5 实际能用的工作流
1. 顶部选 **Category**（如 momentum）→ 卡片网格刷新
2. 顶部选 **Dataset + Symbol**（每个 dataset 默认选第一个 symbol）
3. 点因子卡片 → 进详情面板
4. **Visualization** Tab → Load Chart → 看价格 + 因子曲线
5. **IC Analysis** Tab → 选 Forward 1 bars → Run IC Analysis → 看 8 项指标
6. **Correlation** Tab → 选 ≥2 个因子 → Compute Correlation → 看相关性矩阵

> 备注：想跑"按因子分桶的回测"请去 **Backtest Workspace**（`/backtests`）用策略做；Factor Studio 当前**不直接做**分桶回测。

---

## 9. Signal Research（信号研究）

**路径**：`/signals`

**作用**：比 Factor 更高一层——把因子组合成"信号"，并分析信号覆盖率、可视化、远期收益。

> ⚠️ **本节经过 2026-06-18 实际核查** [`SignalWorkspace.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/signals/SignalWorkspace.vue)，下述功能为**真实存在的 UI**。信号热力图、信号驱动的回测结果 当前均**未提供**（回测请去 §7 Backtest Workspace）。

### 9.1 页面顶部：筛选器
| 控件 | 字段 | 备注 |
|------|------|------|
| el-select | `selectedDataset` | 数据集，改了调 `onDatasetChange` 拉 `symbols` |
| el-select（clearable，width=140px） | `selectedSymbol` | 标的，**只能选一个** |
| el-button（icon=Refresh, circle） | — | 重新拉信号列表 |

### 9.2 左侧：Signal Builder + 信号列表

#### 9.2.1 Signal Builder（3 个 Tab）

**Tab 1: Threshold**
| 字段 | 控件 | 备注 |
|------|------|------|
| Factor | el-select（filterable） | 从 `factorList` 中选 |
| Op | el-select | `<` / `<=` / `>` / `>=` / `==` |
| Value | el-input-number | 阈值 |
| Direction | el-select | `long` / `short` |
| Build | el-button（type=primary, size=small） | 构建信号 |

**Tab 2: Crossover**
| 字段 | 控件 | 备注 |
|------|------|------|
| Fast | el-select（filterable） | 快线因子 |
| Slow | el-select（filterable） | 慢线因子 |
| Build | el-button（type=primary, size=small） | 构建交叉信号 |

**Tab 3: Combine**
| 字段 | 控件 | 备注 |
|------|------|------|
| Select signals | el-select（**multiple**，width=300px） | 选 ≥2 个已有信号 |
| Logic | el-select | `AND` / `OR` / `MAJORITY` |
| Combine | el-button（type=primary, size=small） | 合并信号；`disabled` 当 `combineSignals_.length < 2` |

#### 9.2.2 信号列表
- 每个信号是一个 `.signal-item`，点击 → `selectSignal(name)` 切到详情面板
- 卡片显示：`name` + `type` 标签（ThresholdSignal / CrossoverSignal / ZeroCrossoverSignal / AndSignal / OrSignal / MajoritySignal）
- 选中状态：`.active` 高亮

### 9.3 右侧：Signal Detail（3 个 Tab）

#### Tab 1: Coverage
- 工具栏：**Analyze** 按钮（type=primary, size=small）
- 加载后渲染 **5 张统计卡**（`.coverage-grid`）：

| 卡片 | 含义 |
|------|------|
| Total Bars | 总 bar 数 |
| Long Signals | 多头信号数 + 占比 |
| Short Signals | 空头信号数 + 占比 |
| Neutral | 中性信号数 |
| Coverage | 覆盖率（%） |

#### Tab 2: Visualization
- 工具栏：**Load Chart** 按钮（type=primary, size=small）
- 加载后渲染 **2 个 echarts 图表**：
  - **Price Chart**（`priceChartRef`）—— K 线图
  - **Signal Chart**（`signalChartRef`）—— 信号时序柱状图（Long 绿 / Short 红）

#### Tab 3: Forward Return
- 工具栏：**Run Analysis** 按钮（type=primary, size=small）
- 加载后渲染 **远期收益表**（`fwdTableData`）：

| 列 | 含义 |
|------|------|
| Period | 远期 bar 数（1 bar / 5 bars / 10 bars / 20 bars） |
| Long Mean | 多头信号远期收益均值 |
| Long WR | 多头胜率（%） |
| Short Mean | 空头信号远期收益均值 |
| Short WR | 空头胜率（%） |
| Count | 样本数 |

### 9.4 ❌ 当前版本**不提供**的能力
- ❌ **信号热力图**（标的 × 时间）—— 无
- ❌ **信号驱动的回测**—— 请去 §7 Backtest Workspace
- ❌ **权重线性组合**（如 `MA_cross * 0.7 + RSI_zone * 0.3 > 0.5`）—— Combine 只支持 AND / OR / MAJORITY 逻辑组合
- ❌ **多 symbol 信号对比** —— Symbol 是单选

### 9.5 实际能用的工作流
1. 顶部选 **Dataset + Symbol**
2. 左侧 **Signal Builder** 选 Tab（Threshold / Crossover / Combine）→ 填表 → Build
3. 信号列表刷新，点击信号 → 右侧详情
4. **Coverage** Tab → Analyze → 看 5 项统计
5. **Visualization** Tab → Load Chart → 看 K 线 + 信号柱状图
6. **Forward Return** Tab → Run Analysis → 看远期收益表

---

## 10. Research Lab（实验流水线）

**路径**：`/research`

**作用**：参数扫描、热力图、Walk-Forward、候选过滤、鲁棒性分析、研究报告。

> ⚠️ **本节经过 2026-06-18 实际核查** [`ResearchLab.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/research/ResearchLab.vue)，下述功能为**真实存在的 UI**。先前文档描述的 "Batch Configuration / Pipeline Options / Run & Monitor" 三大模块**均不存在**。

### 10.1 页面结构：6 个 Tab

#### 10.1.1 Parameter Sweep
左右分栏布局：

**左侧：Sweep Configuration**
| 字段 | 控件 | 备注 |
|------|------|------|
| Strategy | el-input | 策略 ID（如 `ma_cross`） |
| Dataset | el-input | 数据集 ID（如 `default`） |
| Parameters | 动态行 | 每行：`param_key`（disabled）+ `param_vals`（逗号分隔，如 `5,10,20`）+ Delete 按钮 |
| 新增参数行 | el-input + el-input + Plus 按钮 | 输入 param name + vals → 添加 |
| Run Sweep | el-button（type=primary, width=100%） | 执行参数扫描 |

**Sweep History**（扫描完成后显示）：
- 列表显示历史 sweep，点击可切换查看

**右侧：Results**
- 统计栏：Total / Completed / Best Sharpe / Avg Sharpe
- 结果表：各参数列 + Sharpe / Return / MaxDD / Trades / WinRate（均可排序）

#### 10.1.2 Heatmap
- 前置条件：需先跑 Parameter Sweep
- 工具栏：
  - X Axis（el-select）：选参数
  - Y Axis（el-select）：选参数
  - Metric（el-select）：`sharpe` / `total_return` / `max_drawdown`
  - **Generate Heatmap** 按钮
- 输出：echarts 热力图（420px 高）

#### 10.1.3 Walk Forward
- 工具栏：
  - Strategy（el-select）：`ma_cross` / `rsi_reversal`
  - Train Years（el-input-number，1~10）
  - Test Years（el-input-number，1~5）
  - **Run Walk Forward** 按钮
- 输出：
  - 统计栏：Windows / Avg OOS Sharpe / Avg OOS Return / Stability
  - 窗口表：# / Train / Test / Train Sharpe / Test Sharpe / Test Return / MaxDD / Best Params

#### 10.1.4 Candidates
- 前置条件：需先跑 Parameter Sweep
- 工具栏：
  - min Sharpe（el-input-number，step=0.1）
  - max DD（el-input-number，step=0.05，0~1）
  - min trades（el-input-number，step=10）
  - **Find Candidates** 按钮
- 输出：
  - 统计栏：Found 数量
  - 候选表：各参数列 + Sharpe / Return / MaxDD / Trades / WinRate

#### 10.1.5 Robustness
- 前置条件：需先跑 Parameter Sweep
- 工具栏：
  - Metric（el-select）：`sharpe` / `total_return`
  - **Calculate Robustness** 按钮
- 输出：
  - **5 张卡片**：Best Params / Best Metric / Neighbors / Neighbor Std / **Robustness Score**（>60% 绿 / 30~60% 黄 / <30% 红）
  - 邻居性能分布图（echarts，280px 高）

#### 10.1.6 Report
- 前置条件：需先跑 Parameter Sweep
- 工具栏：**Generate Report** 按钮
- 输出：
  - Report Header：strategy_id / dataset_id / generated_at
  - Overview：Best Sharpe / Best Return / Avg Sharpe / Total Combos
  - Robustness：Score / Neighbor Std
  - Candidates（Top 5）：各参数列 + Sharpe / Return

### 10.2 ❌ 当前版本**不提供**的能力
- ❌ **Strategy Pool 多选** —— Strategy 是单输入
- ❌ **Dataset Pool 多选** —— Dataset 是单输入
- ❌ **Parallelism 选择**（thread / process / subprocess）—— 无
- ❌ **Early Filter / Top-K 保留** —— 无
- ❌ **实时进度条 + 预计剩余时间** —— 无
- ❌ **Stop 按钮** —— 无
- ❌ **失败列表 + 错误日志** —— 无

### 10.3 实际能用的工作流
1. **Parameter Sweep** Tab → 输 Strategy + Dataset + 参数网格 → Run Sweep
2. 切到 **Heatmap** Tab → 选 X/Y 参数 + Metric → Generate Heatmap
3. 切到 **Walk Forward** Tab → 选 Strategy + Train/Test Years → Run Walk Forward
4. 切到 **Candidates** Tab → 设 min Sharpe / max DD / min trades → Find Candidates
5. 切到 **Robustness** Tab → 选 Metric → Calculate Robustness
6. 切到 **Report** Tab → Generate Report → 看汇总报告

---

## 11. Experiments（实验管理）

**路径**：`/experiments`

**作用**：所有回测的"档案库"，SQLite 持久化。

> ⚠️ **本节经过 2026-06-18 实际核查** [`ExperimentList.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/experiments/ExperimentList.vue) + [`ExperimentDetail.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/experiments/ExperimentDetail.vue)，下述功能为**真实存在的 UI**。

### 11.1 列表视图

**实际列**：

| 列 | 含义 |
|----|------|
| （选择框） | 多选用于 Compare |
| Experiment | 名称 + ID + Status 标签（candidate/production）+ Folder 标签 + ★收藏 |
| Strategy | 策略名 |
| Return | 总收益（%，绿正红负，可排序） |
| Sharpe | 夏普（可排序） |
| MaxDD | 最大回撤（%，红色，可排序） |
| Win% | 胜率 |
| Trades | 交易数 |
| Created | 创建日期 |
| Actions | 下拉菜单：Mark Candidate / Mark Production / Set Normal / Move to Folder |

### 11.2 顶部操作栏
- **搜索框**：按 name / id / strategy / note 模糊搜索
- **Sort by**：Return / Sharpe / MaxDD / Created（点击切换升降序）
- **Status 过滤**：Normal / Candidate / Production
- **Folder 过滤**：按文件夹过滤
- **Compare** 按钮（选中 ≥2 个时显示）：跳转 `/compare`
- **Refresh** 按钮

### 11.3 Experiment Detail（`/experiments/:id`）

5 个 Tab：

#### Tab 1: Overview
- **Metrics Grid**：所有核心指标卡片（Sharpe / Sortino / Max DD / Win Rate / PF / Expectancy / Total Return / Annualized Return 等）
- **Parameters**：策略参数列表

#### Tab 2: Performance
- **Equity Curve & Drawdown**：合并图表
- **Monthly Returns Heatmap**：月度收益热力图
- **Annual Returns**：年度收益柱状图

#### Tab 3: Trades
- **Trade Records**：交易表（TradesWidget 组件）
- **PnL Distribution**：PnL 分布图
- **Holding Time**：持仓时间统计卡
- **Top Winners / Top Losers**：左右对比列表

#### Tab 4: Risk
- **Rolling Sharpe (60d)**：滚动夏普
- **Rolling Max Drawdown (60d)**：滚动回撤
- **Rolling Volatility (60d)**：滚动波动率
- （数据不足 60 bars 时显示空态）

#### Tab 5: Journal
- **Candidate Pipeline**：状态流水线（normal → candidate → production），可点击切换
- **Bookmark**：收藏/取消收藏
- **Research Notes**：文本框 + Save Note 按钮
- **Tags**：标签管理（添加/删除）

### 11.4 ❌ 当前版本**不提供**的能力
- ❌ **Dataset 列** —— 列表中无 Dataset 列（详情页有显示）
- ❌ **Date Range 列** —— 列表中无时间区间列
- ❌ **血缘（Lineage）Tab** —— 无派生链展示
- ❌ **导出报告**（HTML / JSON）—— 无导出按钮
- ❌ **复制配置**（跳到 BacktestWorkspace 预填）—— 无此按钮
- ❌ **删除实验** —— 无删除功能

---

## 12. Compare（实验对比）

**路径**：`/compare`

**作用**：并排对比多个实验的收益曲线、指标、参数差异。

> ⚠️ **本节经过 2026-06-18 实际核查** [`ExperimentCompare.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/compare/ExperimentCompare.vue)，下述功能为**真实存在的 UI**。

### 12.1 操作流程
1. 在 `/experiments` 列表选中 ≥2 个实验
2. 点 **Compare** 按钮 → 跳转 `/compare?ids=id1,id2`
3. 自动加载对比数据

### 12.2 对比内容（3 个区块）

#### 12.2.1 Equity Curve Comparison
- 多条权益曲线叠加图（vue-echarts）
- 每个实验一种颜色

#### 12.2.2 Metrics Comparison
- 并排指标表：

| 列 | 含义 |
|----|------|
| Experiment | 名称 + 颜色点 |
| Strategy | 策略名 |
| Return | 总收益（%，可排序） |
| Sharpe | 夏普（可排序） |
| MaxDD | 最大回撤（%，可排序） |
| Win% | 胜率 |
| Trades | 交易数 |
| Final Equity | 最终权益 |

#### 12.2.3 Parameter Differences
- 参数差异表（仅当实验间参数不同时显示）
- 列：Parameter + 各实验的参数值（不同的高亮）

### 12.3 ❌ 当前版本**不提供**的能力
- ❌ **Drawdown 叠加** —— 无独立 Drawdown 图
- ❌ **Return Distribution 直方图对比** —— 无
- ❌ **拖拽排序** —— 无
- ❌ **Add to Compare 按钮**（在 Experiment Detail 页）—— 只能在列表页多选

---

## 13. Leaderboard（排行榜）

**路径**：`/leaderboard`

**作用**：所有 Experiment 按关键指标排名，卡片式展示。

> ⚠️ **本节经过 2026-06-18 实际核查** [`LeaderboardPage.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/leaderboard/LeaderboardPage.vue)，下述功能为**真实存在的 UI**。

### 13.1 顶部操作栏
- **Metric** 排序：Sharpe Ratio（默认）/ Total Return / Max Drawdown / Win Rate
- **Top N**：Top 10 / Top 20（默认）/ Top 50
- **Refresh** 按钮

### 13.2 卡片式排行
- 每个实验一张卡片（`.lb-card`），Top 3 有特殊样式（金/银/铜）
- 卡片内容：
  - **Rank**：排名数字（1 金 / 2 银 / 3 铜 / 其他数字）
  - **Name**：实验名
  - **Strategy**：策略名
  - **Return**：总收益（%，绿正红负）
  - **Sharpe**：夏普
  - **MaxDD**：最大回撤（%）
  - **Badges**：Candidate / Production 标签 + ★收藏标记
- **点击卡片**：跳转 `/experiments/:id`

### 13.3 ❌ 当前版本**不提供**的能力
- ❌ **Sortino / Calmar 排序** —— 只有 Sharpe / Return / MaxDD / WinRate
- ❌ **时间范围 / 策略 / 数据集过滤** —— 无
- ❌ **过拟合检测标签** —— 无
- ❌ **加入对比按钮** —— 无
- ❌ **一键复现**（跳到 BacktestWorkspace 预填）—— 无

### 13.4 适用场景
- 选 SOTA 策略上 live
- 看排名找退化策略

---

## 14. Production Studio（生产运行时）

**路径**：`/production`

**作用**：监控一台交易机器的运行状态、资金、风险、持仓、订单、PnL、日志、恢复。

> ⚠️ **本节经过 2026-06-18 实际核查** [`ProductionStudio.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/production/ProductionStudio.vue)，下述功能为**真实存在的 UI**。先前文档描述的 "Accounts / Strategies / Allocations / Supervisor" 等 Tab **均不存在**。

### 14.1 顶部操作栏
- **Runtime 状态标签**（el-tag，effect=dark）：`IDLE` / `RUNNING` / `PAUSED` / `STOPPING` / `STOPPED` / `READONLY` / `RECOVERING`
- **Kill Switch 标签**（el-tag，type=danger）：触发时显示 `KILL SWITCH ACTIVE`
- **按钮组**：
  - **Start**（icon=VideoPlay）：启动 Runtime（`disabled` 当 state=`RUNNING`）
  - **Pause**（icon=VideoPause）：暂停（`disabled` 当 state≠`RUNNING`）
  - **Stop**（icon=CircleClose）：停止（`disabled` 当 state=`STOPPED`）
  - **KILL SWITCH**（type=danger，icon=WarningFilled）：手动触发 Kill Switch（`disabled` 当已触发）

### 14.2 主体 Tabs（8 个）

#### 14.2.1 Overview
4 张指标卡（`.metrics-grid`）：

| 卡片 | 字段 |
|------|------|
| **Runtime** | State / Ticks / Errors / Readonly |
| **Capital** | Total / Allocated / Available |
| **Health** | All Alive / Components / Watchdog Alerts |
| **Self-Healing** | Total Heals / Success Rate |

#### 14.2.2 Execution Health
- **Heartbeat Monitor** 表：Component / Beats / Status（ALIVE/DEAD）/ Last Beat / Lag (s)
- **Watchdog Alerts** 表：Level（CRITICAL/WARNING）/ Category / Message / Time

#### 14.2.3 Risk
- **Risk Engine** 描述列表：Kill Switch 状态 / Rejects Count
- **Recent Rejects** 表（有数据时显示）：Reason / Symbol / Qty / Time

#### 14.2.4 Positions
- **Portfolio Positions** 表：Symbol / Qty / Avg Price / Market Price / Market Value / Unrealized PnL / Strategy

#### 14.2.5 Orders
- **Recent Orders** 表：Order ID / Symbol / Side（BUY/SELL）/ Qty / Filled / State / Signal ID / Strategy

#### 14.2.6 PnL Attribution
6 张 PnL 卡片（`.pnl-grid`）：

| 卡片 | 含义 |
|------|------|
| Total PnL | 总 PnL |
| Market PnL | 市场收益 |
| Strategy PnL | 策略收益 |
| Execution PnL | 执行收益 |
| Slippage Cost | 滑点成本（负值） |
| Commission Cost | 手续费成本（负值） |

#### 14.2.7 Journal
- **Trade Journal** 表（可按 Type 过滤：All / Signal / Order / Fill / Risk Alert / Kill Switch / Recovery）
- 列：Time / Type / Strategy / Symbol / Message

#### 14.2.8 System Status
3 个区块：
- **Recovery Status**：State Restorer / Order Recovery / Position Recovery
- **Self-Healing History**：Total Heals / Successful / Success Rate + 历史表（Time / Action / Reason / Status）
- **Replay Engine**：Position / Total Events / Progress

### 14.3 ❌ 当前版本**不提供**的能力
- ❌ **Accounts Tab**（账户列表 + 启用/停用/调拨）—— 无
- ❌ **Strategies Tab**（已注册策略 + 单策略启停）—— 无
- ❌ **Allocations Tab**（资金分配矩阵）—— 无
- ❌ **Supervisor Tab**（系统级 Kill Switch 阈值配置）—— 无
- ❌ **策略注册入口** —— 无 Register 按钮
- ❌ **账户管理** —— 无账户列表

### 14.4 实际能用的工作流
1. 顶部看 **Runtime 状态** → 确认是否 RUNNING
2. **Overview** Tab → 看 4 张卡（Runtime / Capital / Health / Self-Healing）
3. **Execution Health** Tab → 看心跳 + Watchdog 告警
4. **Risk** Tab → 看 Kill Switch + 拒单列表
5. **Positions** Tab → 看实时持仓
6. **Orders** Tab → 看最近订单
7. **PnL Attribution** Tab → 看 PnL 分解
8. **Journal** Tab → 按类型过滤看交易日志
9. **System Status** Tab → 看恢复状态 + 自愈历史 + 重放引擎
10. 紧急情况 → 点顶部 **KILL SWITCH** 按钮

---

## 15. Execution Fidelity Studio（V3.5）

**路径**：`/fidelity`

**作用**：把"纸面交易"逼近"真实交易"。订单簿模拟、冲击建模、成本分解、Fill 引擎、影子模式、自适应拆单、True PnL。

> ⚠️ **本节经过 2026-06-18 实际核查** [`FidelityStudio.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/fidelity/FidelityStudio.vue)，下述功能为**真实存在的 UI**。

### 15.1 顶部操作栏
- **Refresh** 按钮（icon=Refresh）：重新拉取所有数据

### 15.2 Overview Tab：6 张 Summary 卡片
| 卡片 | 含义 |
|------|------|
| Fill Engines | symbols 数 |
| Avg Cost | total execution cost（bps） |
| Latency | avg round-trip（ms） |
| Shadow Alerts | critical alerts 数 |
| True PnL | net of all costs |
| Adaptive Plans | execution plans 数 |

### 15.3 主体 Tabs（8 个）

#### 15.3.1 Order Book
- **控制栏**：Symbol / Mid Price / Volatility / Volume / **Generate** / **Sweep Market**（Side + Qty）
- **输出**：
  - 左：Asks 表（Price / Qty，前 10 档）
  - 右：Bids 表（Price / Qty，前 10 档）
  - Sweep Result：Avg Price / Impact (bps) / Filled

#### 15.3.2 Impact
- **控制栏**：Order Qty / Mid Price / Volume / Volatility / Model（`sqrt` / `linear` / `power`）/ **Calculate** / **Suggest Split**
- **输出**：
  - Impact Result：Impact (bps) / Impact Price / Impact Cost / Permanent / Temporary / Model
  - Split Suggestion：N slices + 各 slice qty

#### 15.3.3 Cost
- **控制栏**：Symbol / Side / Qty / Price / Slippage (bps) / Volume / Volatility / **Calculate**
- **输出**：Cost Breakdown（Fee / Slippage / Impact / Opportunity / Funding / **Total**）

#### 15.3.4 Fill Engine
- **控制栏**：Order ID / Symbol / Side / Qty / Order Type（`MARKET` / `LIMIT`）/ Mid Price / Volatility / Volume / **Process Order**
- **输出**：
  - Fill Result：Fill ID / Filled Qty / Fill Price / Slippage (bps) / Commission / Partial
  - Fills 表（多档成交时）：Price / Qty

#### 15.3.5 Shadow Mode
- **Shadow Mode Summary**：Comparisons / OK / Warning / Critical
- **Record Fills** 控制栏：Order ID / Symbol / Qty / Paper Price / Live Price / **Record & Compare** / **Compare All**
- **Comparisons 表**：Order ID / Symbol / Paper Price / Live Price / Diff (bps) / Severity（CRITICAL/WARNING/OK）

#### 15.3.6 Adaptive
- **控制栏**：Order ID / Symbol / Side / Total Qty / Volatility / Liquidity Score / Urgency / **Generate Plan**
- **输出**：
  - Execution Plan：Regime / Style + Rationale（el-alert）
  - Slices 表：# / Qty / Delay (ms) / Type

#### 15.3.7 True PnL
- **控制栏**：Symbol / Qty / Avg Entry / **Update Position** / Price / **Update Price** / **Compute True PnL**
- **输出**：
  - True PnL Report：Gross PnL / Total Cost / **True PnL** / Fee / Slippage / Impact / True PnL (bps) / Cost Drag (bps)
  - Positions 表：Symbol / Qty / Avg Entry / Current / Gross / Cost / True PnL

### 15.4 ❌ 当前版本**不提供**的能力
- ❌ **成本结构饼图** —— Cost Tab 只有描述列表，无饼图
- ❌ **Shadow Mode PDF 报告** —— 无导出功能
- ❌ **Shadow Mode Stop 按钮** —— 无启停控制，只有 Record & Compare

### 15.5 典型流程：策略上线前的真实化测试
1. 在 **Order Book** 生成一个市场 → Sweep Market 看扫单结果
2. 算 **Impact** → 看冲击 bps + 建议拆单
3. 算 **Cost** → 看成本分解
4. **Fill Engine** 模拟下单 → 看 fill 报告
5. **Adaptive** 生成拆单计划
6. **Shadow Mode** 录入 paper/live fill → 对比差异
7. **True PnL** 录入持仓 + 价格 → 计算真实 PnL

---

## 16. Alpha-Aware Studio（V3.6）

**路径**：`/alpha-aware`

**作用**：评估策略的"市场存活率"——从"预测收益"到"真实可交易"。

> ⚠️ **本节经过 2026-06-18 实际核查** [`AlphaAwareStudio.vue`](file:///d:/python_workspace/quantlab/frontend/src/views/alpha_aware/AlphaAwareStudio.vue)，下述功能为**真实存在的 UI**。

### 16.1 顶部操作栏
- **一键全流程评估** 按钮（type=primary，icon=MagicStick）：自动跑完 10 个模块

### 16.2 Summary 卡片（评估完成后显示）
5 张卡片（`.summary-grid`）：

| 卡片 | 含义 |
|------|------|
| 可实现性 | `realizability_verdict` |
| 生存判定 | `survival_verdict` |
| 可交易评级 | `tradeability_rank`（S/A/B/C/D/F） |
| 真实夏普 | `adjusted_sharpe` |
| 推荐实盘 | `is_recommended`（YES/NO） |

### 16.3 主体 Tabs（10 个模块各一 Tab）

#### ① Realizability
- **表单**：IC / IC IR / Sharpe / Turnover / Avg Return / Slippage (bps)
- **按钮**：评估可实现性
- **输出**：Signal Strength / Liquidity Score / Turnover Penalty / Cost Adjusted Return / **Real Score** / **Real Sharpe** + Verdict + Warnings

#### ② Turnover
- **表单**：持仓序列（逗号分隔）/ 资金量 / 手续费率 / 滑点 (bps)
- **按钮**：分析换手压力
- **输出**：日均换手 / 最大日换手 / 年化换手 / 年化成本 / 成本拖累 / **压力评分** + 可持续判定

#### ③ Liquidity
- **表单**：Symbol / 24h Volume (USD) / Spread (bps) / Depth (USD) / Volatility / Impact (bps)
- **按钮**：流动性过滤
- **输出**：Verdict + Overall Score + 分项分数进度条 + 拒绝原因

#### ④ Sensitivity
- **表单**：Base Sharpe / Base Return / Slippage Sensitivity
- **按钮**：执行敏感性测试
- **输出**：Sharpe Stability / Return Degradation / **Breakpoint Multiplier** + 场景表（Scenario / Slippage Mult / Sharpe / Return / Cost Ratio / Profitable）+ Verdict

#### ⑤ Latency
- **表单**：Base Sharpe / Alpha Decay Rate (/ms)
- **按钮**：延迟脆弱性测试
- **输出**：Alpha Half Life (ms) / Critical Latency (ms) / Latency Class / Scalable + 场景表（Scenario / Delay / Sharpe / Alpha Decay / Fill Rate）+ Verdict

#### ⑥ Impact BT
- **表单**：Paper Sharpe / Paper Return / Volume / Volatility
- **按钮**：冲击回测
- **输出**：Paper Sharpe / **Real Sharpe** / Sharpe Decay / Paper Return / **Real Return** / Return Decay / Total Impact Cost / Avg Impact / Max Impact

#### ⑦ Adj Sharpe
- **表单**：Paper Sharpe / Annual Return / Turnover / Fee Rate / Slippage (bps)
- **按钮**：计算执行调整夏普
- **输出**：
  - 对比框：Paper Sharpe → Real Sharpe + Grade
  - 分解：Fee Penalty / Slippage Penalty / Impact Penalty / **Total Penalty**
  - Verdict + 是否达机构标准

#### ⑧ Survival
- **表单**：IC Mean / IC IR / IC Hit Rate / Turnover / Slippage Sensitivity / Breakpoint Mult / Liquidity Score / Real Sharpe
- **按钮**：评估生存能力
- **输出**：Verdict + Survival Score（进度条）+ 分项分数 + Strengths / Failure Reasons

#### ⑨ Features
- **表单**：RSI / Momentum / Mean Reversion
- **市场环境**：Volume / Spread (bps) / Depth / Volatility / Turnover / Impact (bps)
- **按钮**：执行感知特征调整
- **输出**：特征表（Feature / Original / Adjusted / Weight / Adjustment Factor）

#### ⑩ Tradeability
- **按钮**：计算可交易评分
- **输出**：
  - Alpha Score + Rank（大标签）
  - 分项分数进度条
  - Strengths / Weaknesses（左右卡片）
  - Recommendations（el-alert）

### 16.4 ❌ 当前版本**不提供**的能力
- ❌ **PDF 报告导出** —— 一键评估后无导出按钮
- ❌ **自动跑完 10 个模块的进度条** —— 只有一个 loading 状态

### 16.5 典型流程：策略最终评估
1. 点顶部 **一键全流程评估** → 等 loading 完成
2. 看顶部 5 张 Summary 卡片
3. **Rank F → 拒绝**（无论回测多漂亮）
4. **Rank C → 修短板**（看哪个分项低）
5. **Rank ≥ B → 进 Production Studio**
6. 也可单独进某个 Tab 手动调参评估

---

## 17. 通用操作

> ⚠️ **本节经过 2026-06-18 实际核查** [`TopBar.vue`](file:///d:/python_workspace/quantlab/frontend/src/components/TopBar.vue)，下述功能为**真实存在的 UI**。

### 17.1 顶部 TopBar
- **左侧**：当前页标题（取自 `route.meta.title`）+ 分隔符 + "Research Platform" 副标题
- **右侧**：
  - **Workspace 预设切换器**（仅在 `/studio` 路径显示）：下拉切换 Workspace 预设
  - **主题切换**：Moon / Sunny 图标，切换 Light / Dark
  - **System Status**：绿色圆点 + "System Online" 文本（静态显示，非 API 健康检查）

### 17.2 ❌ 当前版本**不提供**的能力
- ❌ **全局快捷键**（`Ctrl+K` / `Esc` / `/`）—— 代码中无任何 keydown 监听
- ❌ **表格列头右键菜单**（显示/隐藏列）—— 无此功能
- ❌ **表头拖拽调整列顺序** —— 无此功能
- ❌ **表格行数切换**（10/25/50/100）—— 无分页组件
- ❌ **图表导出 PNG** —— 无导出按钮
- ❌ **数据导入 CSV / Parquet** —— 无上传组件
- ❌ **导入策略 `.py`** —— Strategies 列表无 Import 按钮
- ❌ **导出报告**（HTML / JSON）—— Experiment Detail 无导出按钮
- ❌ **导出 Fidelity 报告** —— Fidelity Studio 无下载功能
- ❌ **导出 Alpha-Aware 报告** —— Alpha-Aware Studio 无 PDF 导出

### 17.3 实际可用的通用交互
- **表格排序**：点击支持 sortable 的列头切换升降序
- **表格行点击**：多数列表行可点击跳转详情
- **图表交互**：vue-echarts 原生支持滚轮缩放、拖拽平移、图例点击
- **主题切换**：TopBar 右侧图标一键切换 Light / Dark

---

## 18. 常见问题 FAQ

### 18.1 启动 / 部署

**Q：前端报 `Failed to fetch dynamically imported module`**
- A：检查 `frontend/src/utils/api.ts` 是否存在；检查后端是否启动在 8000 端口。

**Q：Vite 启动报端口占用**
- A：执行 `Stop-Process -Id <PID> -Force` 或修改 `vite.config.ts` 的 `server.port`。

**Q：前端调 API 跨域**
- A：后端已配置 CORS。检查 `.env` 的 `CORS_ORIGINS` 是否包含 `http://localhost:5173`。

### 18.2 策略相关

**Q：跑回测时 `numpy.float64 has no attribute rolling`**
- A：策略被错误地传了"单行 DataFrame"。在 `/production` 页面注册时**必须**传 `full_data=data`。

**Q：双引擎一致性的 Sharpe 差距 > 30%**
- A：先看 metrics 表里哪个分项差。常见原因：BarEngine 用 close 价，VectorBT 用 vwap。

**Q：策略名报错 `must be a valid Python identifier`**
- A：策略名**只允许**英文、数字、下划线；不能以数字开头。

### 18.3 Fidelity / Alpha-Aware

**Q：`real_score` 一直为 0**
- A：检查 `cost_adjusted_return`。如果是负的，看 turnover 是不是太高（>20%/日）或者 fee 设错。

**Q：`adaptive_plan` 切片数 = 1**
- A：检查 `urgency` 参数。如果设了 0.9+，大资金会变 single slice；建议 ≤ 0.7。

**Q：`survival_score` 0.61 vs 0.95 都 `SURVIVES`**
- A：V3.6 的 0.6 是**通过线**。实盘请看**具体分数**，0.61 策略实盘表现远差于 0.95。

**Q：Tradeability F 策略回测 Sharpe 2.0，能不能小资金试试？**
- A：**不能**。F 策略通常"延迟敏感 / 流动性差 / 换手爆炸"。小资金也救不了这些问题。

**Q：Shadow Mode paper 和 live 价差很大**
- A：检查 `PaperBroker` 的滑点假设。常见原因：假设 `0 bps` 而 live 是 5 bps。建议统一设 2~3 bps。

### 18.4 Production 相关

**Q：V3.4 的 AccountManager 和 V2.5 的 LiveEngine 冲突吗？**
- A：不冲突但**不要混用**。新代码全部走 `StrategyRuntime + PortfolioSupervisor`；V2.5 LiveEngine 标记 deprecated。

**Q：Kill Switch 触发了怎么恢复？**
- A：Production Studio → Supervisor → **Reset**，并人工确认 root cause 后再 ARM。

**Q：`full_data` 必须传吗？**
- A：必须。V3.4 的 `sup.register_strategy(..., full_data=data)` 强制要求，否则 `signal()` 在单行 DataFrame 上 `rolling` 会报错。

### 18.5 性能

**Q：100 个标的 × 1 年数据，Fidelity + Alpha-Aware 要跑多久？**
- A：< 1s。可以加进每日 Pipeline。

**Q：VectorBT 在我机器上崩溃**
- A：切到 SubprocessVectorBT；并行优化时设 `PARALLEL_USE_THREAD=1`。

---

## 附录 A：典型用户角色使用流程

### A.1 量化研究员（一线）
1. `/strategy-builder` → 搭一个新策略
2. `/backtests` → 跑单次回测，看 Sharpe
3. `/fidelity` → 真实化评估（True PnL ≥ 0）
4. `/alpha-aware` → 全流程评估（Rank ≥ B）
5. `/experiments` → 入库，写好备注

### A.2 策略 PM（决策）
1. `/leaderboard` → 找 Sharpe Top 5
2. `/compare` → 并排对比前 5
3. `/experiments/:id` → 看详情 + 血缘
4. 选 Top 1 推上线 → 转交 A.3

### A.3 运维 / 实盘负责人
1. `/production` → 启用账户 + 分配资金
2. `/production` → Register 策略（带 full_data）
3. `/production` → Start
4. `/production` → Supervisor 监控（告警 / Kill Switch）
5. 每周：检查 `cost_drag_bps`、Shadow Mode 状态

### A.4 量化新人
1. `/studio` → 熟悉首页
2. `/datasets` → 找一个示例数据集
3. `/backtests` → 跑一个内置策略（如 MaCross）
4. `/experiments` → 看指标怎么读
5. `/strategy-builder` → 自己改参数，再跑
6. `/leaderboard` → 看到自己的实验上榜

---

## 附录 B：术语速查

| 术语 | 含义 |
|------|------|
| **bps** | 1 bps = 0.01% |
| **IC** | 信息系数，预测值与实际收益的相关系数 |
| **Rank IC** | 用 Rank 而非线性值算的 IC |
| **Slippage** | 实际成交价 vs 预期价的差 |
| **Impact** | 你下单对市场价格的扰动 |
| **Turnover** | Σ|position_t - position_{t-1}| |
| **Sharpe** | 风险调整后收益（年化 mean/std × √252） |
| **Sortino** | 只惩罚下行波动版的 Sharpe |
| **Max DD** | 最大回撤 |
| **Profit Factor** | 总盈利 / abs(总亏损) |
| **Calmar** | 年化收益 / abs(Max DD) |
| **Paper Trading** | 模拟盘，下单走模拟 broker |
| **Live Trading** | 实盘 |
| **Kill Switch** | 一键停机 |
| **Cost Drag (bps)** | 全部成本占收益的比例 |
| **Survival Score** | V3.6 的"是否能活下来"分 |
| **Tradeability Rank** | V3.6 的 S~F 综合评级 |

---

**文档版本**：v3.6
**最后更新**：2026-06-17
