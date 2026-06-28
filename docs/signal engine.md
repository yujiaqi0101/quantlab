所以，我们重新回到 ML Lab。

我建议整个 ML Lab 的架构重新整理成下面这样（个人版）。

ML Lab
│
├── Dataset Manager
│
├── Universe Manager
│
├── Feature Engineering
│
├── Label Engineering
│
├── Feature Selection
│
├── Data Split
│
├── Model Zoo
│
├── Training Engine
│
├── Hyperparameter Search
│
├── Validation Engine
│
├── Model Registry
│
├── Signal Engine   ← 今天讨论
│
├── Strategy Builder
│
└── Experiment Tracker

注意：

Signal Engine 是 ML Lab 的最后一层。

也就是说：

整个 ML Lab 的最终产物不是 Model。

而是：

Signal

不是：

Feature

↓

Model

而是：

Feature

↓

Model

↓

Signal

这是 ML Lab 的终点。

我建议重新定义 Signal Engine

我建议 Signal Engine 不要理解成：

Prediction

↓

Buy

而应该理解成：

Prediction Interpretation Layer（预测解释层）

什么意思？

模型：

输出：

未来5天收益

+3.4%

对于策略来说：

没有意义。

真正策略需要的是：

可以买

可以买多少

什么时候卖

多久持仓

风险等级

所以：

Signal Engine：

就是负责：

把 Model Prediction 转换成 Strategy Language。

这是整个职责。

Signal Engine 在 ML Lab 的位置

完整流程建议如下：

Dataset
        │
        ▼
Feature Pipeline
        │
        ▼
Feature Selection
        │
        ▼
Training
        │
        ▼
Validation
        │
        ▼
Best Model
        │
        ▼
Prediction
        │
        ▼
Signal Engine
        │
        ▼
Signal
        │
        ▼
Strategy Builder

所以：

Signal Engine：

属于：

ML。

不是：

Strategy。

Signal Engine 的职责

我建议定义成：

Prediction

↓

Calibration

↓

Signal Generation

↓

Filtering

↓

Ranking

↓

Scoring

↓

Risk Adjustment

↓

Position Suggestion

↓

Signal Output

注意：

Signal Engine：

不下单。

我建议 Signal Engine 里面拆成九个模块
signal_engine/

├── prediction_adapter.py
├── calibrator.py
├── generator.py
├── scorer.py
├── filter.py
├── ranker.py
├── position_allocator.py
├── signal_registry.py
└── signal_validator.py

下面一个一个定义。

一、Prediction Adapter

作用：

统一所有模型输出。

因为：

不同模型：

输出完全不同。

例如：

LightGBM：

0.023

XGBoost：

0.015

分类模型：

Bull

Bear

Transformer：

Sequence

RL：

Action

Prediction Adapter：

全部转换成：

统一 Prediction。

例如：

Prediction

symbol

datetime

value

probability

metadata

以后：

Signal Engine：

只认识 Prediction。

二、Prediction Calibrator

很多模型：

输出：

其实不能直接交易。

例如：

分类模型：

0.55

是不是可以买？

不知道。

所以：

Calibration：

例如：

Temperature Scaling

Platt Scaling

Isotonic Regression

Probability Calibration

以后：

Confidence：

更可靠。

三、Signal Generator（核心）

这一层：

真正：

把 Prediction：

变成：

Signal。

例如：

Prediction：

Return=4%

Generator：

规则：

Return>2%

↓

Long

输出：

Long

Generator：

支持：

Threshold

Quantile

Ranking

Probability

Regression

Classification

Custom

全部插件化。

四、Signal Filter

模型：

每天：

可能：

预测：

5000只股票。

但是：

不是：

全部交易。

Filter：

负责：

例如：

流动性

停牌

涨跌停

上市时间

成交额

黑名单

过滤。

五、Signal Ranker

很多模型：

都会输出：

大量：

Signal。

例如：

3000只股票

Long

怎么办？

Rank。

例如：

Top50

Top100

Bottom50

这一层：

专门：

负责排序。

六、Signal Scorer

这里：

很多平台：

没有。

我建议：

增加：

统一：

Score。

例如：

[-100,100]

或者：

[-1,1]

以后：

所有策略：

统一。

例如：

0.91

非常强
七、Position Allocator

这里：

注意。

不是：

Portfolio。

这里只是：

建议。

例如：

Confidence

0.92

建议：

Weight

5%

或者：

Kelly

Volatility Scaling

Risk Parity

Equal Weight

这里只输出：

Suggested Position。

真正 Portfolio：

以后：

再约束。

八、Signal Registry

我建议：

Signal：

不要：

即时生成：

然后丢掉。

而是：

全部保存。

例如：

Signal

↓

Registry

保存：

Signal Version

Generator

Threshold

Model Version

Dataset

Validation

以后：

Observe：

直接：

看。

九、Signal Validator

这一层：

不是：

验证模型。

而是：

验证 Signal。

例如：

指标：

Hit Rate

Precision

Recall

Average Return

Turnover

Holding Days

IC

Rank IC

Win Rate

Signal：

先：

验证。

再：

Strategy。

Signal 对象（统一定义）

整个系统：

我建议：

Signal：

统一。

class Signal:

    signal_id

    symbol

    datetime

    direction

    score

    confidence

    expected_return

    suggested_weight

    holding_period

    source_model

    generator

    metadata

以后：

整个 QuantLab：

统一。

Signal Engine 最终输出

我建议：

Signal Engine：

最终：

只输出：

一个对象：

SignalSet

例如：

SignalSet

├── BTC

├── ETH

├── SOL

├── AAPL

└── TSLA

Strategy Builder：

以后：

直接：

读取。

我认为还应该增加两个模块（这是我建议加入 ML Lab，而不是 Research Graph）
① Signal Templates

也就是说：

ML Lab：

内置：

TopK

Long Short

Probability

Mean Reversion

Momentum

Breakout

Triple Barrier

Meta Labeling

用户：

不用：

自己：

写。

直接：

配置。

② Signal Explainability

点击：

Signal。

直接：

看到：

Prediction

↓

Threshold

↓

Filter

↓

Ranking

↓

Score

↓

Suggested Weight

这对于以后调试 ML 模型极其重要。

我建议的最终版 Signal Engine（ML Lab V1）
ML Lab
│
├── Dataset Manager
├── Universe Manager
├── Feature Engineering
├── Label Engineering
├── Feature Selection
├── Model Zoo
├── Training Engine
├── Hyperparameter Search
├── Validation Engine
├── Model Registry
│
├─────────────────────────────────────
│
├── Signal Engine
│     │
│     ├── Prediction Adapter
│     ├── Prediction Calibrator
│     ├── Signal Generator
│     ├── Signal Filter
│     ├── Signal Ranker
│     ├── Signal Scorer
│     ├── Position Allocator
│     ├── Signal Validator
│     ├── Signal Registry
│     ├── Signal Templates
│     └── Signal Explainability
│
├─────────────────────────────────────
│
├── Strategy Builder
└── Experiment Tracker
最后，我再给一个建议（我认为这是 ML Lab V1 最合理的边界）

为了保持架构清晰，我建议 Signal Engine 到 Suggested Position 为止。

也就是说：

Prediction
    │
    ▼
Signal
    │
    ▼
Suggested Position

到这里结束。

不要把以下内容放进 ML Lab：

Portfolio Optimization（组合优化）
Risk Engine（风险控制）
Execution（执行）
Broker（券商接口）

这些应该属于交易系统（Trading Core）。

这样 ML Lab 的职责非常明确：

ML Lab 的任务不是交易，而是生成经过验证、可解释、可版本管理的高质量交易信号。

我认为这是个人版 QuantLab 最清晰、最容易扩展的 Signal Engine 定义。