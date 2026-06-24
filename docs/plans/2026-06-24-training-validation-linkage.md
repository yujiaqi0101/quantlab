# Training → Validation 链路打通计划：从 Experiment 到 Raw Model

> 计划日期：2026-06-24
> 状态：待确认
> 范围：Training Center 产出持久化 + Validation Pipeline 消费 Experiment

---

## 一、问题诊断

### 1.1 当前 Training Center 的产出

[job.py:246-274](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py#L246-L274) 训练完成后产出三样东西：

| 产出 | 存储位置 | 性质 |
|------|---------|------|
| TrainingResult | 内存（`TrainingManager._results`） | 临时对象，进程重启即失 |
| Experiment | SQLite `experiments` 表 | 持久化，可追溯 |
| model 对象 | `result.model`（内存） | **未持久化**，重启即失 |

### 1.2 Experiment 表的现状

[experiment/__init__.py:42-90](file:///d:/python_workspace/quantlab/quantlab/ml/experiment/__init__.py#L42-L90) Experiment 表已有 `model_version_id` 字段，但：

- **当前一直是空的**——TrainingJob.run() 从不写入这个字段
- **没有保存训练好的模型本身**——只存了 metrics/feature_importance 等元信息
- **没有经过任何质量验证**——IC 高不代表能上线

### 1.3 Validation Pipeline 的断层

[ml.py:1658-1742](file:///d:/python_workspace/quantlab/quantlab/api/ml.py#L1658-L1742) `run_validation_pipeline` 虽然接收 `dataset_id`/`feature_ids`/`label_id` 等字段，但：

- **没有实现从数据库加载数据的逻辑**——这些字段只作为元信息存进 ValidationContext
- **强制要求前端传 feature_data/label_data**——`if not req.feature_data: raise HTTPException(400)`
- **绕过了 Training Center**——用户得自己重新准备数据，丢失 Experiment 上下文

### 1.4 前端 ValidationCenter 的缺陷

[ValidationCenter.vue:34-55](file:///d:/python_workspace/quantlab/frontend/src/views/ml_lab/panels/ValidationCenter.vue#L34-L55) Run Pipeline tab 让用户手动粘贴 JSON：

```
特征数据: textarea → {"f1": [1,2,3], "f2": [4,5,6]}
标签数据: textarea → [0.1, 0.2, 0.3]
```

没有 Dataset/Feature/Label 下拉选择，也没有 Experiment 选择。

---

## 二、设计目标

### 2.1 核心原则

**Training Center 的产出 = Raw Model（未验证的裸模型）+ Experiment（训练记录）**

Validation Pipeline 的输入应该是 **Experiment ID**，而不是用户手动粘贴的原始数据。

### 2.2 目标架构

```
Training Center
  ├─ 训练完成
  ├─ 持久化 Raw Model（model.pkl + metadata.json，状态=DRAFT）
  ├─ Experiment.model_version_id = MV-xxx（关联持久化的 Raw Model）
  └─ Experiment 持久化到 SQLite
        ↓
Validation Pipeline
  ├─ 输入：experiment_id
  ├─ 后端从 Experiment 加载：
  │   ├─ model_version_id → ModelStore.load() → Raw Model
  │   ├─ dataset_id + feature_set_id + label_set_id → MLPipeline.build() → TrainingDataset
  │   └─ model_params / metrics → ValidationContext.training_result
  ├─ 构建 ValidationContext
  └─ 跑 6 级 Gate
        ↓
  PASS → ModelStore 状态升级 DRAFT → CANDIDATE → Registry
  FAIL → 保留 DRAFT，标记验证失败
```

### 2.3 关键设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| Raw Model 存哪里 | 复用 ModelStore（`storage/models/<family>/v<n>/`） | 已有 model.pkl 持久化能力，不重复造轮子 |
| Raw Model 进 Registry 吗 | **不进**，状态标记为 DRAFT | Raw Model 是"未验证的"，只有 PASS 后才升级为 CANDIDATE |
| 数据如何重建 | 复用 `MLPipeline.build(dataset_id, feature_set_id, label_set_id)` | 已有逻辑，保证数据可重现 |
| 模型如何加载 | `ModelStore.load(version_id)` | 已有接口 |
| Experiment 如何关联 | 复用 `Experiment.model_version_id` 字段 | 字段已存在，无需改表结构 |
| 数据库结构变更 | **无** | 复用现有 experiments 表 + ModelStore 文件系统 |

---

## 三、Tasks List

### Phase 1：后端 — Training Center 产出 Raw Model

#### Task 1.1：TrainingJob.run() 训练完成后持久化 Raw Model
- [ ] 训练成功后，调用 `ModelStore.save()` 持久化 model.pkl + metadata.json
- [ ] ModelVersion 状态设为 `LifecycleStatus.DRAFT`（未验证）
- [ ] family 命名规则：`{model_type}_{experiment_name}`（如 `LGBM_momentum_v1`）
- [ ] version_number 自动递增（同 family 下）
- [ ] 把 `model_version_id` 写入 Experiment 记录

**修改文件**：[job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py)

**关键代码位置**：[job.py:246-274](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py#L246-L274) `result.model = model` 之后

#### Task 1.2：TrainingResult 增加 model_version_id 字段
- [ ] TrainingResult 新增 `model_version_id: str = ""` 字段
- [ ] `to_dict()` 输出该字段
- [ ] 前端 TrainingCenter 列表展示 model_version_id

**修改文件**：[job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py)（TrainingResult dataclass）

#### Task 1.3：Experiment 持久化 model_version_id
- [ ] TrainingJob.run() 保存 Experiment 时，填入 `model_version_id`
- [ ] 验证 ExperimentTracker.save() 是否已支持该字段（应已支持，字段已存在）

**修改文件**：[job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py)（Experiment 构造处）

---

### Phase 2：后端 — Validation Pipeline 消费 Experiment

#### Task 2.1：新增从 Experiment 构建 ValidationContext 的函数
- [ ] 新增 `build_context_from_experiment(experiment_id: str) -> ValidationContext`
- [ ] 逻辑：
  1. 从 ExperimentTracker 加载 Experiment
  2. 从 `experiment.model_version_id` 调用 `ModelStore.load()` 加载 Raw Model
  3. 从 `experiment.dataset_id + feature_set_id + label_set_id` 调用 `MLPipeline.build()` 重建 TrainingDataset
  4. 用 Raw Model 对 features 做预测，得到 predictions
  5. 组装 ValidationContext（raw_model + features + labels + predictions + training_result）

**新增位置**：[validation/pipeline/core.py](file:///d:/python_workspace/quantlab/quantlab/ml/validation/pipeline/core.py) 或新建 `validation/pipeline/loader.py`

#### Task 2.2：ValidationPipelineRequest 支持 experiment_id 入口
- [ ] `ValidationPipelineRequest` 新增 `experiment_id: str = ""` 字段
- [ ] `run_validation_pipeline` 端点逻辑：
  - 如果 `experiment_id` 非空 → 调用 `build_context_from_experiment()`
  - 如果 `feature_data` 非空 → 走原有逻辑（保留手动输入作为高级模式）
  - 两者都空 → 报错

**修改文件**：[ml.py](file:///d:/python_workspace/quantlab/quantlab/api/ml.py)（[1658-1742](file:///d:/python_workspace/quantlab/quantlab/api/ml.py#L1658-L1742)）

#### Task 2.3：Validation 通过后升级 Raw Model 状态
- [ ] Pipeline PASS 后，调用 `ModelStore` 把 Raw Model 状态从 DRAFT 升级为 CANDIDATE
- [ ] 写入 validation 结果到 ModelStore 的 metadata.json
- [ ] （可选）自动注册到 ModelRegistry

**修改文件**：[ml.py](file:///d:/python_workspace/quantlab/quantlab/api/ml.py)（run_validation_pipeline 末尾）

---

### Phase 3：前端 — ValidationCenter 改为选择 Experiment

#### Task 3.1：Run Pipeline tab 改为 Experiment 选择模式
- [ ] 移除 textarea 手动输入（改为"高级模式"折叠面板，默认收起）
- [ ] 新增 Experiment 下拉选择（调用 `getExperiments()` API）
- [ ] 选中 Experiment 后展示：dataset / feature_set / label_set / model_type / metrics 摘要
- [ ] 保留 Walk Forward 配置 + stop_on_fail 开关
- [ ] 运行按钮调用 `runValidationPipeline({ experiment_id })`

**修改文件**：[ValidationCenter.vue](file:///d:/python_workspace/quantlab/frontend/src/views/ml_lab/panels/ValidationCenter.vue)

#### Task 3.2：API 接口适配
- [ ] `runValidationPipeline` 的 data 类型新增 `experiment_id?: string`
- [ ] 新增 `getExperiments()` 已存在，直接复用

**修改文件**：[ml.ts](file:///d:/python_workspace/quantlab/frontend/src/api/ml.ts)（[777-801](file:///d:/python_workspace/quantlab/frontend/src/api/ml.ts#L777-L801)）

#### Task 3.3：TrainingCenter 展示 model_version_id
- [ ] 训练任务列表新增 "Raw Model" 列，展示 model_version_id
- [ ] 点击可跳转到 ValidationCenter 并自动选中该 Experiment

**修改文件**：[TrainingCenter.vue](file:///d:/python_workspace/quantlab/frontend/src/views/ml_lab/panels/TrainingCenter.vue)

---

### Phase 4：测试

#### Task 4.1：后端单元测试
- [ ] `tests/test_training_persistence.py` — 训练完成后验证 model.pkl 存在、Experiment.model_version_id 非空
- [ ] `tests/test_validation_from_experiment.py` — 从 experiment_id 构建 ValidationContext 并跑通 Pipeline
- [ ] `tests/test_validation_state_upgrade.py` — Pipeline PASS 后 Raw Model 状态升级为 CANDIDATE

**测试脚本位置**：`tests/`（按 AGENTS.md 规则6.1，临时验证脚本放 tests/，修复后清除；正式测试保留）

#### Task 4.2：端到端测试
- [ ] Training → Validation → Registry 完整链路打通
- [ ] 使用较短历史数据回测（按 AGENTS.md 规则2）

---

## 四、Checklist

### 后端
- [ ] TrainingJob.run() 训练完成后调用 ModelStore.save() 持久化 Raw Model
- [ ] Raw Model 状态 = LifecycleStatus.DRAFT
- [ ] Experiment.model_version_id 正确写入
- [ ] TrainingResult.model_version_id 字段新增并输出
- [ ] `build_context_from_experiment()` 函数实现
- [ ] `run_validation_pipeline` 端点支持 experiment_id 入口
- [ ] Pipeline PASS 后 Raw Model 状态升级 DRAFT → CANDIDATE
- [ ] 后端单元测试通过

### 前端
- [ ] ValidationCenter Run Pipeline tab 改为 Experiment 选择模式
- [ ] 保留手动输入作为"高级模式"折叠面板
- [ ] Experiment 下拉选择 + 摘要展示
- [ ] TrainingCenter 列表展示 model_version_id
- [ ] TrainingCenter → ValidationCenter 跳转联动

### 数据库结构一致性（AGENTS.md 规则5）
- [ ] experiments 表结构 **无变更**（model_version_id 字段已存在）
- [ ] ModelStore 文件系统结构 **无变更**（复用 storage/models/<family>/v<n>/）
- [ ] LifecycleStatus 已有 DRAFT 状态 **无需新增**

### 集成
- [ ] Training → Validation 流程打通（通过 experiment_id）
- [ ] Validation PASS → Registry 流程打通（状态升级）
- [ ] 端到端测试通过

---

## 五、实施顺序

1. **Phase 1**（Training 持久化 Raw Model）— 最高优先级，是后续一切的基础
2. **Phase 2**（Validation 消费 Experiment）— 依赖 Phase 1
3. **Phase 3**（前端适配）— 依赖 Phase 2
4. **Phase 4**（测试）— 每个 Phase 完成后立即做

---

## 六、复用策略（避免重写）

| 新功能 | 复用已有代码 |
|--------|-------------|
| Raw Model 持久化 | `ModelStore.save()` / `ModelStore.load()` |
| TrainingDataset 重建 | `MLPipeline.build(dataset_id, feature_set_id, label_set_id)` |
| Experiment 加载 | `ExperimentTracker.get(experiment_id)` |
| DRAFT 状态 | `LifecycleStatus.DRAFT`（已存在） |
| Experiment 字段 | `Experiment.model_version_id`（已存在） |
| 前端 Experiment 列表 | `getExperiments()` API（已存在） |

---

## 七、风险与约束

1. **不破坏现有 API**：`run_validation_pipeline` 保留 `feature_data` 入口作为高级模式，新增 `experiment_id` 入口
2. **不重写算法**：复用 ModelStore / MLPipeline / ExperimentTracker
3. **数据库不变**：复用现有 SQLite 表结构，不新增表，不改字段
4. **向后兼容**：已有的手动粘贴 JSON 模式保留（折叠为"高级模式"）
5. **Raw Model 不进 Registry**：只有 Validation PASS 后才升级状态，避免污染 Registry

---

## 八、已确认决策

1. **Raw Model 的 family 命名规则**：`{model_type}_{experiment_name}`（如 `LGBM_momentum_v1`）— 已确认
2. **Validation PASS 后自动注册到 ModelRegistry** — 已确认，Pipeline PASS 后自动升级状态并注册
3. **Validation FAIL 的 Raw Model 保留** — 已确认，保留 Raw Model 但标记为 FAIL 状态（不删除）
