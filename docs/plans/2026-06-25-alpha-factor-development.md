# Alpha191 + Alpha101 因子开发计划

> **项目代号**：Alpha Factory（因子工厂）
> **创建日期**：2026-06-25
> **状态**：📋 规划中（待评审）
> **数据来源**：
> - `docs/国泰君安Alpha191因子公式详解.md`（191 个因子）
> - `docs/WorldQuant_101_Alphas_完整解析.md`（101 个因子）
> **核心理念**：先建算子底座，再批量产因子；算子统一、因子可测、回测可验

---

## 〇、项目背景与现状诊断

### 0.1 因子资源现状

项目已沉淀两份高质量因子公式文档：

| 文档 | 因子数 | 算子数 | 分类数 | 数据要求 |
|------|--------|--------|--------|----------|
| 国泰君安 Alpha191 | 191 | 28 个 | 8 大类 | OHLCV + VWAP + AMOUNT + 基准指数 |
| WorldQuant Alpha101 | 101 | 20 个 | 11 大类 | OHLCV + VWAP + adv20 + cap + 行业分类 |

两套算子体系高度重叠（RANK/rank、CORR/correlation、DELTA/delta、DELAY/delay、STD/stddev、SUM/ts_sum、MEAN/sma、TSMAX/ts_max、TSMIN/ts_min、DECAYLINEAR/decay_linear 等），但命名风格不同（Alpha191 全大写，Alpha101 全小写），且存在各自独有算子：

- **Alpha191 独有**：TSRANK、WMA、REGBETA、SUMIF、SUMAC、HIGHDAY、LOWDAY、SEQUENCE、BANCHMARKINDEX*
- **Alpha101 独有**：ts_argmax、ts_argmin、scale、product、SignedPower、IndNeutralize、sign、abs、log

### 0.2 代码基础设施现状（关键发现）

经实地核查 `quantlab/` 包目录，**README 与 STRATEGY_DEV_GUIDE 中描述的核心回测框架模块当前并不存在**：

| 模块 | 文档描述 | 实际状态 |
|------|----------|----------|
| `quantlab/signals/` | SignalStrategy 基类 + MACross/RSI/Alpha001 | ❌ 缺失 |
| `quantlab/factors/` | 因子函数库（ma 等） | ❌ 缺失 |
| `quantlab/engine/` | BarEngine / EventEngine | ❌ 缺失 |
| `quantlab/portfolio_construction/` | TopN / EqualWeight | ❌ 缺失 |
| `quantlab/research/` | Experiment / Report / ValidationRunner | ❌ 缺失 |
| `quantlab/optimizer/` | Optimizer / FastOptimizer | ❌ 缺失 |
| `quantlab/strategy/` | 旧策略入口 | ❌ 缺失 |
| `quantlab/event/`、`quantlab/event_engine/` | 事件总线 | ❌ 缺失 |
| `quantlab/_compat.py`、`quantlab/__init__.py` | 包初始化 | ❌ 缺失 |

**已实现模块**：`api/`、`asset/`、`asset_package/`、`execution/`（较完整）、`ml/`（较完整）、`services/`、`strategy_studio/`

**结论**：`main.py` 与 `examples/` 中引用 `from quantlab.signals import ...` 等导入当前会失败。因子开发计划必须从算子底座与因子基类开始建设，不能假设回测框架已就绪。

### 0.3 计划目标

1. 建立统一的因子算子库（覆盖两套文档全部算子）
2. 分批实现 Alpha191（191 个）与 Alpha101（101 个）因子，共 292 个
3. 每个因子具备最小单元测试与回测验证
4. 因子可注册到现有 AssetRegistry，可被 ML Lab 复用为 FeatureSet
5. 文档完备，与现有因子体系（文档描述的 factors/signals）对齐

---

## 一、因子需求分析

### 1.1 待开发因子筛选与优先级

考虑到 292 个因子规模庞大，按"算子依赖少 → 多、逻辑简单 → 复杂、数据要求低 → 高"排序，分四批开发：

#### 第一批：基础因子（P0，共 60 个）

选取仅依赖 OHLCV + 简单算子（DELAY/DELTA/MEAN/SUM/STD/RANK）的因子，用于打通算子库与回测链路。

> **图例**：✅ 已完成 | ⚠️ 阻塞（需特殊依赖/长窗口/文字描述/STUB） | ⛔ 阻塞于 adv20

**Alpha191 P0 因子进度表（25 个）**

| 因子 | 状态 | 说明 |
|------|------|------|
| #14 | ✅ 已完成 | 5日动量 |
| #15 | ✅ 已完成 | 隔夜收益率 |
| #54 | ✅ 已完成 | 量价偏离 |
| #70 | ✅ 已完成 | 成交量标准化 |
| #95 | ✅ 已完成 | 成交额波动率 |
| #97 | ✅ 已完成 | 量价相关 |
| #100 | ✅ 已完成 | 量价标准化 |
| #118 | ✅ 已完成 | 影线比 |
| #127 | ✅ 已完成 | 回撤RMS |
| #76 | ✅ 已完成 | STD(\|RET\|/V,20)/MEAN(\|RET\|/V,20)，成交量效率变异系数 |
| #137 | ✅ 已完成 | Wilders TR-normalised，TR 算子已实现 |
| #158 | ✅ 已完成 | (HIGH-LOW)/CLOSE 振幅比率 |
| #161 | ✅ 已完成 | MEAN(TR,12) 12日ATR，TR 算子已实现 |
| #175 | ✅ 已完成 | MEAN(TR,6) 6日ATR，TR 算子已实现 |
| #188 | ✅ 已完成 | 振幅偏离率，SMA 算子已实现 |
| #189 | ✅ 已完成 | MEAN(ABS(CLOSE-MA6),6) MAD |
| #165 | ✅ 已完成 | 48日累积偏离极差，SUMAC 算子已实现 |
| #183 | ✅ 已完成 | 24日累积偏离极差，SUMAC 算子已实现 |
| #30 | ⛔ STUB | `WMA(REGRESI(...)^2,20)` [STUB-公式不完整]，需 Fama-French 三因子回归 |
| #50 | ⛔ 文字描述 | 下突破占比-上突破占比(12日) — 需人工解读突破定义 |
| #51 | ⛔ 文字描述 | 纯下突破占比(12日) — 需人工解读突破定义 |
| #93 | ⛔ 文字描述 | 20日开盘向下突破累积 — 需人工解读突破定义 |
| #144 | ⛔ 文字描述 | 20日下跌日\|RET\|/AMOUNT均值 — 需人工解读"下跌日"逻辑 |
| #160 | ⛔ 文字描述 | SMA(下跌日STD(CLOSE,20),20,1) — 需人工解读"下跌日"逻辑 |
| #174 | ⛔ 文字描述 | SMA(上涨日STD(CLOSE,20),20,1) — 需人工解读"上涨日"逻辑 |

**Alpha101 P0 因子进度表（35 个）**

| 因子 | 状态 | 说明 |
|------|------|------|
| #4 | ✅ 已完成 | 低价时序排名反转 |
| #6 | ✅ 已完成 | 开盘价-成交量负相关 |
| #9 | ✅ 已完成 | 趋势一致性 |
| #10 | ✅ 已完成 | 趋势一致性截面排名 |
| #12 | ✅ 已完成 | 量价方向符号 |
| #20 | ✅ 已完成 | 开盘缺口三因子乘积 |
| #22 | ✅ 已完成 | 量价相关变化-波动率 |
| #23 | ✅ 已完成 | 价格突破反转 |
| #33 | ✅ 已完成 | 日内涨跌幅排名 |
| #34 | ✅ 已完成 | 波动率比率-价格变化 |
| #38 | ✅ 已完成 | 价格时序排名-日内比率 |
| #40 | ✅ 已完成 | 波动率-量价相关 |
| #41 | ✅ 已完成 | 几何均价-VWAP偏离 |
| #42 | ✅ 已完成 | VWAP偏离比率 |
| #44 | ✅ 已完成 | 价格-成交量排名相关 |
| #46 | ✅ 已完成 | 价格加速度 |
| #49 | ✅ 已完成 | 价格加速度阈值 |
| #51 | ✅ 已完成 | 最低价时序排名极值 |
| #53 | ✅ 已完成 | K线形态变化 |
| #55 | ✅ 已完成 | 开盘价偏离-日内变化 |
| #8 | ✅ 已完成 | -1*rank(sum(open,5)*sum(returns,5)-delay(...,10))，OHLCV+returns |
| #26 | ✅ 已完成 | -1*ts_max(corr(ts_rank(volume,5),ts_rank(high,5),5),3)，纯 OHLCV |
| #27 | ✅ 已完成 | 二值阈值，需 vwap |
| #30 | ✅ 已完成 | 价格方向一致性-成交量比，纯 OHLCV |
| #35 | ✅ 已完成 | 多因子时序排名，OHLCV+returns |
| #37 | ✅ 已完成 | 200日长窗口相关，纯 OHLCV |
| #45 | ✅ 已完成 | 三因子乘积，纯 OHLCV |
| #19 | ✅ 已完成 | 250日累计收益率，长历史数据已支持 (300日) |
| #24 | ✅ 已完成 | 100日均线变化率，长历史数据已支持 |
| #32 | ✅ 已完成 | 230日量价相关+vwap，长历史数据已支持 |
| #29 | ✅ 已完成 | 深层嵌套动量反转，scale/log/product 算子已实现 |
| #25 | ✅ 已完成 | rank((-returns)*adv20*vwap*(high-close))，FactorContext.get_adv 解锁 |
| #28 | ✅ 已完成 | scale(corr(adv20,low,5)+(high+low)/2-close)，FactorContext.get_adv 解锁 |
| #31 | ✅ 已完成 | 多因子组合，含 corr(adv20,low,12)，FactorContext.get_adv 解锁 |
| #36 | ✅ 已完成 | 加权多因子，含 adv20+vwap+200日，FactorContext.get_adv 解锁 |
| #39 | ✅ 已完成 | 含 decay_linear(volume/adv20,9)+250日收益，FactorContext.get_adv 解锁 |
| #43 | ✅ 已完成 | ts_rank(volume/adv20,20)*ts_rank(-delta(close,7),8)，FactorContext.get_adv 解锁 |
| #47 | ✅ 已完成 | 复合量价因子，含 adv20+vwap，FactorContext.get_adv 解锁 |

> **注**：上表已超额列入 #49-#55 部分，Alpha101 P0 实际计划因子为 35 个，已完成 20 个。

#### ⛔ Alpha101 剩余因子阻塞说明（建议扩展 FactorContext 支持 adv20）

Alpha101 P0 剩余 18 个因子中，**7 个可直接实现**（依赖 OHLCV/returns/vwap，算子已具备），**11 个被阻塞**，阻塞原因分布：

| 阻塞类型 | 因子 | 数量 | 解锁方案 |
|----------|------|------|----------|
| adv20 依赖 | #25, #28, #31, #39, #43, #47 | 6 | 扩展 `FactorContext.get_adv(n)` 方法，计算 `ts_mean(volume, 20)` |
| adv20 + vwap + 长窗口 | #36 | 1 | 同上 + 提供 200 日以上历史数据 |
| 深层嵌套 | #29 | 1 | 实现 `scale`/`log`/`product` 算子 |
| 长窗口（100/230/250 日） | #19, #24, #32 | 3 | 提供足够长的历史数据（≥250 日） |

**建议优先级**：
1. **最高优先级**：扩展 `FactorContext.get_adv(n=20)` → 立即解锁 7 个因子（#25, #28, #31, #39, #43, #47, #36）
2. 次优先级：实现 `scale`/`log`/`product` 算子 → 解锁 #29
3. 长窗口因子（#19, #24, #32）仅需提供长历史数据，无需新增算子

#### 第二批：量价相关因子（P1，共 80 个）

依赖 CORR/COV/TSRANK/ts_rank 等相关性算子，涵盖量价关系核心逻辑。

| 来源 | 因子编号 | 数量 |
|------|----------|------|
| Alpha191 | 1, 2, 3, 5, 7, 11, 16, 32, 33, 35, 36, 39, 40, 42, 43, 44, 45, 60, 61, 62, 64, 68, 73, 74, 77, 83, 84, 87, 90, 91, 92, 99 | 32 |
| Alpha101 | 2, 3, 13, 14, 15, 16, 44, 50, 68, 72, 75, 78, 85 | 13 |
| Alpha101（VWAP 偏离类） | 5, 11, 41, 42, 61, 62, 71 | 7 |
| Alpha101（量价方向类） | 7, 12, 43, 60 | 4 |
| 其他量价类 | 见文档分类 | 24 |

#### 第三批：动量与均值回复因子（P2，共 90 个）

依赖 SMA/WMA/DECAYLINEAR/REGBETA 等平滑与回归算子。

| 来源 | 因子编号 | 数量 |
|------|----------|------|
| Alpha191 动量类 | 6, 8, 14, 15, 17, 18, 20, 21, 24, 25, 27, 28, 29, 37, 38, 41, 48, 53, 57, 58, 67, 75, 79, 85, 86, 88, 89, 96, 98 等 | 56 |
| Alpha191 均值回复类 | 2, 4, 12, 13, 19, 22, 26, 31, 34, 46, 47, 65, 66, 71, 72, 78, 82 | 17 |
| Alpha101 动量/趋势类 | 8, 9, 10, 17, 19, 22, 25, 46, 49, 57, 73, 77 | 12 |
| Alpha101 K 线形态类 | 33, 41, 53, 54, 101 | 5 |

#### 第四批：复杂与特殊因子（P3，共 62 个）

依赖行业中性化、基准指数、市值数据、深层嵌套等。

| 来源 | 因子编号 | 数量 | 特殊依赖 |
|------|----------|------|----------|
| Alpha101 行业中性化 | 48, 56, 58, 59, 63, 66, 67, 69, 70, 76, 79, 80, 82, 84, 87, 89, 90, 91, 93, 97, 100 | 21 | IndNeutralize + 行业分类 |
| Alpha191 基准类 | 75, 149, 181, 182 | 4 | 基准指数 OHLC |
| Alpha101 深层嵌套 | 29, 36 | 2 | 多层嵌套非线性 |
| Alpha191 成交量类 | 80, 81, 102, 111, 120, 124, 128, 132, 134, 145, 150, 155, 168, 170, 178, 191 | 16 | AMOUNT/VOLUME 异常 |
| Alpha191 剩余波动率/相关性 | 49, 76, 93, 95, 97, 100, 109, 118, 127, 137, 144, 158, 160, 161, 165, 174, 175, 183, 188, 189 等 | 19 | STD + 多算子组合 |

### 1.2 数据来源与频率要求

| 数据项 | 频率 | 来源 | 适用因子 |
|--------|------|------|----------|
| OPEN / HIGH / LOW / CLOSE | 日频 | 市场数据（后复权） | 全部 292 个 |
| VOLUME | 日频 | 市场数据 | 全部 292 个 |
| VWAP | 日频 | 分时数据聚合 / 日频近似 | Alpha191 大部分 + Alpha101 VWAP 类 |
| AMOUNT | 日频 | 市场数据 | Alpha191 成交量类 |
| adv20（20 日均量） | 日频 | `SMA(VOLUME, 20)` 计算 | Alpha101 多个因子 |
| RET（日收益率） | 日频 | `CLOSE/DELAY(CLOSE,1)-1` 计算 | Alpha101 多个因子 |
| cap（市值） | 日频 | 财务/估值数据 | Alpha101 部分因子 |
| IndClass（行业分类） | 低频 | 行业映射表 | Alpha101 行业中性化类（21 个） |
| 基准指数 OHLC | 日频 | 指数行情 | Alpha191 基准类（4 个） |

**数据约束**（遵循项目规则）：
- 数据库中的市场数据必须是干净的、可信任的，模拟数据绝不写入数据库
- 首次回测使用较短时间范围的历史数据，确保测试效率

### 1.3 算子统一映射表

将两套算子统一为内部命名（小写下划线风格，与 STRATEGY_DEV_GUIDE 一致）：

| 内部算子 | Alpha191 名称 | Alpha101 名称 | 实现优先级 |
|----------|---------------|---------------|-----------|
| `delay(x, n)` | DELAY | delay | P0 |
| `delta(x, n)` | DELTA | delta | P0 |
| `rank(x)` | RANK | rank | P0 |
| `ts_rank(x, n)` | TSRANK | ts_rank | P0 |
| `corr(x, y, n)` | CORR | correlation | P0 |
| `cov(x, y, n)` | COV/COVARIANCE | covariance | P0 |
| `mean(x, n)` | MEAN | sma（简单） | P0 |
| `sum(x, n)` | SUM | ts_sum | P0 |
| `std(x, n)` | STD | stddev | P0 |
| `ts_max(x, n)` | TSMAX | ts_max | P0 |
| `ts_min(x, n)` | TSMIN | ts_min | P0 |
| `decay_linear(x, n)` | DECAYLINEAR | decay_linear | P0 |
| `sma(x, n, m)` | SMA（指数，alpha=m/n） | — | P1 |
| `wma(x, n)` | WMA（线性加权） | — | P1 |
| `regbeta(x, y, n)` | REGBETA | — | P1 |
| `ts_argmax(x, n)` | — | ts_argmax | P1 |
| `ts_argmin(x, n)` | — | ts_argmin | P1 |
| `scale(x, k)` | — | scale | P1 |
| `product(x, n)` | — | product | P1 |
| `signed_power(x, a)` | — | SignedPower | P1 |
| `sum_if(x, n, cond)` | SUMIF | — | P2 |
| `cumsum(x)` | SUMAC | — | P2 |
| `highday(high, n)` | HIGHDAY | — | P2 |
| `lowday(low, n)` | LOWDAY | — | P2 |
| `ind_neutralize(x, g)` | — | IndNeutralize | P3 |
| `sign(x)` / `abs(x)` / `log(x)` | 隐含 | sign/abs/log | P0（内置） |

---

## 二、开发流程设计

### 2.1 因子开发标准步骤（每个因子必走）

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 公式解析                                        │
│  从文档提取公式 → 确认算子依赖 → 确认数据字段            │
├─────────────────────────────────────────────────────────┤
│  Step 2: 算子实现/复用                                   │
│  检查算子库是否已有 → 无则实现算子 + 单元测试             │
├─────────────────────────────────────────────────────────┤
│  Step 3: 因子函数实现                                    │
│  quantlab/factors/alpha191/alpha_XXX.py                 │
│  或 quantlab/factors/alpha101/alpha_XX.py                │
│  函数签名: def alpha_XXX(ctx) -> pd.DataFrame            │
├─────────────────────────────────────────────────────────┤
│  Step 4: 最小单元测试                                    │
│  tests/test_alpha_XXX.py → 构造已知数据 → 断言因子值      │
├─────────────────────────────────────────────────────────┤
│  Step 5: 策略封装（可选）                                 │
│  AlphaXXXStrategy(SignalStrategy) → signal(ctx)          │
├─────────────────────────────────────────────────────────┤
│  Step 6: 回测验证                                        │
│  短历史数据回测 → 检查信号分布、换手率、收益              │
├─────────────────────────────────────────────────────────┤
│  Step 7: 文档与注册                                      │
│  更新因子文档 → 注册到 AssetRegistry                      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 函数设计规范

#### 算子层（`quantlab/factors/operators/`）

```python
# quantlab/factors/operators/ts.py
def delay(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时序延迟 n 期"""
    return x.shift(n)

def delta(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时序差分: x - delay(x, n)"""
    return x - x.shift(n)

def ts_rank(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时间序列排名: 过去 n 期的百分位排名 (0~1)"""
    return x.rolling(n).apply(lambda s: s.rank().iloc[-1] / n, raw=False)
```

- 输入输出统一为 `pd.DataFrame`（index=date, columns=symbol）
- 纯函数，无副作用，可组合
- 每个算子一个独立单元测试

#### 因子层（`quantlab/factors/alpha191/`、`quantlab/factors/alpha101/`）

```python
# quantlab/factors/alpha191/alpha_014.py
"""Alpha191 #14: CLOSE-DELAY(CLOSE,5) — 5日动量"""
from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, delta

def alpha_014(ctx: FactorContext) -> pd.DataFrame:
    close = ctx.close
    return close - delay(close, 5)
```

- 因子函数签名统一：`def alpha_XXX(ctx: FactorContext) -> pd.DataFrame`
- `FactorContext` 封装 OHLCV/VWAP/AMOUNT 等数据，避免长参数列表
- 一个因子一个文件，文件名 `alpha_XXX.py`
- 文件头注释公式原文与分类

#### 策略层（`quantlab/signals/`）

```python
# quantlab/signals/alpha_014.py
from quantlab.signals.base import SignalStrategy
from quantlab.factors.alpha191.alpha_014 import alpha_014

class Alpha014Strategy(SignalStrategy):
    def __init__(self, period: int = 5):
        self.period = period

    def signal(self, ctx) -> pd.DataFrame:
        return alpha_014(ctx)  # 返回连续因子值，由 PortfolioConstructor 截面排名
```

### 2.3 参数定义规范

- 参数必须可被 `int/float/bool/str` 序列化（遵循 STRATEGY_DEV_GUIDE 硬约束）
- 窗口期参数命名：`n`（通用）、`fast`/`slow`（快慢线）
- 因子方向通过 `direction` 字段标注（`+1` 正向 / `-1` 反向），不在公式内硬编码取负

### 2.4 数据处理规范

| 场景 | 处理方式 |
|------|----------|
| `HIGH == LOW`（涨跌停/停牌） | 分母为零时返回 `NaN`，不抛异常 |
| `VOLUME == 0`（停牌） | `log(VOLUME)` 前做 `max(VOLUME, 1)` 下限保护 |
| `VWAP` 缺失 | 日频近似 `AMOUNT / VOLUME`，VOLUME=0 时用 CLOSE 替代 |
| 前 N 期数据不足 | 返回 `NaN`，回测引擎自动跳过预热期 |
| 除权除息 | 使用后复权价格 |
| 停牌日 | 因子值置 `NaN`，不参与截面排名 |

---

## 三、系统影响评估

### 3.1 对现有架构的影响

```
                    ┌─────────────────────────────┐
                    │      新增模块（本次）         │
                    │  quantlab/factors/          │
                    │    ├── operators/            │
                    │    ├── alpha191/             │
                    │    ├── alpha101/             │
                    │    └── context.py            │
                    │  quantlab/signals/          │
                    │    └── alpha_*.py            │
                    └──────────────┬──────────────┘
                                   │ 依赖
                    ┌──────────────▼──────────────┐
                    │   现有模块（已实现）          │
                    │  quantlab/asset/            │
                    │  quantlab/asset_package/    │
                    │  quantlab/ml/feature/       │
                    │  quantlab/api/              │
                    └──────────────┬──────────────┘
                                   │ 需新建（前置依赖）
                    ┌──────────────▼──────────────┐
                    │   缺失模块（需先补建）        │
                    │  quantlab/signals/base.py   │
                    │  quantlab/engine/            │
                    │  quantlab/portfolio_*        │
                    │  quantlab/research/          │
                    └─────────────────────────────┘
```

**影响评估**：

| 影响项 | 影响程度 | 说明 |
|--------|----------|------|
| 现有 `asset/` 模块 | 低 | 因子可注册为 AssetPackage，接口已就绪 |
| 现有 `ml/feature/` 模块 | 中 | 因子需适配为 FeatureSet 供 ML 使用，需增加适配器 |
| 现有 `api/` 模块 | 中 | 需新增因子查询/计算 API 端点 |
| 现有 `execution/` 模块 | 无 | 因子层不直接依赖执行层 |
| 缺失的 `engine/` 等 | 高 | **回测验证依赖引擎，必须先补建最小可用引擎** |

### 3.2 性能影响

| 场景 | 预估耗时 | 优化策略 |
|------|----------|----------|
| 单因子计算（3000 股 × 250 日） | < 50ms | 向量化 pandas/numpy |
| 292 因子全量计算 | ~15s | 并行计算（joblib）+ 算子缓存 |
| `CORR` / `REGBETA` 滚动窗口 | 较慢 | 使用 `numpy.lib.stride_tricks` 或 `numba` 加速 |
| 截面 `RANK` | 快 | pandas `rank(axis=1)` 原生支持 |

**缓存策略**：相同算子相同输入的结果缓存（如 `CORR(CLOSE, VOLUME, 10)` 被多因子复用）

### 3.3 兼容性

- 因子层与算子层为**纯新增**，不修改现有 `execution/ml/asset` 代码
- `FactorContext` 作为数据适配层，隔离因子与底层数据源
- 与文档描述的 `quantlab/signals/base.SignalStrategy` 接口对齐，未来引擎实现后可直接接入

---

## 四、实施步骤规划

### 4.1 阶段总览

```
Phase 0: 基础设施补建 ──→ Phase 1: 算子库 ──→ Phase 2: P0 因子 ──→ Phase 3: P1 因子
                                                        │
Phase 5: 文档与注册 ←── Phase 4: P2/P3 因子 ←────────────┘
```

### 4.2 Phase 0：基础设施补建（前置依赖）

**目标**：补建因子开发所必需的最小回测框架

| 任务 | 交付物 | 责任 |
|------|--------|------|
| 0.1 创建 `quantlab/__init__.py` | 包初始化 | 后端 |
| 0.2 创建 `quantlab/factors/` 目录结构 | 目录 + `__init__.py` | 后端 |
| 0.3 实现 `FactorContext` 数据上下文 | `factors/context.py` | 后端 |
| 0.4 实现 `SignalStrategy` 基类 | `signals/base.py` | 后端 |
| 0.5 补建最小可用 `BarEngine` | `engine/bar.py` | 后端 |
| 0.6 补建 `TopN` 组合构造器 | `portfolio_construction/topn.py` | 后端 |
| 0.7 补建 `Experiment` + `Report` | `research/experiment.py` | 后端 |

**验收标准**：`Alpha014Strategy` 能跑通一次完整回测并输出 Report

### 4.3 Phase 1：算子库实现

**目标**：实现 P0 + P1 级算子（共 22 个），每个算子配单元测试

| 任务 | 交付物 |
|------|--------|
| 1.1 时序算子（delay/delta/ts_rank/ts_max/ts_min/ts_argmax/ts_argmin） | `operators/ts.py` + 测试 |
| 1.2 截面算子（rank/scale/ind_neutralize） | `operators/cross_section.py` + 测试 |
| 1.3 统计算子（corr/cov/mean/sum/std/product） | `operators/stats.py` + 测试 |
| 1.4 平滑算子（sma/wma/decay_linear） | `operators/smooth.py` + 测试 |
| 1.5 回归算子（regbeta） | `operators/regression.py` + 测试 |
| 1.6 工具算子（signed_power/sum_if/cumsum/highday/lowday/sequence） | `operators/misc.py` + 测试 |

**验收标准**：算子单元测试覆盖率 100%，与文档公式手算结果一致

### 4.4 Phase 2：P0 基础因子（60 个）

**目标**：实现第一批 60 个基础因子，打通"公式 → 因子 → 测试 → 回测"全链路

| 任务 | 交付物 |
|------|--------|
| 2.1 Alpha191 P0 因子（25 个） | `factors/alpha191/alpha_014.py` 等 + 测试 |
| 2.2 Alpha101 P0 因子（35 个） | `factors/alpha101/alpha_004.py` 等 + 测试 |
| 2.3 因子策略封装 | `signals/alpha_*.py` |
| 2.4 批量回测脚本 | `examples/run_alpha_batch.py` |

**验收标准**：60 个因子全部通过单元测试 + 短历史回测无异常

### 4.5 Phase 3：P1 量价相关因子（80 个）

**目标**：实现量价相关性、VWAP 偏离类因子

| 任务 | 交付物 |
|------|--------|
| 3.1 Alpha191 量价类因子（32 个） | `factors/alpha191/` + 测试 |
| 3.2 Alpha101 量价相关因子（48 个） | `factors/alpha101/` + 测试 |
| 3.3 因子相关性矩阵分析 | 分析报告 |

### 4.6 Phase 4：P2/P3 复杂因子（152 个）

**目标**：实现动量、均值回复、波动率、行业中性化、基准类因子

| 任务 | 交付物 |
|------|--------|
| 4.1 Alpha191 动量 + 均值回复因子（73 个） | `factors/alpha191/` + 测试 |
| 4.2 Alpha101 动量 + K 线形态因子（17 个） | `factors/alpha101/` + 测试 |
| 4.3 Alpha101 行业中性化因子（21 个） | 需行业分类数据 |
| 4.4 Alpha191 基准类因子（4 个） | 需基准指数数据 |
| 4.5 剩余因子（37 个） | 按分类补全 |

#### 4.6.1 Phase 4 批次进度表

> **图例**：✅ 已完成 | ⚠️ 跳过（STUB/数据依赖） | 🚧 进行中 | 📋 待开发

**Alpha191 批次（共 155 个：实现 131 个 + 跳过 24 个）**

| 批次 | 分类 | 因子范围 | 实现数 | 跳过数 | 状态 | 说明 |
|------|------|----------|--------|--------|------|------|
| 6a | 相关性类第一批 | #1,2,3,5,7,11,16,32,33,35,36 | 11 | 0 | ✅ | 11个量价相关因子 |
| 6b | 相关性/量价类剩余 | #39,40,42,43,44,45,60,61,62,64,68,73,74,77 | 14 | 0 | ✅ | 含VWAP偏离+量价相关 |
| 7 | 成交量类+价格类 | #80,81,102,111,120,124,126,128,132,134,145,150,155,168,178,191 | 16 | 1 | ✅ | 跳过#170(STUB) |
| 8 | 动量类+波动率类 | #10,85,88,89,96,103,106,107,109,112,116,117,144,160,174 | 15 | 9 | ✅ | 标注9个STUB(#23,25,37,49,50,51,86,93,98) |
| 9 | 动量/量价/成交量/相关性/波动率补充 | #9,59,63,94,105 | 5 | 0 | ✅ | 新增5因子: #9价格效率SMA/#59 TR累积/#63 6日RSI/#94 30日OBV/#105开盘量价背离 |
| 10 | 动量/量价/反转类第一批 | #4,52,55,56,69,101 | 6 | 0 | ✅ | 动量反转+量价综合因子，已修复alpha_004/101的NaN保护 |
| 11 | 均值回复/动量类 | #110,113,114,115,119,121 | 6 | 0 | ✅ | 量价相关+波动率综合 |
| 12 | 量价/动量类 | #122,123,125,129,130,131 | 6 | 0 | ✅ | 量价背离+相关性排名 |
| 13 | 均值回复/动量类 | #133,135,136,138,139,140 | 6 | 0 | ✅ | 量价相关性+RSI+收益率平滑 |
| 14 | 动量/量价类 | #141,142,146,147,148,151 | 6 | 0 | ✅ | 量价相关性+趋势排名 |
| 15 | 动量/反转/量价类 | #152,153,154,156,157,159 | 6 | 0 | ✅ | SMA延迟+量价排名 |
| 16 | 动量/量价类 | #162,163,164,166,167,169 | 6 | 0 | ✅ | SMA差值+量价相关性 |
| 17 | 均值回复/动量/量价类 | #171,172,173,176,177,179 | 6 | 0 | ✅ | 均值偏离+时序排名 |
| 18 | 量价/反转/动量类 | #180,184,185,186,187,190 | 6 | 0 | ✅ | 放量反转+波动率+对数收益率 |

**Alpha101 批次（共 17 个：全部实现）**

| 批次 | 分类 | 因子范围 | 实现数 | 跳过数 | 状态 | 说明 |
|------|------|----------|--------|--------|------|------|
| 9 | 动量+K线类 | #1,2,3,5,7,11,13,14,15,16,17,18,21,50,52,54,57 | 17 | 0 | ✅ | 含波动率+量价相关+趋势一致性 |

#### 4.6.2 跳过因子汇总

**Alpha191 跳过因子（共 24 个）**

| 类型 | 因子 | 原因 |
|------|------|------|
| STUB（公式不明确/递归自引用） | #23,25,37,49,50,51,86,93,98 | 公式不完整或需Fama-French三因子回归 |
| STUB | #30 | WMA(REGRESI(...)^2,20) 公式不完整 |
| STUB | #170 | 公式不明确 |
| 数据依赖-基准指数 | #75,149,181,182 | 需基准指数OHLC数据 |
| 数据依赖-行业中性化 | Alpha101 #48,56,58,59,63,66,67,69,70,76,79,80,82,84,87,89,90,91,93,97,100 | 需行业分类数据 |
| 数据依赖-市值 | Alpha101部分因子 | 需cap市值数据 |

#### 4.6.3 关键技术修复记录

| 修复项 | 影响范围 | 说明 |
|--------|----------|------|
| `ts_rank` 窗口含NaN处理 | Alpha191批次8 #117 | 窗口含NaN时返回NaN，避免错误排名传播 |
| `sum_if` 预热期 | Alpha191批次7 #128, 批次8 #144 | 算子将NaN替换为0.0，预热期需精确计算 |
| 幂运算inf处理 | Alpha191 #108 | `result.replace([np.inf, -np.inf], np.nan)` |
| 条件因子预热期 | Alpha101 #7, #21 | 预热期(adv/ma为NaN)需显式mask返回NaN |

### 4.7 Phase 5：文档与资产注册

| 任务 | 交付物 |
|------|--------|
| 5.1 因子目录索引 | `docs/factor_catalog.md` |
| 5.2 因子注册到 AssetRegistry | 自动注册脚本 |
| 5.3 因子 API 端点 | `/api/v1/factors/*` |
| 5.4 前端因子工作室对接 | `FactorStudio.vue` 数据接入 |

### 4.8 时间表与责任人

| 阶段 | 任务量 | 责任人 | 里程碑 |
|------|--------|--------|--------|
| Phase 0 | 7 项 | 后端工程师 | 基础设施就绪，Alpha014 可回测 |
| Phase 1 | 22 算子 | 后端工程师 | 算子库完备，测试覆盖 100% |
| Phase 2 | 60 因子 | 后端工程师 | P0 因子全链路打通 |
| Phase 3 | 80 因子 | 后端工程师 | 量价因子完成 |
| Phase 4 | 152 因子 | 后端工程师 | 全部 292 因子完成 |
| Phase 5 | 文档+注册 | 后端 + 前端 | 因子可查可用 |
| 全程 | 质量保障 | QA / 策略研究员 | 每批因子验收 |

> 注：遵循项目规则"避免给出时间预估"，上表不标注具体工期，以里程碑驱动。

---

## 五、质量保障措施

### 5.1 因子正确性验证方法

#### 5.1.1 算子级验证

每个算子必须通过以下测试：

```python
# tests/operators/test_ts.py
def test_delay():
    df = pd.DataFrame({"A": [1, 2, 3, 4, 5]})
    result = delay(df, 2)
    assert result["A"].iloc[0:2].isna().all()  # 前两期为 NaN
    assert result["A"].iloc[2] == 1            # 第三期 = 第一期
    assert result["A"].iloc[4] == 3            # 第五期 = 第三期

def test_corr_against_numpy():
    # 与 numpy.corrcoef 交叉验证
    ...
```

#### 5.1.2 因子级验证

每个因子必须通过：

1. **手算对照**：构造 5~10 行已知数据，手算预期值，断言因子输出一致
2. **边界测试**：`HIGH==LOW`、`VOLUME==0`、数据不足等边界场景不崩溃
3. **方向验证**：正向因子大涨时因子值应增大，反向因子相反

```python
# tests/factors/alpha191/test_alpha_014.py
def test_alpha_014_basic():
    ctx = make_ctx(close=[10, 11, 12, 13, 14, 15])
    result = alpha_014(ctx)
    assert result.iloc[-1] == 5  # 15 - 10 = 5

def test_alpha_014_insufficient_data():
    ctx = make_ctx(close=[10, 11])  # 不足 5 期
    result = alpha_014(ctx)
    assert result.isna().all()
```

### 5.2 回测评估指标

每个因子策略回测后必须输出以下指标：

| 指标类别 | 具体指标 | 合格阈值 |
|----------|----------|----------|
| 收益 | 年化收益率 | > 0（正向）/ < 0（反向，做空） |
| 风险 | 最大回撤 | < 30% |
| 风险调整 | 夏普比率 | > 0.5 |
| 换手 | 日均换手率 | < 50%（短周期因子可放宽） |
| 信号 | 因子值覆盖率 | > 95%（非 NaN 比例） |
| 信号 | 因子值分布 | 无极端单值占比 > 10% |
| 稳定性 | IC 均值 | |IC| > 0.02 |
| 稳定性 | ICIR | > 0.3 |

### 5.3 上线前全面测试方案

```
┌─ 单元测试（每个因子）──────────────────────────────┐
│  手算对照 + 边界测试 + 方向验证                      │
└──────────────────────┬───────────────────────────┘
                       ▼
┌─ 集成测试（每批因子）──────────────────────────────┐
│  批量回测 + 信号分布检查 + 异常值检测                │
└──────────────────────┬───────────────────────────┘
                       ▼
┌─ 一致性测试（双引擎）──────────────────────────────┐
│  BarEngine vs EventEngine 结果一致性 > 80%          │
└──────────────────────┬───────────────────────────┘
                       ▼
┌─ 滚动验证（WalkForward）──────────────────────────┐
│  样本内 vs 样本外表现衰减 < 50%                     │
└──────────────────────┬───────────────────────────┘
                       ▼
┌─ 上线评审 ────────────────────────────────────────┐
│  因子文档 + 测试报告 + 回测报告 → 评审通过 → 注册   │
└───────────────────────────────────────────────────┘
```

**测试脚本位置**（遵循项目规则）：
- 单元测试：`tests/factors/alpha191/test_alpha_XXX.py`
- 集成测试：`tests/factors/test_batch_*.py`
- 独立验证脚本（如需）：`tests/` 目录下，问题修复后清除

---

## 六、文档编写要求

### 6.1 因子技术文档规范（强制要求）

**每个因子必须有完整备注**，这是不可跳过的硬约束。因子文件必须以完整的模块级 docstring 开头，并覆盖以下 10 个必填字段：

```python
"""
Alpha191 #14 — 5日收盘价动量
========================================

公式:
    CLOSE - DELAY(CLOSE, 5)

公式解释:
    计算当前收盘价与5日前收盘价的差值。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    最基础的5日动量因子，直接衡量过去5个交易日的价格变动幅度。
    正值表示上涨，负值表示下跌。正向意味着偏好近期上涨的股票（动量效应）。

适用场景:
    短期动量策略，偏好近期表现强势的股票。

变种与优化:
    - 可调整窗口期（5日→10日/20日）
    - 可使用对数收益率 log(CLOSE/DELAY(CLOSE,5)) 替代差值
    - 可加入成交量确认

注意事项:
    - 简单动量因子容易被均值回复策略反向利用，需结合其他因子使用
    - 前5期数据不足时返回 NaN，回测引擎自动跳过预热期
    - 需使用后复权价格以避免除权除息造成的虚假跳动
"""
```

**完整备注 10 个必填字段清单**（缺一不可，code review 时逐项检查）：

| 序号 | 字段 | 说明 |
|------|------|------|
| 1 | 标题行 | `Alpha来源 #编号 — 因子简称` |
| 2 | 公式 | 原文公式（与文档一致） |
| 3 | 公式解释 | 用自然语言描述计算过程 |
| 4 | 分类 | 8/11 大类之一 |
| 5 | 信号方向 | 正向(+1)/反向(-1) |
| 6 | 数据来源与频率 | OHLCV/VWAP/AMOUNT/基准等 + 日频 |
| 7 | 算子依赖 | 列出所有用到的算子 |
| 8 | 背后逻辑 | 因子设计思路与金融含义 |
| 9 | 适用场景 | 适用的策略类型 |
| 10 | 变种与优化 + 注意事项 | 可调参数、已知坑、边界处理 |

**强制检查**：开发流程 Step 7（文档与注册）中，若因子文件 docstring 缺少任一字段，视为未完成，不予合并。

### 6.2 因子目录索引（`docs/factor_catalog.md`）

| 编号 | 来源 | 公式 | 分类 | 方向 | 数据 | 算子 | 状态 |
|------|------|------|------|------|------|------|------|
| 14 | Alpha191 | `CLOSE-DELAY(CLOSE,5)` | 动量 | 正向 | CLOSE | delay | ✅ 已实现 |
| 4 | Alpha101 | `-1*Ts_Rank(rank(low),9)` | 价格排名 | 反向 | LOW | ts_rank, rank | ✅ 已实现 |
| ... | ... | ... | ... | ... | ... | ... | 📋 待开发 |

### 6.3 使用说明文档

- `docs/factor_usage_guide.md`：如何调用因子、如何封装为策略、如何回测
- 示例代码：`examples/run_alpha_014.py`

### 6.4 与现有因子体系的关联说明

| 关联模块 | 关联方式 |
|----------|----------|
| `quantlab/factors/`（本次新建） | 因子函数库，纯计算 |
| `quantlab/signals/`（本次补建） | 因子 → 策略封装层 |
| `quantlab/asset/`（已实现） | 因子注册为 AssetPackage |
| `quantlab/ml/feature/`（已实现） | 因子适配为 FeatureSet 供 ML 训练 |
| `quantlab/api/`（已实现） | 因子查询/计算 API |
| 文档描述的 `factors/ma` 等 | 本次实现的对齐文档描述的接口 |

---

## 七、关键决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 算子命名风格 | 小写下划线（`ts_rank`） | 与 STRATEGY_DEV_GUIDE 因子函数规范一致 |
| 因子函数签名 | `def alpha_XXX(ctx: FactorContext) -> pd.DataFrame` | 统一接口，ctx 封装数据避免长参数 |
| 因子方向处理 | 公式内不取负，`direction` 字段标注 | 保持公式与文档一致，方向可配置 |
| 算子输入输出 | 统一 `pd.DataFrame`（date × symbol） | 向量化友好，与回测引擎兼容 |
| 开发顺序 | P0→P1→P2→P3 按算子复杂度递增 | 先简后繁，尽早打通链路 |
| 基础设施 | Phase 0 先补建最小引擎 | 回测验证依赖引擎，不可跳过 |
| 行业中性化因子 | 放 P3 最后 | 依赖行业分类数据，数据准备成本高 |
| 测试位置 | `tests/factors/` 下按来源分子目录 | 遵循项目规则，问题修复后清除临时脚本 |

---

## 八、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 基础设施缺失导致无法回测 | 高 | Phase 0 优先补建最小引擎，不假设框架已就绪 |
| VWAP 日频近似精度不足 | 中 | 文档标注近似方式，关键因子预留分时数据接口 |
| 行业分类数据缺失 | 中 | P3 因子延后，先完成无行业依赖的 271 个因子 |
| 292 因子工作量大 | 高 | 分批交付，每批独立可验收，P0 优先打通链路 |
| 算子实现与文档公式有偏差 | 高 | 每个算子手算对照测试，因子级方向验证 |
| 因子过拟合 | 中 | WalkForward 滚动验证，样本内外衰减检查 |

---

## 九、验收清单（Checklist）

### Phase 0 验收
- [x] `quantlab/__init__.py` 存在
- [x] `FactorContext` 可加载 OHLCV 数据
- [x] `SignalStrategy` 基类可继承
- [x] `BarEngine` 可跑通单次回测
- [x] `Alpha014Strategy` 回测输出 Report

> Phase 0 已于 2026-06-25 完成。58 项单元测试全部通过，端到端回测跑通
> （合成趋势数据：总收益 29.06%，夏普 63.77，最大回撤 -0.49%）。
> 交付物：`factors/context.py`、`signals/base.py`、`engine/bar.py`、
> `portfolio_construction/base.py`(EqualWeight/TopN)、`research/experiment.py`、
> `factors/operators/{ts,cross_section,stats,smooth}.py`、
> `factors/alpha191/alpha_014.py`(含完整 10 字段备注)、`signals/alpha_014.py`。

### Phase 1 验收
- [x] 22 个算子全部实现
- [x] 算子单元测试覆盖率 100%
- [x] 算子与 numpy/pandas 原生函数交叉验证通过

> Phase 1 已于 2026-06-25 完成。算子库共 25 个算子，36 项单元测试全部通过。
> 交付物：`factors/operators/{ts,cross_section,stats,smooth,regression,misc}.py`
> 新增算子：`regbeta`(回归斜率)、`signed_power`(带符号幂)、`sum_if`(条件求和)、
> `cumsum`(累积和)、`highday/lowday`(极值距今天数)、`sequence`(序列生成)。
> 现有算子合计：时序11 + 截面3 + 统计2 + 平滑3 + 回归1 + 工具6 = 26 个（覆盖计划要求的 22 个核心算子及 4 个辅助算子）。

### Phase 2 验收
- [ ] 60 个 P0 因子全部实现
- [ ] 每个因子有手算对照单元测试
- [ ] 批量回测脚本可运行
- [ ] 因子目录索引更新

### Phase 3-4 验收
- [ ] 232 个因子全部实现
- [ ] 全部通过单元测试
- [ ] IC/ICIR 指标达标
- [ ] WalkForward 验证通过

### Phase 5 验收
- [ ] 因子目录索引完整
- [ ] 因子注册到 AssetRegistry
- [ ] API 端点可用
- [ ] 前端 FactorStudio 可展示

---

> **附注**：本计划基于 2026-06-25 项目实际代码状态制定。核心发现是 README/STRATEGY_DEV_GUIDE 描述的 `signals/factors/engine` 等模块当前缺失，Phase 0 已将其纳入补建范围。计划执行过程中如发现基础设施已有其他实现路径，应及时调整 Phase 0 范围。
