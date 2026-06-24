# Model Arena 集成到 Training Center — 设计文档

## 背景

当前 Model Arena 位于 Stage 6「Model Registry」下，与训练流程割裂。用户实际使用流程是：先横评选模型 → 再正式训练。Arena 应前移到训练阶段作为"选模型"步骤。

## 目标

- 将 Model Arena 从 Stage 6 移到 Stage 4 Training Center 下，作为训练前的选型工具
- Arena 排行榜每行加「用此模型训练」按钮，一键跳转到 Training Jobs tab 并全量预填充表单
- TrainingCenter 表单支持两种模式：特征集模式（与 Arena 一致）和单个特征模式（原有）

## 设计

### 1. 后端改造（quantlab/api/ml.py）

`TrainRequest` 加两个字段：
```python
feature_set_id: str = ""
label_set_id: str = ""
```
`submit_training` 把它们传给 `TrainingJob`（TrainingJob 已支持模式2，无需改 job.py）。

### 2. 前端 Tab 结构（MLLab.vue）

- Stage 4 Training Center 下新增「模型横评 Model Arena」tab，排最前
- 移除 Stage 6 Model Registry 下的 Arena tab
- `import ModelArena` 从 Stage 6 移到 Stage 4
- `watch(store.prefill.ready)`，true 时 `activeSubTab = 'training'`

### 3. 新建 Pinia store（stores/mlTraining.ts）

```ts
prefill = { dataset_id, feature_set_id, label_set_id, model_type, ready }
setPrefill(data)  // Arena 调用
consume()          // TrainingCenter 消费后重置 ready
```

### 4. ModelArena.vue 改造

排行榜每行加「用此模型训练」按钮：
- 点击 → `store.setPrefill({ dataset_id, feature_set_id, label_set_id, model_type: row.model_type })`

### 5. TrainingCenter.vue 改造（核心）

表单加模式切换 radio：
```
模式: ( ) 特征集 FeatureSet（推荐）  ( ) 单个特征 Features
```
- 选「特征集」→ 显示 FeatureSet/LabelSet 选择器（和 Arena 一致）
- 选「单个特征」→ 显示原有 feature_ids/label_id 选择器
- `watch(store.prefill.ready)` → 填充表单 + 切到集合模式 + 打开训练对话框 + `consume()`

### 数据流

```
Arena 横评 → 点击「用此模型训练」
  → store.setPrefill({dataset_id, feature_set_id, label_set_id, model_type})
  → MLLab watch ready → 切到 training tab
  → TrainingCenter watch ready → 填充表单 + 打开对话框
  → 用户确认 → 正式训练（保存到 Experiment + ModelStore）
```

## 改动文件清单

- `quantlab/api/ml.py`（+2 行 TrainRequest 字段，+2 行传参）
- `frontend/src/stores/mlTraining.ts`（新建，~30 行）
- `frontend/src/views/ml_lab/MLLab.vue`（tab 调整 + watch 跳转）
- `frontend/src/views/ml_lab/panels/ModelArena.vue`（加按钮）
- `frontend/src/views/ml_lab/panels/TrainingCenter.vue`（模式切换 + 预填充）

## 验收标准

- Stage 4 Training Center 下第一个 tab 是「模型横评 Model Arena」
- Stage 6 Model Registry 下不再有 Arena tab
- Arena 排行榜每行有「用此模型训练」按钮
- 点击按钮后自动切到 Training Jobs tab，训练对话框打开，dataset/feature_set/label_set/model_type 已填充
- TrainingCenter 支持特征集和单个特征两种模式切换
- 前端构建无错
