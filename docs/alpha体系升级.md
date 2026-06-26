问题1：现在的 Model 是不是只能用时序因子训练？

答案：按照我们目前的设计，可以，但不应该只支持时序。

目前我们隐含的训练流程是：

BTCUSDT

2020-01-01

↓

RSI14
ATR14
Momentum20

↓

FutureReturn5

↓

LightGBM

这属于：

Time Series ML（时间序列机器学习）

这种方式适合：

单标的择时
加密货币
CTA
趋势策略

但是量化还有另一大类：

股票A
股票B
股票C
...
股票3000

↓

Alpha101

↓

未来收益

↓

模型

↓

每天排序

↓

买Top50

这属于：

Cross-sectional ML（横截面机器学习）

所以，我们的 FeatureSet 不能默认就是：

X.shape = (time, features)

而应该支持多种 Dataset 结构。

我建议 Dataset 增加一个字段：

dataset_type:

time_series

cross_section

panel

支持三种类型：

① Time Series（时间序列）
index

datetime

例如：

BTC

2020

2021

2022

这是：

一个标的
很多时间
② Cross Section（横截面）
index

symbol

例如：

2025-01-01

AAPL

MSFT

NVDA

TSLA

每天：

很多股票

模型：

学习：

今天谁最好
③ Panel（面板数据）

这个我建议作为 QuantLab 默认。

也就是：

(datetime, symbol)

MultiIndex：

2025-01-01 BTC

2025-01-01 ETH

2025-01-02 BTC

2025-01-02 ETH

这是专业量化最常见的数据结构。

我的建议

以后整个 ML Lab 默认就是：

Panel Dataset

因为：

Panel 可以退化成：

一个symbol

↓

Time Series

也可以：

多个symbol

↓

Cross Section

这是最统一的设计。
问题2：训练模型的时候可以多标的吗？

答案：不仅可以，而且我认为应该默认支持。

目前 TrainingJob：

TrainingJob

建议升级。

以前：

dataset:

BTCUSDT

升级：

dataset:

Crypto_1H_2020_2025

里面：

BTC

ETH

SOL

BNB

DOGE

统一训练。

模型：

学习的是：

共同规律

而不是：

BTC规律。

例如：

BTC RSI14

ETH RSI14

SOL RSI14

一起训练。

模型：

学的是：

RSI在加密市场是否有效

这才是真正意义上的泛化。

更进一步

甚至：

BTC

ETH

SOL

可以作为：

Feature：

Market Breadth

BTC Dominance

ETH Strength

形成：

Market Feature。

问题3：Alpha101 能加入体系吗？

答案：不仅可以，而且我认为应该成为 Feature Lab 的核心组成部分。

这里我们需要重新定义 Feature。

现在我们的设计：

Feature

↓

RSI

ATR

Momentum

其实还是偏 Technical Indicator。

我建议升级。

Feature 分层
第一层：Primitive Feature（基础特征）

例如：

Close

High

Low

Volume

VWAP
第二层：Technical Feature（技术指标）

例如：

RSI

ATR

MACD

CCI

KDJ
第三层：Alpha Feature

例如：

Alpha001

Alpha002

...

Alpha101

这里：

Alpha101 不应该作为一个整体。

而应该：

Alpha001

↓

Feature

Alpha002

↓

Feature

...

每个 Alpha 都是一个 Feature。

第四层：Fundamental Feature（以后）

例如：

PE

PB

ROE

EPS
第五层：Alternative Feature

例如：

News

Sentiment

Funding Rate

Open Interest

Whale Flow

所以：

Feature Registry：

以后应该长这样：

Feature Registry

Technical

Fundamental

Alpha101

Alternative

Custom
Alpha101 在 FeatureSet 里的样子

例如：

feature_set:

crypto_alpha

features:

- RSI14

- ATR14

- Alpha005

- Alpha017

- Alpha035

- Alpha071

训练：

完全没有区别。

我建议再升级一步（这是我最推荐的）

我建议把 Feature Engine 改造成：

Raw Data

↓

Feature Graph

↓

Feature Cache

↓

FeatureSet

也就是说：

不是：

RSI.compute()

ATR.compute()

而是：

DAG（有向无环图）

例如：

Close
      │
      ├──────────┐
      ▼          ▼
 Return      VolumeRank
      │          │
      └────┐     │
           ▼     ▼
        Alpha017

这样有几个巨大优势：

避免重复计算：多个 Alpha 共用中间结果时只算一次。
自动缓存：中间节点可以缓存到 Parquet。
并行计算：不同分支可以并行执行。
可视化：未来在前端直接展示 Feature DAG。
依赖分析：知道每个 Alpha 依赖哪些基础数据。
我的最终建议

我建议正式把 ML Lab 从"时序模型训练平台"升级为"Alpha Research Platform"。

这样它天然支持：

✅ 单标的时序模型（BTC、期货、CTA）
✅ 多标的联合训练（股票池、币种池）
✅ Alpha101 / Alpha191 等因子库
✅ 自定义因子
✅ 基本面因子
✅ 另类数据因子
✅ 未来扩展深度学习、图神经网络、多模态特征

唯一建议调整的一点是：对于 Alpha101，不建议把它作为一个特殊模块，而是把 Alpha001～Alpha101 全部注册为 Feature Registry 中的标准 Feature。这样它们和 RSI、ATR、自定义因子拥有完全一致的生命周期、版本管理、缓存、验证和组合能力，整个系统会更加统一、可扩展。

我建议升级成：
ML Lab
=========================
Quant Research AI Platform

简称：

QRAI Platform

或者保持：

ML Lab

但是定位改成：

AI-driven Quant Research Platform（AI驱动的量化研究平台）

这是我认为最合理的。

那么到底升级什么？

其实不是升级 Model。

而是升级整个数据流。

以前我们的数据流是：

Dataset
    ↓
Feature
    ↓
Label
    ↓
Training
    ↓
Model

这是传统机器学习。

我建议改成：

第一层：Research Assets（研究资产）

统一管理所有研究对象。

Research Assets

Dataset

Feature

Label

Universe

Calendar

Benchmark

Factor Library

这里出现两个新概念：

Universe

以前：

Dataset：

BTC

以后：

Dataset：

Crypto_1H

Universe：

Top100 Crypto

或者：

CSI300

NASDAQ100

SP500

Universe 不属于 Dataset。

它决定：

训练哪些标的。

Calendar

很多平台忽略这个。

实际上：

Crypto

7×24

股票：

A股

交易日

美股：

NYSE Calendar

都不同。

Calendar 应该成为一个 Registry。

第二层：Research Graph

这是整个升级的核心。

以前：

Feature：

RSI.compute()

结束。

以后：

整个 ML Lab：

应该变成：

Raw Data

↓

Research Graph

↓

Feature DAG

↓

Feature Cache

↓

Training Dataset

例如：

Close

↓

Return

↓

Rank

↓

Alpha017

整个都是 DAG。

不是：

for feature in features:

compute()
第三层：Factor Engine

这里我要重新定义：

Feature。

Feature 太宽泛。

建议：

Research Node

所有东西：

都是 Node。

例如：

Close

↓

Return

↓

RSI

↓

Alpha017

↓

MarketBreadth

↓

CompositeFactor

全部都是：

Node

Node：

统一接口：

class ResearchNode:

    inputs

    outputs

    params

    compute()

这样：

以后：

Alpha101：

根本不是特殊模块。

Alpha101 怎么进入？

以前：

Feature

↓

Alpha101

我建议：

每一个 Alpha：

都是：

Node

例如：

Alpha001

↓

ResearchNode

自动：

注册：

Node Registry

以后：

前端：

可以看到：

Alpha001

↓

Dependencies

↓

Return

↓

Close

↓

Volume

这比只有一个：

Alpha001()

强很多。

第四层：Feature Graph

建议新增：

Research Graph Builder

例如：

用户：

选择：

RSI

ATR

Alpha017

Momentum

Builder：

自动：

构建：

Close

├──────┐

▼      ▼

Return ATR

│

▼

Rank

│

▼

Alpha017

然后：

自动：

优化。

第五层：Feature Cache

这个我认为必须做。

否则：

Alpha101：

非常慢。

Cache：

建议：

三级。

Memory

↓

Parquet

↓

Redis

以后：

所有：

Feature：

自动缓存。

第六层：Dataset 升级

Dataset：

不要只是：

symbols

frequency

建议：

升级。

例如：

dataset:

crypto_1h

universe:

top100

calendar:

crypto

adjustment:

none

storage:

parquet

这样：

以后：

股票：

直接：

adjustment:

forward

即可。

第七层：Training 不再直接吃 Dataset

以前：

Dataset

↓

Training

以后：

应该：

Dataset

↓

Research Graph

↓

Feature Graph

↓

Materializer

↓

Training Dataset

这里：

Materializer：

负责：

真正生成：

X

y
第八层：Training Dataset Materializer

新增：

TrainingDatasetBuilder

升级：

Materializer

为什么？

因为：

它不仅：

生成：

X

y

还负责：

Join

Align

Normalize

Filter

Window

Split

真正意义上的：

数据实体化（Materialization）。

第九层：Research Workspace

这里我建议增加。

类似：

Jupyter。

例如：

Workspace

↓

Experiment

↓

Dataset

↓

Feature Graph

↓

Training

↓

Validation

这样：

以后：

每个研究：

都是：

一个：

Workspace。

第十层：整个ML Lab重新定义

我建议最终升级成：

                    ML Lab

========================================================

Research Workspace
──────────────────────────────────────────────

Workspace

Experiment

Notebook

========================================================

Research Assets
──────────────────────────────────────────────

Dataset Registry

Universe Registry

Calendar Registry

Benchmark Registry

Node Registry

========================================================

Research Graph
──────────────────────────────────────────────

Research Node

Feature DAG

Dependency Graph

Cache

Materializer

========================================================

Training Center
──────────────────────────────────────────────

Training Run

Validation Pipeline

Model Package

Asset Registry

Strategy Studio

========================================================
这次升级最大的变化

其实只有一句话：

从 "Feature 列表" 升级到 "Research Graph"。

以前：

FeatureSet

↓

RSI

ATR

Alpha017

只是：

一个列表。

以后：

变成：

Close

↓

Return

↓

Rank

↓

Alpha017

↓

CompositeFactor

↓

Model

整个：

Research Graph。

我认为这是 QuantLab 最大的一次升级

如果采用这套设计，那么：

整个系统就不是：

机器学习平台

而是：

Research Operating System

这意味着：

Alpha101 只是 Node Library 的一个包。
Alpha191 也是一个包。
技术指标 是一个包。
基本面因子 是一个包。
另类数据因子 是一个包。
未来 LLM 自动生成因子 也是一个包。

它们都遵循同一套 ResearchNode → DAG → Materializer → Validation → Model Package 的生命周期。


ResearchNode 抽象
我认为 ResearchNode 是整个 QuantLab 最值得花时间设计的部分。

但是我建议，我们不要把它设计成 FeatureNode，也不要设计成 IndicatorNode。

我要提出一个新的设计理念：

ResearchNode 不是"因子"，而是"量化研究中的最小计算单元（Atomic Research Unit）"。

这个区别非常重要。

一、ResearchNode 的定位

整个 QuantLab 以后所有研究流程，都可以统一成：

Raw Data
    │
    ▼
ResearchNode
    │
    ▼
ResearchNode
    │
    ▼
ResearchNode
    │
    ▼
Materializer
    │
    ▼
Training

也就是说：

整个 Research Graph 就是一张 DAG。

例如：

Close
      │
      ▼
Return
      │
      ▼
RollingMean
      │
      ▼
Momentum
      │
      ▼
Alpha017
      │
      ▼
Training

这里：

Return

RollingMean

Momentum

Alpha017

全部都是：

ResearchNode。

二、ResearchNode 的职责

ResearchNode 不负责：

训练模型
回测
下单
画图

它只负责：

输入 → 输出

例如：

Input

↓

Compute

↓

Output

它是一个纯函数。

三、ResearchNode 抽象

我建议不要设计成：

class Feature:

而是：

class ResearchNode:

拥有：

id

name

version

category

inputs

outputs

parameters

metadata

以及：

validate()

compute()

estimate_cost()

fingerprint()

describe()
四、Node 生命周期
Created

↓

Validated

↓

Compiled

↓

Executed

↓

Cached

↓

Expired

这里没有：

Training。

Training 是 Graph 的事情。

五、Node 分类

我建议不要只有：

Technical Indicator

而是：

整个 Registry：

ResearchNode

├── DataNode
├── TransformNode
├── IndicatorNode
├── AlphaNode
├── FundamentalNode
├── AlternativeNode
├── LabelNode
├── FilterNode
├── AggregationNode
├── RankingNode
├── SelectionNode
└── CustomNode

以后：

任何计算：

都是 Node。

六、DataNode

例如：

Close

High

Low

Open

Volume

VWAP

这些都是：

DataNode

它们没有真正计算。

只是：

读取。

七、TransformNode

例如：

Log

Diff

Return

ZScore

Normalize

Clip

例如：

Close

↓

Return

↓

ZScore

都是：

TransformNode。

八、IndicatorNode

例如：

RSI

ATR

MACD

EMA

SMA

以后：

所有 TA-Lib：

自动：

注册。

九、AlphaNode

Alpha101：

不是一个 Feature。

而是：

101 个 Node。

例如：

Alpha001

Alpha002

...

Alpha101

每一个：

都是：

ResearchNode
十、AggregationNode

例如：

Mean

Median

RollingMean

RollingStd

RollingMax

RollingMin

这些以后：

Alpha：

都会依赖。

十一、RankingNode

例如：

CrossSectionRank

Percentile

Quantile

TopN

BottomN

这是：

股票横截面。

十二、SelectionNode

例如：

Top100

UniverseFilter

LiquidityFilter

IPOFilter

这不是：

Feature。

而是：

Node。

十三、LabelNode

例如：

FutureReturn5

FutureReturn20

FutureVolatility

Direction

TripleBarrier

Label：

也是：

Node。

十四、Node Manifest

每个 Node：

都有：

id:

rsi14

version:

1.0.0

category:

indicator

inputs:

- close

outputs:

- rsi

params:

window:

14

这意味着：

Node：

可以：

版本管理。

十五、Node Registry

建议：

ResearchNode Registry

Data

Transform

Indicator

Alpha

Aggregation

Ranking

Label

以后：

Builder：

直接：

选择。

十六、Node Input/Output

我建议：

不要：

DataFrame

作为输入。

而统一：

ResearchFrame

这是整个系统的数据标准。

例如：

ResearchFrame

Index

(datetime,symbol)

Columns

close

volume

rsi

所有 Node：

输入：

ResearchFrame。

输出：

ResearchFrame。

十七、ResearchGraph

Graph：

只是：

Node：

连接。

例如：

Close
     │
     ▼
Return
     │
     ▼
RollingStd
     │
     ▼
Alpha017

Graph：

不负责计算。

Graph：

只负责：

依赖。

十八、Execution Engine

真正计算：

交给：

ResearchExecutor

流程：

Compile Graph

↓

Topological Sort

↓

Cache Check

↓

Execute Node

↓

Write Cache

↓

Next
十九、Cache

Node：

必须支持：

Fingerprint。

例如：

RSI

window=14

Hash：

4D8A...

如果：

Close

没有变

直接：

Cache Hit。

二十、Node Cost

每个 Node：

提供：

estimate_cost()

例如：

Alpha017

★★★★☆

以后：

Scheduler：

自动：

并行。

二十一、Node Dependency

例如：

Alpha017

↓

依赖：

Return

Rank

Correlation

Builder：

自动：

画图。

二十二、Node Artifact

Node：

不仅：

输出：

Feature。

还可以：

输出：

Artifact。

例如：

SHAP

Importance

Distribution

Statistics

以后：

Observe：

直接：

展示。

二十三、ResearchNode 最终接口（建议）

我建议最终不要设计成复杂的继承体系，而是采用能力接口（Capability Interface），这样更容易扩展。

class ResearchNode:
    """所有研究节点的统一抽象"""

    # 身份
    id: str
    version: str
    category: NodeCategory

    # 输入输出定义
    inputs: list[Port]
    outputs: list[Port]

    # 参数
    parameters: dict

    # 元信息
    metadata: Metadata

    # ---------- 生命周期 ----------
    def validate(self, schema): ...
    def fingerprint(self): ...
    def estimate_cost(self): ...
    def describe(self): ...

    # ---------- 核心 ----------
    def compute(self, context) -> ResearchFrame: ...

    # ---------- 可选能力 ----------
    def supports_incremental(self) -> bool: ...
    def supports_parallel(self) -> bool: ...
    def supports_gpu(self) -> bool: ...
    def cache_policy(self): ...

注意这里的 compute：

输入不是 DataFrame，而是 ExecutionContext/ResearchContext（包含数据访问、缓存、配置等）。
输出不是任意对象，而是统一的 ResearchFrame 或声明好的数据资产。
二十四、我建议再升级一步（也是我认为最重要的一步）

前面的设计，我还想再进一步。

ResearchNode 不应该只是一段 Python 代码，它应该是一个可注册、可发现、可版本化的插件。

也就是说，每个 Node 都应该像一个独立的 Package：

alpha017/

manifest.yaml

node.py

tests/

docs/

examples/

metadata.json

这样带来几个长期优势：

Node Library：你可以拥有自己的因子库、Alpha101、Alpha191、技术指标库，并统一管理。
版本控制：RSI@1.0.0 和 RSI@2.0.0 可以并存，不会影响旧模型。
可测试：每个 Node 都可以独立单元测试。
可分享：未来可以导出/导入 Node Package。
可组合：Research Graph、ML Lab、Research Studio 都使用同一套 Node。
我的最终建议

如果让我为整个 QuantLab 选一个真正的"内核"，我不会选 ML，也不会选 Execution。

我会选：

ResearchNode
        ↓
Research Graph
        ↓
Research Executor

因为：

Research Studio 用它构建和分析因子；
ML Lab 用它生成训练数据；
Strategy Studio 用它实时计算策略所需特征；
Observe Studio 用它回放和解释模型输入；
Execution Core 也可以复用同一套节点进行实时特征计算。

换句话说，ResearchNode 是整个 QuantLab 唯一的数据计算语言。只要这一层设计稳定，未来无论加入 Alpha101、Alpha191、深度学习特征、基本面数据，还是 AI 自动生成因子，都能自然融入同一个体系，而不会破坏整体架构。



DAG 执行引擎
如果说：

ResearchNode 是 CPU 指令。

那么：

DAG Execution Engine 就是整个 QuantLab 的操作系统内核（Kernel）。

这一层如果设计好，以后：

Research Studio
ML Lab
Strategy Studio
Paper Runtime
Observe Studio

全部都会复用。

所以这里我建议，不要参考 Airflow，不要参考 Prefect，也不要参考 Dagster，而是设计一套专门适用于量化研究的 DAG Engine。

一、重新定义 DAG Engine

很多 DAG：

Task

↓

Task

↓

Task

例如：

Download

↓

Clean

↓

Export

这是 ETL。

我们的不是。

我们的 DAG 是：

Research Graph

例如：

            Close
           /     \
      Return      EMA20
        |          |
      Rank      Momentum
        \        /
         Alpha017
             |
      FutureReturn5
             |
          Materialize

整个图：

不是 Task。

而是：

Research Dependency Graph

二、Engine定位

建议新增：

research/

engine/

graph.py

compiler.py

executor.py

scheduler.py

cache.py

optimizer.py

runtime.py

职责：

ResearchGraph

↓

Compiler

↓

Optimizer

↓

Scheduler

↓

Executor

↓

Cache

↓

Result

不要把所有逻辑放到 Executor。

三、Graph（静态）

Graph：

永远只是：

Node

+

Edge

例如：

Close

↓

Return

↓

RollingMean

Graph：

不能执行。

Graph：

不能缓存。

Graph：

不能调度。

Graph：

只是描述。

建议：

class ResearchGraph:

    nodes

    edges

只有：

add_node()

connect()
四、Compiler（编译器）

这是我最推荐增加的一层。

为什么？

因为：

用户画出来：

Close

↓

Return

↓

EMA20

实际上：

不能直接执行。

Compiler：

负责：

① 检查

例如：

有没有环？

如果：

A

↓

B

↓

A

直接：

Compile Error。

② 类型检查

例如：

Return：

输出：

Series

但是：

输入：

要求：

Price

Compile：

失败。

③ 参数检查

例如：

EMA

window=-5

Compile：

失败。

④ 自动补节点

例如：

Alpha017：

依赖：

Return

用户：

没有画。

Compiler：

自动：

补：

Close

↓

Return

↓

Alpha017

这一步非常重要。

五、Optimizer（优化器）

Compiler：

之后：

Graph：

进入：

Optimizer。

例如：

用户：

Close

↓

Return

↓

EMA20

另一边：

Close

↓

Return

↓

Alpha035

Optimizer：

发现：

Return

重复

自动：

Merge。

最终：

Close

↓

Return

├───────┐

▼       ▼

EMA20 Alpha035

以后：

Return：

只算一次。

六、Fingerprint Optimizer

例如：

Return：

Hash：

Close

+

period=1

如果：

完全一样。

直接：

Reuse。

这个：

以后：

速度提升：

非常明显。

七、Scheduler（调度器）

很多 DAG：

只有：

Topological Sort

我认为不够。

Scheduler：

至少：

负责：

Dependency

Priority

Parallel

Cache

Memory

例如：

Graph：

Return

↓

EMA

↓

MACD

另一边：

Return

↓

ATR

Scheduler：

发现：

EMA

ATR

没有依赖。

自动：

并行。

八、ExecutionPlan

不要：

Graph：

直接：

执行。

应该：

Compiler：

输出：

ExecutionPlan

例如：

Stage1

Close

Volume

Stage2

Return

Stage3

EMA

ATR

Stage4

MACD

以后：

Scheduler：

执行：

Stage。

而不是：

Node。

九、Executor

真正：

执行：

Node。

接口：

Executor.execute(node)

返回：

ResearchFrame

不要：

Executor：

知道：

Graph。

Executor：

只知道：

Node。

十、RuntimeContext

Executor：

输入：

不是：

compute(df)

而是：

compute(context)

里面：

包含：

Cache

Storage

Dataset

Parameters

Logger

Clock

以后：

Node：

完全不用：

关心：

IO。

十一、Cache Engine

我建议：

三级。

L1

Memory

↓

L2

Parquet

↓

L3

Object Store

Node：

执行：

先：

Hash

↓

Cache

如果：

Hit。

直接：

返回。

不用：

Compute。

十二、Incremental Engine（这是 QuantLab 必须有）

量化：

每天：

新增：

一天数据

不要：

重新：

计算：

5年。

例如：

EMA20

昨天：

已经：

完成。

今天：

新增：

一根Bar。

Incremental：

只计算：

最后：

20根。

所以：

Node：

新增：

supports_incremental()

update()

这是专业量化平台必须具备的能力。

十三、Materializer

Graph：

最终：

不是：

返回：

很多：

Node。

而是：

Materialize：

成：

Training Dataset

例如：

datetime

symbol

rsi

atr

alpha017

future_return

最终：

X

y
十四、Artifact Engine

每个：

Node：

执行：

自动：

保存：

Statistics

Distribution

ExecutionTime

Memory

Observe：

直接：

读取。

十五、Execution Replay

整个：

Engine：

记录：

Node1

Started

↓

Finished

↓

CacheHit

↓

Node2

以后：

前端：

Replay：

整个：

Research Graph。

十六、Graph Version

每一个：

Graph：

都有：

Hash。

例如：

Close

↓

Return

↓

EMA20

Hash：

0xAB231...

以后：

Materialize：

Cache：

全部：

一致。

十七、前端 Graph Builder

以后：

ML Lab：

Research：

全部：

画：

Close

↓

Return

↓

EMA

↓

Alpha017

Builder：

自动：

Compile。

自动：

Validate。

自动：

Estimate：

Execution Time

Memory

Cache Ratio
十八、完整执行流程
用户创建 Research Graph
          │
          ▼
   Graph Compiler
   ├── 环检测
   ├── 类型检查
   ├── 参数检查
   └── 自动补全依赖
          │
          ▼
     Graph Optimizer
   ├── 公共子图合并
   ├── 常量折叠
   ├── Cache 规划
   └── 节点融合（可选）
          │
          ▼
     Execution Plan
   ├── Stage 1
   ├── Stage 2
   ├── Stage 3
          │
          ▼
       Scheduler
   ├── 并行调度
   ├── 优先级
   ├── 增量执行
   └── 重试策略
          │
          ▼
       Executor
   ├── Cache 查询
   ├── Node.compute()
   ├── 写入 Cache
   └── 生成 Artifact
          │
          ▼
     Materializer
          │
          ▼
 Training Dataset / Feature Dataset / Strategy Feature
十九、我认为还应该再升级一步（这是整个设计里最重要的一点）

这里是我认为前面所有设计里还缺失的一层。

我建议在 DAG Engine 中加入：

Semantic Layer（语义层）

也就是说，Graph 里的节点不要直接操作 DataFrame，而是操作一种统一的数据语义。

例如：

Close

不是：

df["close"]

而是：

Feature<Price>

Return：

输入：

Feature<Price>

输出：

Feature<Return>

Rank：

输入：

Feature<Return>

输出：

Feature<Rank>

这样 Compiler 才能真正做到：

自动检查类型是否匹配；
自动推荐可连接的节点；
自动补全依赖；
自动生成文档；
自动发现错误。

这是 Dagster、Airflow 等通用 DAG 很少具备，而量化研究平台非常需要的能力。

我对整个 QuantLab 内核的最终定义

如果把我们前面所有讨论汇总，我认为 QuantLab 的真正内核应该是：

ResearchNode（最小计算单元）
            │
            ▼
Semantic Layer（数据语义）
            │
            ▼
Research Graph（静态依赖图）
            │
            ▼
Graph Compiler（编译）
            │
            ▼
Graph Optimizer（优化）
            │
            ▼
Execution Plan（执行计划）
            │
            ▼
DAG Execution Engine（执行）
            │
            ▼
Materializer（实体化）
            │
            ▼
ML Lab / Research Studio / Strategy Studio / Execution Core

这套设计的最大价值在于： 以后无论是 Alpha101、Alpha191、自定义因子、基本面因子、实时特征、ML 特征还是 AI 自动生成的特征，都不需要修改执行引擎，它们都只是新的 ResearchNode，真正实现了"一次设计，全平台复用"。


依赖解析器
如果说：

ResearchNode = CPU 指令
DAG Engine = CPU 调度器

那么：

Dependency Resolver（依赖解析器）= 编译器里的 Linker（链接器）+ Type Checker（类型检查器）+ Package Manager（包管理器）

它其实不是 DAG Engine 的一部分。

它应该独立成为整个 QuantLab 的一个基础组件。

这是我建议修改的第一点。

一、重新定义 Dependency Resolver

很多人理解：

NodeA

↓

NodeB

就是 Dependency。

实际上不是。

真正的 Dependency 有五种。

Node Dependency

Data Dependency

Semantic Dependency

Package Dependency

Runtime Dependency

Version Dependency

我们需要全部支持。

否则以后：

Alpha101

↓

Custom Factor

↓

LLM Factor

↓

Online Feature

一定会乱。

二、整体架构

我建议新增：

research/

resolver/

├── dependency_resolver.py
├── graph_builder.py
├── semantic_checker.py
├── package_resolver.py
├── version_resolver.py
├── type_checker.py
├── validator.py
├── planner.py
└── registry.py

这里注意：

Resolver 不是一个类。

而是一个系统。

三、整体流程

整个 Graph 编译流程建议改成：

Research Graph

↓

Dependency Resolver
────────────────────────

Dependency Builder

↓

Semantic Resolver

↓

Type Resolver

↓

Package Resolver

↓

Version Resolver

↓

Graph Expander

────────────────────────

Compiled Graph

↓

Optimizer

↓

Execution Plan

这是完整流程。

四、第一层：Node Dependency

最简单。

例如：

Alpha017

↓

需要：

Return

Graph：

用户：

Close

↓

Alpha017

Resolver：

自动：

发现：

Alpha017

需要：

Return

于是：

自动补：

Close

↓

Return

↓

Alpha017

所以：

Graph：

可以不完整。

Resolver：

负责：

补全。

五、Dependency Registry

所有 Node：

必须声明：

依赖。

例如：

id: alpha017

inputs:

- return

- volume_rank

requires:

- return

- rank

- correlation

这里：

requires：

不是：

Input。

而是：

依赖节点。

以后：

Compiler：

直接：

递归解析。

六、递归依赖解析

例如：

Alpha017：

依赖：

Return

Rank

Correlation

但是：

Correlation：

又依赖：

Return

RollingMean

最终：

Resolver：

得到：

Close

↓

Return

├─────┐

▼     ▼

Rank RollingMean

      │

      ▼

Correlation

      │

      ▼

Alpha017

用户：

不用画。

系统：

自动展开。

七、Semantic Dependency

这是我认为整个系统最大的升级。

例如：

RSI：

输入：

不是：

close

而是：

Price

Return：

输出：

Return

Rank：

输入：

NumericFeature

以后：

Resolver：

发现：

RSI

↓

Return

直接：

报错。

因为：

Return：

需要：

Price。

RSI：

输出：

Indicator。

语义：

不一致。

所以：

Node：

增加：

input_type:

PriceSeries

output_type:

ReturnSeries

以后：

Semantic Resolver：

自动检查。

八、Data Dependency

例如：

Alpha017：

需要：

Volume

但是：

Dataset：

没有：

Volume

Resolver：

Compile：

失败。

例如：

Dataset:

CryptoTick

里面：

只有：

Price

没有：

Volume

Graph：

不能运行。

九、Package Dependency

例如：

用户：

使用：

Alpha191

实际上：

Package：

没安装。

Resolver：

发现：

Package Missing

自动：

提示：

Install:

alpha191

以后：

Node：

真正：

插件化。

十、Version Dependency

例如：

Graph：

RSI

↓

Alpha017

但是：

Alpha017：

要求：

RSI>=2.0

现在：

Registry：

只有：

RSI1.0

Resolver：

Compile：

失败。

以后：

版本：

真正：

安全。

十一、Graph Expansion

这是我认为必须增加的一层。

用户：

画：

Alpha017

Resolver：

真正展开：

Close

↓

Return

↓

RollingMean

↓

Rank

↓

Correlation

↓

Alpha017

Graph：

从：

Logical Graph

变成：

Physical Graph
十二、Dependency Tree

每一个 Node：

都应该：

自动：

生成：

Dependency Tree

例如：

Alpha017
├── Return
│   └── Close
├── Rank
│   └── Return
└── Correlation
    ├── Return
    └── RollingMean

以后：

前端：

直接：

展示。

十三、Dependency Fingerprint

这里我建议增加。

例如：

Graph：

Return(window=5)

Hash：

ABCD...

另一边：

也是：

Return(window=5)

Resolver：

发现：

Hash：

一样。

自动：

Merge。

而不是：

Optimizer：

以后：

Graph：

天然：

没有重复节点。

十四、Dependency Scope

量化：

还有一个特殊问题。

例如：

Cross Section Rank

只能：

一天

计算。

不能：

TimeSeries。

所以：

Node：

增加：

scope:

time_series

cross_section

panel

Resolver：

自动：

检查。

以后：

不会：

混用。

十五、Execution Dependency

例如：

GPU Node：

LSTM

CPU：

EMA

Resolver：

自动：

标记：

GPU Stage

↓

CPU Stage

Scheduler：

不用：

分析。

十六、Circular Resolver

除了：

Compile：

报错。

我建议：

还能：

指出：

A

↓

B

↓

C

↓

A

形成：

Dependency Report

例如：

Alpha017

↓

Correlation

↓

RollingFeature

↓

Alpha017

直接：

定位。

十七、Lazy Dependency

这是未来：

Online Feature：

必须有。

例如：

NewsSentiment

只有：

真正：

请求。

才：

计算。

Resolver：

标记：

Lazy

Scheduler：

不会：

提前：

执行。

十八、Resolver 输出

最终：

不要：

输出：

Graph。

应该：

输出：

CompiledGraph。

例如：

CompiledGraph

nodes

edges

dependency_tree

execution_stage

cache_plan

type_info

semantic_info

以后：

Optimizer：

不用：

重新分析。

十九、再升级一步：Capability Resolver（这是我最推荐增加的一层）

我认为，真正专业的 Dependency Resolver，不应该只解析依赖关系，还应该解析能力（Capability）。

也就是说，每个 ResearchNode 不只是声明输入输出，还声明自己具备什么能力：

capabilities:
  - incremental
  - parallel
  - gpu
  - streaming
  - cacheable
  - deterministic

例如：

Node	Incremental	GPU	Streaming	Cacheable
EMA	✅	❌	✅	✅
Alpha017	✅	❌	❌	✅
LSTM Feature	❌	✅	❌	❌
News Embedding	❌	✅	✅	部分

Dependency Resolver 在编译阶段就可以形成一份 Capability Graph：

Graph
    │
    ▼
Capability Resolver
    │
    ├── Incremental Path
    ├── GPU Path
    ├── Streaming Path
    ├── Cache Plan
    └── Parallel Groups

随后：

Scheduler 根据 Capability Graph 决定如何调度；
Executor 不需要再推断能力；
Observe Studio 可以直接展示哪些节点支持 GPU、哪些命中缓存、哪些采用增量计算。

这样，Resolver 就不仅是"找依赖"，而是整个 Research Graph 的编译分析中心（Compile Analysis Center）。

二十、我建议的最终架构（推荐采用）

经过前面所有讨论，我建议 Research Graph Engine 的真正内核应该设计成下面这样：

ResearchNode Registry
        │
        ▼
Dependency Resolver
────────────────────────────────
Node Resolver
Semantic Resolver
Type Resolver
Package Resolver
Version Resolver
Capability Resolver
Graph Expander
────────────────────────────────
        │
        ▼
CompiledGraph
────────────────────────────────
Dependency Tree
Execution Stage
Capability Graph
Cache Plan
Incremental Plan
GPU Plan
Type Metadata
Semantic Metadata
────────────────────────────────
        │
        ▼
Optimizer
        │
        ▼
Execution Planner
        │
        ▼
Scheduler
        │
        ▼
Executor
我认为最关键的设计原则

我建议我们把 Dependency Resolver 定位成：

Research Graph 的编译器前端（Compiler Frontend）。

它绝不参与执行，也不做性能优化。它的职责只有四件事：

理解用户画出的逻辑图（Logical Graph）。
补全所有隐式依赖（Graph Expansion）。
验证语义、类型、版本、数据和能力是否一致。
生成完整的 CompiledGraph，交给 Optimizer 和 Scheduler。

这样，后面的 Optimizer、Execution Planner、Scheduler、Executor 都可以专注于自己的职责，整个 QuantLab 内核会保持清晰、可维护，并且具备长期扩展能力。


缓存机制
而且我要先纠正一个观念。

缓存(Cache) 不是为了加速。

很多框架（Airflow、Dagster、Sklearn Pipeline）都把 Cache 看成：

Node
    ↓
Result
    ↓
Cache

这是不够的。

我建议重新定义 Cache

在 QuantLab 里面：

Cache 是 Research Graph 的第二层存储（Secondary Storage）

也就是说：

整个系统以后不是：

Research Graph

↓

Execute

↓

Result

而应该变成：

Research Graph

↓

Cache System

↓

Execution Engine

↓

Materializer

Cache 是执行器之前的一层。

一、为什么量化平台必须重新设计 Cache？

因为量化最大的特点：

不是：

计算一次

而是：

每天重复计算

例如：

今天：

BTC

2018~2026

算了一遍。

明天：

新增：

2026-06-27

如果：

重新计算：

RSI

ATR

MACD

Alpha101

八年数据。

这是不能接受的。

所以：

Cache 在量化平台里：

不是优化。

而是：

默认工作方式。

二、整个 Cache 架构

我建议：

                   Cache Manager
====================================================

Memory Cache

↓

Local Disk Cache

↓

Feature Store

↓

Object Store

↓

Remote Cache

不是：

一级。

而是：

五级。

三、第一层：Memory Cache（L1）

最快。

生命周期：

一次执行

例如：

Graph：

Return

↓

EMA20

↓

Alpha017

EMA：

已经：

用了：

Return。

Alpha017：

不用：

重新：

算：

Return。

直接：

Memory。

生命周期：

ExecutionContext

结束：

自动：

释放。

四、第二层：Local Cache（L2）

建议：

Parquet

Arrow IPC

Feather

存：

SSD。

例如：

cache/

return/

hash.parquet

以后：

重启：

仍然：

存在。

五、第三层：Feature Store（L3）

这是我建议新增的。

不是：

Cache。

而是：

长期：

Feature Repository。

例如：

feature_store/

RSI14/

BTC/

1H/

2024.parquet

以后：

ML：

Research：

Observe：

共享。

这里：

Feature Store：

其实已经：

不是 Cache。

而是：

数据资产。

六、第四层：Object Store（L4）

以后：

支持：

MinIO

S3

OSS

保存：

Alpha101

Feature Package

Model Artifact

用于：

长期保存。

七、第五层：Remote Cache（L5）

以后：

多机器：

例如：

Redis

Ray

Shared Memory

目前：

个人版：

可以：

预留接口。

不用实现。

八、Cache Key（最重要）

这里：

很多系统：

设计不好。

例如：

RSI14

作为 Key。

这是错的。

真正：

Key：

必须：

包括：

Node

+

Version

+

Parameters

+

Dataset

+

Range

+

Dependency Fingerprint

例如：

RSI

window=14

dataset=crypto_1h

BTC

2018~2026

CloseHash=ABCD...

最终：

Hash：

F3A928...
九、Fingerprint（整个 Cache 的核心）

我建议：

Fingerprint：

统一：

Fingerprint

=

Node Hash

+

Input Hash

+

Parameter Hash

+

Version Hash

例如：

EMA20

↓

Input

CloseHash

↓

Param

20

↓

Version

1.1.0

生成：

SHA256

以后：

任何：

变化。

自动：

失效。

十、Cache Unit

不要：

缓存：

整个：

Graph。

而是：

缓存：

每一个：

Node。

例如：

Close

↓

Return

↓

EMA

↓

MACD

Return：

缓存。

EMA：

缓存。

MACD：

缓存。

以后：

Graph：

改变：

只：

重算：

受影响：

Node。

十一、Incremental Cache（量化必须有）

例如：

昨天：

EMA20

缓存：

到：

2026-06-26

今天：

新增：

2026-06-27

不要：

重新：

八年。

Node：

实现：

update(new_rows)

Cache：

保存：

最后20根Bar

即可。

这是专业量化平台最重要的能力之一。

十二、Window Cache

例如：

RollingMean。

真正：

需要：

Window=20

Cache：

只：

保存：

最后：

20

+

Margin

不用：

整个：

DataFrame。

十三、Column Cache

ResearchFrame：

例如：

datetime

symbol

close

volume

return

ema20

如果：

只：

请求：

ema20

Cache：

不要：

读：

全部。

支持：

Column Pushdown。

建议：

Arrow。

十四、Lazy Cache

Graph：

很多：

Node：

最终：

没有：

被：

Materialize。

不要：

提前：

算。

例如：

RSI

ATR

MACD

最终：

只：

需要：

RSI

ATR：

不用：

Compute。

十五、Cache Policy

每个 Node：

声明：

cache:

enabled: true

level:

memory

disk

feature_store

ttl:

never

例如：

News：

TTL

1天

价格：

TTL

永久
十六、Cache Invalidator

Cache：

最大的难题：

不是：

存。

而是：

什么时候：

删。

我建议：

统一：

事件驱动。

例如：

Dataset Updated

↓

Invalidate

↓

Return

↓

EMA

↓

MACD

不是：

全部：

删除。

而是：

Dependency：

传播。

十七、Dependency Invalidation

例如：

Close

更新。

Graph：

Close

↓

Return

↓

EMA

↓

MACD

只有：

这些：

失效。

ATR：

如果：

不用：

Close。

不用：

删。

十八、Cache Planner（新增）

这里：

我建议：

增加：

Planner。

Compiler：

之后：

Compiled Graph

↓

Cache Planner

自动：

决定：

哪些：

Memory

哪些：

Disk

哪些：

FeatureStore

Scheduler：

不用：

管。

十九、Materialized Feature（这里我建议升级）

很多平台：

Cache：

最后：

删。

我建议：

如果：

Feature：

价值：

高。

直接：

升级：

Cache

↓

Materialized Feature

进入：

Feature Registry

例如：

Alpha101

Daily

Top3000

以后：

所有：

ML：

直接：

读取。

不用：

重算。

二十、Cache Manifest

每一个 Cache：

都有：

cache_id:

F39AB...

node:

EMA20

dataset:

crypto_1h

range:

2018-2026

version:

1.2

dependencies:

CloseHash

created:

...

size:

...

ttl:

never

以后：

Observe：

直接：

查看。

二十一、我建议再升级一步（这是整个缓存设计里最重要的一层）

我建议把 Cache 分成两种完全不同的东西：

① Execution Cache（执行缓存）

生命周期：

一次 Graph 执行

目的：

避免重复计算。

例如：

Return

在同一张图里只算一次。

② Research Asset Cache（研究资产缓存）

生命周期：

长期

目的：

让研究成果沉淀。

例如：

Alpha101

算好以后：

自动：

升级：

Research Asset

以后：

ML、

Strategy、

Observe、

Backtest

全部：

共享。

所以：

未来：

整个：

Feature Store：

其实：

已经：

不是：

Cache。

而是：

Research Asset Store。

这是我认为和普通 DAG 最大的区别。

二十二、最终架构（推荐）
                     Cache Manager
================================================================

Execution Cache (L1)
────────────────────────────────────────────

Memory Cache

Node Cache

Window Cache

================================================================

Persistent Cache (L2)
────────────────────────────────────────────

Parquet

Arrow

Feather

================================================================

Research Asset Store (L3)
────────────────────────────────────────────

Feature Store

Factor Store

Materialized Feature

================================================================

Object Store (L4)
────────────────────────────────────────────

Artifacts

Snapshots

Packages

================================================================

Remote Cache (L5)
────────────────────────────────────────────

Redis

Ray

Distributed Cache

================================================================

Cache Planner

Fingerprint Engine

Dependency Invalidator

Incremental Updater

Cache Manifest

================================================================
我认为还可以再升级一个理念（也是我最推荐采用的）

这里是我认为整个 QuantLab 与传统 ML 平台最大的不同。

Cache 不应该被视为性能优化，而应该被视为"研究成果的生命周期管理"。

也就是说：

ResearchNode
        │
        ▼
Execution Cache
        │
        ▼
Persistent Cache
        │
        ▼
Materialized Feature
        │
        ▼
Feature Registry
        │
        ▼
Asset Registry

这意味着，一个耗时数小时计算得到的 Alpha、复杂特征或横截面因子，不会因为程序关闭而"消失"，而是自然演进为可复用、可版本管理、可验证、可共享的研究资产。

这是我认为 QuantLab 与一般 DAG 引擎最大的设计差异，也是整个 Research Graph Engine 最有价值的地方。



增量计算
我认为，增量计算（Incremental Computing） 是我们整个 Research Graph Engine 里面价值最高、但也是最容易设计错误的模块。

而且，我建议先推翻一个传统概念。

一、传统的增量计算，其实不适合量化

很多系统理解的 Incremental 是：

昨天：

A → B → C

今天：

新增一点数据

↓

重新算 B

重新算 C

或者：

只处理新增的数据

这对于 ETL 可以。

但是对于量化来说，不够。

原因：

例如：

EMA20

新增一根K线：

真的只算：

最后一根

吗？

不是。

例如：

RollingStd(252)

需要：

252 根窗口。

再例如：

CrossSectionRank

新增：

一个股票。

整个：

Rank：

全部：

变化。

所以：

不同的 Node，增量策略完全不同。

因此：

我建议：

Incremental 不属于 Engine。

它属于：

ResearchNode 的一种 Capability。

二、重新定义 Incremental

建议：

整个系统：

不要叫：

Incremental Computing

而叫：

Incremental Execution Framework

因为：

它不是：

一种算法。

而是：

整个执行框架。

三、整体架构

建议新增：

research/

incremental/

├── planner.py
├── analyzer.py
├── delta.py
├── updater.py
├── checkpoint.py
├── snapshot.py
├── invalidator.py
├── state_store.py
└── policy.py

不要：

写在：

Executor。

四、整体流程

整个执行：

应该：

变成：

Dataset Updated

↓

Delta Analyzer

↓

Incremental Planner

↓

Dependency Analyzer

↓

Execution Planner

↓

Incremental Executor

↓

Checkpoint

↓

Cache
五、Delta Analyzer

这是第一层。

负责：

比较：

昨天：

BTC

2018~2026

今天：

BTC

+

2026-06-27

得到：

Delta。

例如：

+1 Bar

或者：

+300 Symbols

或者：

修改：

2025-03-10

输出：

统一：

Delta

例如：

Delta:

added_rows

updated_rows

deleted_rows

整个系统：

统一。

六、Incremental Policy

这里：

我认为：

是整个系统最重要的设计。

每一个：

Node：

声明：

自己的：

增量策略。

例如：

incremental:

append_only

例如：

Close：

新增：

直接：

Append。

EMA：

incremental:

rolling_window

ATR：

也是。

Rank：

incremental:

full_partition

为什么？

因为：

新增：

一个股票。

整个：

排名：

变化。

LSTM：

incremental:

retrain

不能：

增量。

所以：

Incremental：

不是：

统一。

而是：

Policy。

七、建议定义标准策略

我建议定义一个统一的枚举，而不是让每个节点自己发明策略。

AppendOnly

新增数据即可。

例如：

Close

Volume
RollingWindow

需要保留窗口。

例如：

EMA

ATR

RollingMean
PartitionRecompute

只重算受影响分区。

例如：

CrossSectionRank

IndustryRank

不是全市场。

而是：

某一天。

DependencyRecompute

依赖变化：

自动：

传播。

例如：

Alpha017
FullRecompute

必须：

全部：

重新：

计算。

例如：

PCA

ICA

LSTM Training
Stateful

维护：

内部状态。

例如：

Kalman Filter。

八、State Store

很多系统：

没有。

我建议必须有。

例如：

EMA20。

真正：

需要：

什么？

不是：

整个：

历史。

而是：

最后：

EMA。

所以：

Node：

可以：

保存：

State。

例如：

EMAState

last_value

last_timestamp

以后：

更新：

非常快。

九、Checkpoint

建议：

每一个：

Graph：

周期：

保存：

Checkpoint。

例如：

Checkpoint

↓

Graph Hash

↓

Node States

↓

Cache Hash

↓

Timestamp

以后：

恢复：

不用：

重新：

Compile。

十、Snapshot

Checkpoint：

保存：

状态。

Snapshot：

保存：

结果。

例如：

2026-06-26

Feature Snapshot

以后：

Observe：

直接：

回放。

十一、Dependency Propagation

这里：

非常重要。

例如：

Close

↓

Return

↓

EMA

↓

Alpha017

Close：

更新。

Propagation：

自动：

标记：

Return

EMA

Alpha017

Dirty。

但是：

ATR：

如果：

没有：

依赖。

不动。

十二、Dirty Graph

我建议：

Graph：

增加：

Dirty Flag。

例如：

Close

Dirty

↓

Return

Dirty

↓

EMA

Dirty

↓

MACD

Clean

Scheduler：

只：

执行：

Dirty。

十三、Execution Planner

Planner：

根据：

Incremental：

决定：

执行。

例如：

EMA

↓

RollingWindow

Planner：

自动：

生成：

Load Last State

↓

Load Last20Bars

↓

Update

↓

Write State

而不是：

重新：

Compute。

十四、Incremental Materializer

Materializer：

也：

支持：

增量。

例如：

昨天：

X

100000行

今天：

新增：

100。

不要：

重新：

100000。

Append：

即可。

十五、Incremental Cache

Cache：

不要：

删。

而是：

Merge。

例如：

Return

↓

Old Cache

+

New Delta

↓

Merge

真正：

Feature：

越来越完整。

十六、Window Optimizer

例如：

Rolling252

不要：

读：

2520。

只：

读：

252

+

Delta

Planner：

自动：

优化。

十七、Streaming Mode

未来：

实时。

例如：

Tick

↓

Return

↓

EMA

↓

Signal

Graph：

一直：

活着。

不是：

每次：

重新：

启动。

十八、Incremental Report

Observe：

新增：

页面。

例如：

Incremental Report

Graph

Execution Time

Cache Hit

Dirty Nodes

Updated Nodes

Recomputed Nodes

Skipped Nodes

以后：

调试：

非常方便。

十九、我建议再升级一步：ChangeSet（这是我认为整个增量系统真正的核心）

到这里，我认为还有一个缺失。

我们一直在说：

"新增了一根 K 线"

但系统真正应该处理的，不是 Dataset，而是：

ChangeSet（变更集）

也就是说，整个系统收到的输入永远不是：

新的 DataFrame

而是：

ChangeSet

例如：

change_set:

dataset: crypto_1h

changes:

- append:
    symbol: BTCUSDT
    datetime: 2026-06-27 10:00

- update:
    symbol: ETHUSDT
    datetime: 2026-06-25 08:00

- delete:
    symbol: SOLUSDT
    datetime: 2026-05-10

随后：

Delta Analyzer：

分析：

ChangeSet

↓

Dirty Range

↓

Dirty Node

↓

Dirty Partition

这样：

Incremental：

真正：

统一。

以后：

不仅：

价格。

未来：

基本面、

新闻、

因子、

Label、

Universe

全部：

统一。

二十、最终架构（推荐采用）

我建议整个 Incremental Framework 最终应该设计成：

                     Incremental Framework
================================================================

ChangeSet
────────────────────────────────────────────

Append

Update

Delete

================================================================

Delta Analyzer
────────────────────────────────────────────

Dirty Range

Dirty Partition

Dirty Node

================================================================

Incremental Planner
────────────────────────────────────────────

AppendOnly

RollingWindow

PartitionRecompute

DependencyRecompute

Stateful

FullRecompute

================================================================

State Store
────────────────────────────────────────────

EMA State

Rolling State

Kalman State

Custom State

================================================================

Checkpoint

Snapshot

Cache Merge

Dependency Propagation

================================================================

Incremental Materializer

================================================================

Observe Incremental Report

================================================================
我认为还应该再升级一个理念（也是我最推荐采用的）

这里是我认为 QuantLab 和普通 DAG 最大的不同。

Incremental 不应该只是"性能优化"，而应该成为整个 Research Graph 的默认执行模式。

也就是说：

Research Graph
        │
        ▼
ChangeSet
        │
        ▼
Dependency Resolver
        │
        ▼
Dirty Graph
        │
        ▼
Incremental Planner
        │
        ▼
Incremental Executor
        │
        ▼
State Store + Cache

只有在 Planner 判断：

节点不支持增量；
数据发生结构性变化（例如 Universe、特征定义、Label 定义变化）；
版本升级导致指纹失效；

才自动退化为：

Full Recompute
我唯一建议修改的一点

前面我们一直把 ResearchNode 看成：

ResearchNode
    ↓
compute()

经过增量计算设计后，我建议升级为：

class ResearchNode:
    def compute(...)
    def update(...)
    def save_state(...)
    def load_state(...)
    def invalidate(...)
    def estimate_delta(...)

也就是说，ResearchNode 不再是一个"一次性计算节点"，而是一个具有生命周期和状态管理能力的计算单元。

这样，QuantLab 才能真正做到：

每天自动更新几千个 Alpha；
实时更新策略特征；
支持分钟级、秒级甚至 Tick 级计算；
在保持正确性的前提下，把绝大多数计算量限制在"变化的那一小部分数据"上。

这才是专业量化研究平台真正需要的增量计算体系。


前端可视化 Graph Builder
它不是一个"流程图编辑器（Flow Editor）"。

如果只是做成 Node-RED、Draw.io、React Flow 那样，其实价值并不高，因为用户最终得到的仍然只是一个 DAG。

我建议我们把它设计成：

Visual Quant Research IDE（可视化量化研究 IDE）

也就是说，它不是画图工具，而是整个 QuantLab 的研究工作台（Research Workbench）。

这是整个前端价值最高的模块之一。

一、重新定义 Graph Builder

不要叫：

Graph Builder

建议正式名称：

Research Graph Studio

或者

Visual Research Studio

它属于：

ML Lab

    │

    ▼

Research Graph Studio

以后：

Research Studio

ML Lab

Strategy Studio

全部共用。

二、整个定位

它不是：

Node

↓

Node

↓

Node

而是：

整个研究过程。

例如：

Dataset

↓

Universe

↓

Features

↓

Alpha

↓

Labels

↓

Validation

↓

Training

↓

Model

全部：

可视化。

三、整体架构

建议：

frontend/

modules/

research_graph/

├── GraphCanvas
├── NodePalette
├── Inspector
├── PropertyPanel
├── MiniMap
├── DependencyView
├── ExecutionView
├── CacheView
├── ValidationView
├── SearchPanel
└── Toolbar

Graph：

不是：

一个组件。

而是：

整个模块。

四、页面布局

建议采用专业 IDE 布局，而不是普通流程图。

┌────────────────────────────────────────────────────────────┐
│ Toolbar                                                    │
├──────────────┬──────────────────────────────┬──────────────┤
│              │                              │              │
│ Node Library │       Graph Canvas           │ Inspector    │
│              │                              │              │
│              │                              │              │
├──────────────┼──────────────────────────────┼──────────────┤
│ Console      │ Execution / Validation       │ Property     │
└──────────────┴──────────────────────────────┴──────────────┘

是不是很像：

VSCode。

这就是目标。

五、Node Library

左侧：

不是：

几十个节点。

而是：

整个 Registry。

例如：

Research Nodes

Data

Indicators

Transform

Aggregation

Ranking

Selection

Labels

Alpha101

Alpha191

Fundamental

Alternative

ML

Custom

支持：

搜索。

收藏。

最近使用。

六、Graph Canvas

中间：

真正：

Research Graph。

例如：

Close

↓

Return

↓

EMA20

↓

Momentum

↓

Alpha017

↓

FutureReturn5

↓

Training Dataset

这里：

Graph：

自动布局。

不要：

用户：

一点点：

拖。

建议：

默认：

使用：

DAG Layout。

例如：

ELK。

而不是：

Force Layout。

七、连接方式

不要：

用户：

自己：

连。

例如：

用户：

拖：

RSI

到：

Canvas。

再：

拖：

Momentum

系统：

自动：

推断：

依赖。

例如：

Close

↓

RSI

↓

Momentum

不用：

画：

Close。

八、Dependency Expansion

Graph：

支持：

两种模式。

Logical：

Alpha017

Physical：

Close

↓

Return

↓

Rank

↓

Correlation

↓

Alpha017

按钮：

Expand Dependencies

即可。

这是整个 Builder 最有价值的功能。

九、Inspector

右边：

点击：

Node。

例如：

EMA20。

显示：

Node

EMA20

Category

Indicator

Version

1.0

Parameters

Window=20

Output

Feature<EMA>

Execution

12ms

Cache

Hit
十、Property Panel

支持：

修改：

Window

20

↓

30

Graph：

自动：

Compile。

自动：

重新：

Fingerprint。

十一、Semantic Overlay

我建议增加：

一种模式。

例如：

打开：

Semantic View

Graph：

变成：

Price

↓

Return

↓

Rank

↓

Alpha

不是：

Node。

而是：

语义。

以后：

非常容易：

理解。

十二、Execution Overlay

点击：

Run。

Graph：

变：

绿色：

已执行

黄色：

执行中

灰色：

等待

蓝色：

Cache Hit

红色：

失败

整个：

Replay。

十三、Cache Overlay

Graph：

显示：

EMA

Cache

Disk

RSI

Memory

Alpha017

FeatureStore

直接：

知道：

缓存。

十四、Validation Overlay

例如：

Compile：

失败。

Graph：

直接：

红色。

例如：

Return

↓

RSI

提示：

Type Error

Expected:

Price

Actual:

Indicator

不用：

Console。

十五、Incremental Overlay

新增：

一天。

Graph：

直接：

显示：

Dirty

↓

Return

Dirty

↓

EMA

Clean

↓

MACD

用户：

一眼：

知道：

哪里：

重新：

算。

十六、Execution Timeline

下面：

增加：

Timeline。

例如：

Compile

↓

Dependency Resolve

↓

Cache

↓

Stage1

↓

Stage2

↓

Materialize

点击：

跳。

十七、Node Search

Graph：

很大。

支持：

Ctrl+P

例如：

输入：

EMA

直接：

定位。

十八、Graph Diff

这是我最推荐的功能之一。

例如：

昨天：

Graph。

今天：

Graph。

显示：

新增：

EMA30

删除：

RSI14

修改：

Window20→30

非常适合实验管理。

十九、Experiment Compare

例如：

ExperimentA：

EMA20

ExperimentB：

EMA30

Graph：

左右：

Diff。

训练：

结果：

一起：

显示。

二十、Observe Integration

运行：

结束。

Graph：

点击：

Node。

直接：

查看：

Distribution

Statistics

Missing

SHAP

Correlation

不用：

跳：

Observe。

二十一、Graph Templates

建议：

内置：

模板。

例如：

Time Series Forecast

Cross Section Alpha

Factor Research

Triple Barrier

LightGBM

XGBoost

LSTM

一键：

生成。

二十二、Graph Package

Graph：

不是：

文件。

而是：

Package。

例如：

research_graph/

graph.yaml

nodes/

metadata/

preview.png

README.md

以后：

直接：

导入。

二十三、AI Graph Builder（我认为必须做）

这是整个 QuantLab 最大的亮点。

例如：

输入：

帮我做一个

Alpha101+

LightGBM

预测5日收益

AI：

直接：

生成：

Graph。

例如：

Dataset

↓

Universe

↓

Alpha101

↓

Selection

↓

Feature

↓

FutureReturn5

↓

LightGBM

↓

Validation

用户：

修改。

而不是：

从零开始。

二十四、我建议再升级一步：Research Workspace（这是整个前端设计最重要的一层）

到这里，我认为还缺一层。

不要把 Graph 看成一个独立页面。

它应该属于：

Workspace

例如：

Workspace

├── Graph
├── Dataset
├── Notebook
├── Metrics
├── Observe
├── Validation
├── Models
└── Assets

也就是说：

Graph：

永远：

只是：

Workspace：

一个 Tab。

这样：

以后：

用户：

可以：

Graph

↓

Run

↓

Notebook

↓

Observe

↓

Model Registry

全部：

不用：

跳页面。

二十五、最终架构（推荐采用）
                  Research Graph Studio
================================================================

Workspace
────────────────────────────────────────────

Graph

Notebook

Dataset

Metrics

================================================================

Node Library
────────────────────────────────────────────

Registry

Search

Favorites

Templates

================================================================

Graph Canvas
────────────────────────────────────────────

Logical View

Physical View

Semantic View

================================================================

Inspector
────────────────────────────────────────────

Properties

Dependencies

Artifacts

Metrics

================================================================

Graph Overlay
────────────────────────────────────────────

Execution

Validation

Cache

Incremental

Dependency

================================================================

Timeline

Console

Diff

Experiment Compare

================================================================

AI Assistant

Template Center

Package Manager

================================================================
二十六、我认为还应该再升级一个理念（也是我最推荐采用的）

如果我们只是做一个 Graph Builder，它最终还是一个"流程图工具"。

我建议把它定义成：

Research IDE

也就是说，用户一天的研究工作全部在这里完成。

完整工作流应该是：

Research Workspace
        │
        ▼
Research Graph（设计）
        │
        ▼
Compile（编译）
        │
        ▼
Run（执行）
        │
        ▼
Observe（分析）
        │
        ▼
Validation（验证）
        │
        ▼
Model Registry（登记）
        │
        ▼
Strategy Builder（策略封装）
我最后还有一个建议（我认为这是整个 QuantLab 前端最大的升级）

结合我们前面讨论的 ResearchNode、DAG Engine、Dependency Resolver、Incremental Framework，我建议前端不要只是"画 DAG"。

应该把它做成一个真正的 Visual Compiler。

也就是说，当用户每拖入一个节点、修改一个参数时，前端就实时调用编译能力，立即反馈：

自动补全缺失依赖（无需手工连线）；
实时类型检查与语义检查；
预估执行时间、内存占用和缓存命中率；
标出哪些节点会增量执行、哪些必须全量重算；
显示执行阶段（Stage）和并行组（Parallel Group）；
展示最终生成的 CompiledGraph，而不仅是用户画出的 Logical Graph。

这样，Research Graph Studio 就不仅仅是一个可视化编辑器，而是真正意义上的量化研究编译器前端。这也是我认为它能够超越 QuantDigger、Qlib、BigQuant 等平台的重要原因：用户看到的不只是流程，而是整个研究图从设计、编译、优化到执行的全过程。