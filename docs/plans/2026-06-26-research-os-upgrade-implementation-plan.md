# QuantLab Research OS 升级 — 实施计划

> **依据 Spec**：[2026-06-26-research-os-upgrade.md](./2026-06-26-research-os-upgrade.md)
> **创建日期**：2026-06-26
> **交付方案**：方案 B（一次性全量）
> **回滚机制**：5 重（Git 分支 + DB 备份 + Feature Flag + 兼容层 + 双写过渡）

---

## 实施总览

按 spec 第十节实施顺序，分 12 个阶段推进。每个阶段含明确产出、验收、依赖。阶段间存在依赖链，但阶段内任务可并行。

**总原则**：
- 每完成一个阶段即跑通该阶段单元测试
- DB 变更前必备份
- 旧代码迁移时保留兼容层转发
- 首次回测用短历史数据（BTCUSDT 2024-01-01~2024-06-01）

---

## 阶段 1：基础层（ResearchFrame + ResearchNode 基类 + Port + Manifest）

**目标**：建立统一数据契约与节点抽象根。

### 任务
1.1 创建 `quantlab/research/__init__.py`
1.2 创建 `quantlab/research/frame.py`
   - `ResearchFrame` 类：`(datetime, symbol)` MultiIndex DataFrame 封装
   - `from_ohlcv()` / `from_single_symbol()` / `as_time_series()` / `as_cross_section()`
1.3 创建 `quantlab/research/node/ports.py`
   - `Port` dataclass（name/type/required/description）
   - `PortType` 枚举（series/frame/scalar/panel）
1.4 创建 `quantlab/research/node/manifest.py`
   - `NodeManifest` dataclass
   - `NodeMetadata`（cost/description/author/deprecated）
   - 序列化/反序列化（to_json/from_json）
1.5 创建 `quantlab/research/node/base.py`
   - `ResearchNode` 基类（能力接口，非继承树）
   - 生命周期方法：validate/fingerprint/estimate_cost/describe/compute
   - 能力声明：supports_incremental/supports_parallel/supports_gpu/cache_policy
   - 增量能力：update/save_state/load_state/invalidate/estimate_delta

### 产出文件
```
quantlab/research/__init__.py
quantlab/research/frame.py
quantlab/research/node/__init__.py
quantlab/research/node/ports.py
quantlab/research/node/manifest.py
quantlab/research/node/base.py
```

### 单元测试
- `tests/research/unit/test_frame.py`：MultiIndex 构造、退化模式、from_ohlcv
- `tests/research/unit/test_port.py`：Port 序列化
- `tests/research/unit/test_manifest.py`：Manifest 序列化、版本对比
- `tests/research/unit/test_node_base.py`：能力接口默认值、fingerprint 稳定性

### 验收
- ResearchFrame 可从 OHLCV DataFrame 构造
- ResearchNode 子类可声明 inputs/outputs/params
- fingerprint 相同参数稳定一致

---

## 阶段 2：节点层（9 类 builtin Node + 旧 Feature/Factor 迁移）

**目标**：实现所有 builtin 节点，迁移旧体系。

### 任务
2.1 `research/node/builtin/data.py`：DataNode（Close/High/Low/Open/Volume/VWAP）
2.2 `research/node/builtin/transform.py`：TransformNode（Return/ZScore/Log/Diff/Normalize）+ 封装 `factor/operators/ts.py` 纯函数
2.3 `research/node/builtin/indicator.py`：IndicatorNode（RSI/ATR/MACD/EMA/SMA），迁移 `ml/feature/builtin.py`
2.4 `research/node/builtin/alpha.py`：AlphaNode（Alpha001-101, Alpha001-191），迁移 `factor/alpha101/`, `factor/alpha191/`
2.5 `research/node/builtin/aggregation.py`：AggregationNode（RollingMean/Std/Max/Min）
2.6 `research/node/builtin/ranking.py`：RankingNode（CrossSectionRank/Percentile/TopN）
2.7 `research/node/builtin/selection.py`：SelectionNode（UniverseFilter/LiquidityFilter）
2.8 `research/node/builtin/label.py`：LabelNode（FutureReturn/TripleBarrier/Direction），迁移 `ml/label/builtin.py`
2.9 `research/node/builtin/custom.py`：CustomNode 基类（用户扩展入口）

### 产出文件
```
quantlab/research/node/builtin/__init__.py
quantlab/research/node/builtin/{data,transform,indicator,alpha,aggregation,ranking,selection,label,custom}.py
```

### 单元测试
- 每类 Node 一个测试文件，验证 compute() 输入输出符合 ResearchFrame 契约
- 重点验证：RSI14、Alpha014、Alpha017、FutureReturn
- 旧实现迁移后输出与旧接口（Feature.compute/FactorInfo.fn）数值一致（回归测试）

### 验收
- 9 类 Node 全部可实例化、compute 返回 ResearchFrame
- Alpha017 可由 Return+Delay+TsCorr+Rank 组合表达
- 旧 RSI14 新实现输出 == 旧 `ml/feature/builtin.py:RSI14` 输出

---

## 阶段 3：图层（ResearchGraph + Edge + CompiledGraph + Executor + ExecutionContext）

**目标**：DAG 构建与执行引擎。

### 任务
3.1 `research/graph.py`
   - `ResearchGraph`：add_node/add_edge/compile/to_dag_view/fingerprint
   - `Edge` dataclass
   - `CompiledGraph` dataclass（topo_order/execution_plan/cache_plan/fingerprint）
3.2 `research/executor.py`
   - `ResearchExecutor.execute(graph, dataset_ctx, mode, changeset)`
   - 拓扑序遍历、缓存检查、compute 调用、ResearchFrame 传递
   - 并行执行（execution_plan 同层无依赖并行）
3.3 `ExecutionContext` dataclass（dataset_ctx/cache/frame_store/config/logger）

### 产出文件
```
quantlab/research/graph.py
quantlab/research/executor.py
```

### 单元测试
- `test_graph.py`：无环校验、端口类型匹配、拓扑序正确
- `test_executor.py`：执行顺序、并行分组、Alpha017 示例图端到端执行

### 验收
- Alpha017 Graph 可构建、编译、执行，产出正确 alpha017 ResearchFrame
- 同一 Node 在一次执行中只 compute 一次（L1 Execution Cache 生效）

---

## 阶段 4：缓存层（CacheManager + L1-L5 + CacheManifest + Invalidator + CachePlanner）

**目标**：5 级缓存 + 失效传播 + 编译期缓存规划。

### 任务
4.1 `research/cache/manager.py`：CacheManager 统一入口
4.2 L1：`memory.py`（MemoryCache dict）+ `window.py`（WindowCache 滚动）
4.3 L2：`parquet.py`（ParquetCache）+ `arrow.py`（ArrowCache）
4.4 L3：`feature_store.py`（FeatureStore/FactorStore/MaterializedFeature）
4.5 L4：`artifact.py`（Artifacts：SHAP/Importance/Distribution/Statistics）
4.6 L5：`redis.py`（RedisCache）
4.7 `research/cache/manifest.py`：CacheManifest dataclass + 持久化
4.8 `research/cache/invalidator.py`：反向依赖索引 + 事件驱动失效传播
4.9 `research/cache/planner.py`：CachePlanner（基于 cache_policy + estimate_cost 生成 CachePlan）

### 产出文件
```
quantlab/research/cache/{manager,memory,window,parquet,arrow,feature_store,artifact,redis,manifest,invalidator,planner}.py
```

### 单元测试
- `test_cache_manager.py`：L1 hit/miss、L2 持久化、L3 跨执行命中
- `test_invalidator.py`：Close 变更 → Return/EMA/MACD 失效，ATR 不失效
- `test_planner.py`：廉价节点进 L1、昂贵节点进 L2、高价值进 L3

### 验收
- 同图二次执行 L1 命中率 100%
- 跨执行 L2/L3 命中率 > 90%
- Dataset 更新触发依赖子图失效

---

## 阶段 5：注册层（NodeRegistry + UniverseRegistry + CalendarRegistry）

**目标**：统一注册表，替代旧 Registry，提供兼容层。

### 任务
5.1 `research/node/registry.py`：NodeRegistry（线程安全，id+version 注册）
   - register/get/list/list_categories/load_from_store
5.2 `research/universe.py`：UniverseRegistry + UniverseDefinition
   - 静态成员 + 动态规则（top_n_by_volume）+ rebalance
5.3 `research/calendar.py`：CalendarRegistry
   - 内置：crypto(7x24)、a_share、nyse
5.4 兼容层：修改 `ml/feature/registry.py:get_feature_registry()`、`factor/registry.py:get_registry()` 内部转发到 NodeRegistry，标记 deprecated

### 产出文件
```
quantlab/research/node/registry.py
quantlab/research/universe.py
quantlab/research/calendar.py
（修改）quantlab/ml/feature/registry.py
（修改）quantlab/factor/registry.py
```

### 单元测试
- `test_registry.py`：注册/查询/版本并存、线程安全
- `test_universe.py`：静态/动态 resolve
- `test_calendar.py`：crypto/a_share sessions

### 验收
- 启动时自动注册所有 builtin 节点
- `get_feature_registry()` 经兼容层返回 NodeRegistry 视图
- RSI@1.0.0 与 RSI@2.0.0 可并存

---

## 阶段 6：数据层（Dataset 升级 + Materializer + TrainingDataset）

**目标**：Dataset 新字段 + 实体化训练数据集。

### 任务
6.1 修改 `quantlab/ml/dataset/dataset.py`：新增 dataset_type/universe_id/calendar_id/adjustment/storage 字段
6.2 创建 `research/materializer.py`：Materializer + TrainingDataset
   - Join/Align/Normalize/Filter/Window/Split
   - 输入 CompiledGraph + Dataset + LabelNode + SplitConfig
6.3 创建 `research/dataset_context.py`：DatasetContext（提供原始数据访问给 Node）

### 产出文件
```
（修改）quantlab/ml/dataset/dataset.py
quantlab/research/materializer.py
quantlab/research/dataset_context.py
```

### 单元测试
- `test_dataset_upgrade.py`：新字段默认值、Panel/时序/横截面退化
- `test_materializer.py`：X/y 对齐、时序切分无泄漏、归一化可逆

### 验收
- Dataset 支持 panel/time_series/cross_section 三种类型
- Materializer 产出 TrainingDataset（X_train/y_train/X_test/y_test）
- 时序切分严格无未来信息泄漏

---

## 阶段 7：增量层（ChangeSet + DeltaAnalyzer + IncrementalPlanner + StateStore + Node 增量能力）

**目标**：增量计算成为默认执行模式。

### 任务
7.1 `research/incremental/changeset.py`：ChangeSet + Change + ChangeOp
7.2 `research/incremental/delta_analyzer.py`：DeltaAnalyzer → DirtyGraph
7.3 `research/incremental/planner.py`：IncrementalPlanner + 6 种 IncrementalStrategy
7.4 `research/incremental/state_store.py`：StateStore + NodeState（checkpoint）
7.5 ResearchNode 增量方法实现：update/save_state/load_state/invalidate/estimate_delta
   - 重点：EMA/SMA 等有状态节点、Rolling 窗口节点
7.6 Executor 集成：mode="incremental" 时委托 IncrementalPlanner 生成 dirty subgraph

### 产出文件
```
quantlab/research/incremental/{changeset,delta_analyzer,planner,state_store}.py
（修改）quantlab/research/node/base.py（增量方法实现）
（修改）quantlab/research/executor.py（增量模式集成）
```

### 单元测试 + 集成测试
- `test_changeset.py`：ChangeSet 构造
- `test_delta_analyzer.py`：脏范围识别
- `test_incremental_planner.py`：6 种策略选择
- 集成：追加 1 根 K 线 → 增量结果 == 全量结果（数值一致）

### 验收
- Node supports_incremental() 声明正确
- 增量执行比全量快 10x+（追加 1 根 K 线场景）
- 增量结果与全量结果一致（必过测试）

---

## 阶段 8：训练层（TrainingJob 改造 + feature_analysis/diagnostics/label 迁移）

**目标**：上层全迁移到 Graph 体系。

### 任务
8.1 修改 `ml/training/job.py`：TrainingJob 删除 feature_set_id/label_set_id/feature_ids/label_id，新增 research_graph_id/label_node_id/materialize_config；改用 Materializer
8.2 修改 `ml/feature_analysis/`：改读 Graph 产物 + MaterializedFeature
8.3 修改 `ml/diagnostics/`：feature/label 诊断改用 Node 元数据
8.4 修改 `ml/label/`：LabelNode 注册到 NodeRegistry（旧 LabelRegistry 转发）
8.5 创建 `ml/training/validation.py`：TrainingValidator（防泄漏校验）

### 产出文件
```
（修改）quantlab/ml/training/job.py
（修改）quantlab/ml/feature_analysis/*.py
（修改）quantlab/ml/diagnostics/*.py
（修改）quantlab/ml/label/*.py
quantlab/ml/training/validation.py
```

### 集成测试
- 端到端：Dataset → Graph → Executor → Materializer → TrainingJob → Model，用 BTC/ETH/SOL 真实短历史数据
- 回归：旧 TrainingJob 经兼容层与新流程输出一致

### 验收
- TrainingJob 完全基于 Graph + Materializer
- 端到端训练闭环可用
- 首次回测（BTCUSDT 2024-01~06）跑通

---

## 阶段 9：API 层（api/ml.py + api/factors.py 改造 + 兼容层）

**目标**：暴露新接口，旧接口转发。

### 任务
9.1 修改 `api/ml.py`：新增 Graph CRUD、Materializer、Incremental 执行接口；旧接口转发
9.2 修改 `api/factors.py`：改为 NodeRegistry 查询；旧 Factor 接口转发
9.3 新增 `api/research.py`：Research Graph 专属 API（compile/execute/invalidate/cache 查询）

### 产出文件
```
（修改）quantlab/api/ml.py
（修改）quantlab/api/factors.py
quantlab/api/research.py
```

### 集成测试
- API 端到端：创建 Graph → 编译 → 执行 → 查询缓存
- 兼容层：旧 /api/features 接口可用且输出一致

### 验收
- 新 API 完整覆盖 Research Graph 生命周期
- 旧 API 经兼容层可用

---

## 阶段 10：DB 层（迁移脚本 + 新表 + ALTER + 备份 + 回滚脚本）

**目标**：DB schema 变更 + 回滚保障。

### 任务
10.1 创建 `scripts/migrate_research_os.py`：一次性迁移脚本
   - 备份 `ml_lab.db` → `ml_lab.db.backup_<timestamp>`
   - 新建 7 张 research_* 表 + 2 张 universe/calendar 表
   - ALTER datasets 表（dataset_type/calendar_id/adjustment）
   - ALTER training_jobs 表（research_graph_id/label_node_id/materialize_config_json/materialized_dataset_id）
   - 重命名 feature_sets → feature_sets_deprecated、label_sets → label_sets_deprecated
10.2 创建 `scripts/restore_backup.py`：一键还原 DB
10.3 创建 `config/research.yaml`：Feature Flag（use_research_graph: true/false）

### 产出文件
```
scripts/migrate_research_os.py
scripts/restore_backup.py
config/research.yaml
```

### 测试
- 在副本 DB 上执行迁移脚本，验证表结构
- 执行回滚脚本，验证还原

### 验收
- 迁移脚本幂等可执行
- 旧数据不丢失（ALTER 增量、旧表重命名保留）
- 回滚脚本可一键还原

---

## 阶段 11：前端层（Research Graph Studio + 路由 + 旧页面 deprecated）

**目标**：Visual Quant Research IDE。

### 任务
11.1 安装依赖：`vue-flow`、`dagre`
11.2 创建 `frontend/src/views/research_graph/ResearchGraphStudio.vue`（IDE 主容器）
11.3 创建 panels：
   - `NodePalette.vue`（左侧 Node Library，从 NodeRegistry 拉 manifest）
   - `GraphCanvas.vue`（Vue Flow 画布，拖拽连线，自动布局）
   - `Inspector.vue`（右侧节点属性/端口/参数）
   - `PropertyPanel.vue`（图级属性）
   - `ExecutionView.vue` / `CacheView.vue` / `ValidationView.vue`（底部 Tab）
   - `ConsolePanel.vue`、`MiniMap.vue`、`DependencyView.vue`
11.4 创建 `api/researchGraph.ts`（前端 API 封装）
11.5 创建 `stores/researchGraph.ts`（Pinia store）
11.6 新增路由 `/research-graph`
11.7 修改 `views/ml_lab/panels/FeatureLab.vue`、`FeatureSets.vue`、`views/factors/FactorStudio.vue`：标记 deprecated + 引导跳转

### 产出文件
```
frontend/src/views/research_graph/ResearchGraphStudio.vue
frontend/src/views/research_graph/panels/*.vue (10 个面板)
frontend/src/views/research_graph/api/researchGraph.ts
frontend/src/views/research_graph/stores/researchGraph.ts
（修改）frontend/src/router/index.ts
（修改）frontend/src/views/ml_lab/panels/FeatureLab.vue, FeatureSets.vue
（修改）frontend/src/views/factors/FactorStudio.vue
```

### 测试
- 手动：建图 → 编译 → 执行 → 查看 Execution/Cache/Validation
- E2E（可选）：Playwright 跑通核心流程

### 验收
- 可视化建图、拖拽连线、自动布局
- 编译错误实时显示
- 执行进度可视化
- 旧页面引导跳转新 Studio

---

## 阶段 12：测试与验收（贯穿全过程 + 最终回归）

**目标**：完整测试覆盖 + 升级报告。

### 任务
12.1 单元测试补全：`tests/research/unit/` 全覆盖
12.2 集成测试：`tests/research/integration/`
   - 端到端训练闭环（BTC/ETH/SOL 真实短历史）
   - 增量一致性
   - Cache 命中/失效
12.3 性能测试：`tests/research/perf/`
   - Alpha101 全量耗时
   - 增量 vs 全量加速比
   - Cache 命中率
12.4 回归测试：`tests/research/regression/`
   - 旧 FeatureRegistry 接口 vs NodeRegistry 输出一致性
12.5 首次回测验证（项目规则2）：BTCUSDT 2024-01-01~2024-06-01 跑通完整训练
12.6 编写升级报告 `docs/plans/2026-06-26-research-os-upgrade-report.md`
   - 实现功能清单
   - 解决问题清单
   - 与文档要求符合程度（对照 spec 第十三节）
   - 系统运行验证结果

### 验收
- 所有单元测试通过
- 集成测试通过（含增量一致性必过）
- 性能达标（Alpha101 < 60s、增量 10x+、Cache 命中率 > 90%）
- 回归测试通过
- 升级报告完成

---

## 执行规则

1. **每阶段完成即测试**：阶段内单元测试全过才进入下一阶段
2. **DB 操作前必备份**：阶段 10 执行迁移脚本前 `cp ml_lab.db ml_lab.db.backup_<timestamp>`
3. **旧代码迁移保兼容**：旧入口转发到新实现，不直接删除
4. **首次回测用短历史**：BTCUSDT 2024-01-01~2024-06-01（项目规则2）
5. **每个 Node 迁移即回归测试**：新实现输出与旧实现数值一致
6. **遵循 AGENTS.md 规则**：中文回复、实事求是、最小单元测试、计划入 /docs/plans/

---

## 风险监控点

| 阶段 | 风险 | 监控 |
|------|------|------|
| 2 | Alpha191 数量大，迁移工作量大 | 分批迁移，每批回归测试 |
| 7 | 增量正确性难保证 | 增量 vs 全量一致性必过测试 |
| 8 | TrainingJob 改造影响面广 | 端到端集成测试 + 兼容层 |
| 10 | DB 变更不可逆 | 备份 + 回滚脚本 + 副本验证 |
| 11 | 前端 Vue Flow 复杂度 | 复用成熟方案 + 手动 E2E |

---

**本实施计划共 12 阶段，每阶段含明确产出、测试、验收。按依赖顺序推进，确保每步可独立验证。**
