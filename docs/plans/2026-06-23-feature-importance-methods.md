# Feature Importance 多方法支持 — 实施计划

## 根因

- 训练时 [job.py#L223](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py#L223) 永远只调用 `model.feature_importance()`（树模型内置 gain 方法）
- `from-job/{job_id}` 端点 [ml.py#L574-L608](file:///d:/python_workspace/quantlab/quantlab/api/ml.py#L574-L608) 硬编码返回 `gain`
- 前端 `runAnalysis` 不传 methods，训练对话框没方法选择

## 目标

训练时可选 `gain` / `permutation` / `shap`，训练结果中按方法分别存储，前端 Feature Importance 面板正确展示所有方法。

## 实施步骤

### Task 1: 后端数据模型扩展

- [ ] [quantlab/ml/training/job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py) — `TrainingJob` 加 `methods: List[str] = ["gain"]` 字段
- [ ] [quantlab/ml/training/job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py) — `to_dict()` 包含 `methods`
- [ ] [quantlab/ml/training/job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py) — `TrainingResult` 加 `feature_importance_by_method: Dict[str, Dict[str, float]]` 字段（按方法存）
- [ ] [quantlab/api/ml.py](file:///d:/python_workspace/quantlab/quantlab/api/ml.py) — `TrainRequest` 加 `methods: List[str] = ["gain"]` 字段
- [ ] [quantlab/api/ml.py](file:///d:/python_workspace/quantlab/quantlab/api/ml.py) — `submit_training` 把 `req.methods` 传给 `TrainingJob`

### Task 2: 后端训练逻辑改造

- [ ] [quantlab/ml/training/job.py](file:///d:/python_workspace/quantlab/quantlab/ml/training/job.py) — `run()` 中根据 `self.methods` 调用：
  - `gain` → `compute_gain_importance(model)`（已存在）
  - `permutation` → `compute_permutation_importance(model, X_test, y_test)`（已存在）
  - `shap` → `compute_shap_importance(model, X_test)`（待确认是否存在）
- [ ] 把每个方法的结果合并存到 `result.feature_importance_by_method[method] = {feature: importance}`
- [ ] 保留 `result.feature_importance` 字段为 `gain`（兼容老调用方）

### Task 3: 后端 from-job 端点改造

- [ ] [quantlab/api/ml.py](file:///d:/python_workspace/quantlab/quantlab/api/ml.py) — `feature_importance_from_job` 改为：
  - 从 `result.feature_importance_by_method` 读取
  - 按 `job.methods` 循环返回每个方法的 details
  - 兼容老数据：若 `feature_importance_by_method` 为空但 `feature_importance` 有数据，按 gain 返回

### Task 4: 前端训练对话框

- [ ] 找到训练弹窗组件（`TrainingCenter.vue` 或类似）
- [ ] 在 "模型 Model" 和 "训练比例 Train Ratio" 之间加 "方法 Methods" 多选框（`el-checkbox-group`）
- [ ] 默认勾选 `['gain']`（向后兼容）
- [ ] 提交时把 `methods` 加入请求体

### Task 5: 前端 Feature Importance 面板

- [ ] [frontend/src/views/ml_lab/panels/FeatureImportance.vue](file:///d:/python_workspace/quantlab/frontend/src/views/ml_lab/panels/FeatureImportance.vue) — `runAnalysis` 验证：
  - 提交请求时是否需要传 methods？（当前是从 job 加载，不传）
  - tabs 渲染用 `Object.keys(results)` 已支持多方法，确认无需改
- [ ] 训练对话框传 methods 后，前端 runAnalysis 显示会自动多 tabs（无需改前端 runAnalysis 本身）

### Task 6: 验证

- [ ] 单元测试：在 `/tests` 下新建 `test_feature_importance_methods.py`
  - 创建 mock dataset/feature_set/label_set
  - 提交训练请求，methods=['gain','permutation']
  - 验证 job.feature_importance_by_method 包含两种方法
  - 验证 from-job 端点返回 {gain: {...}, permutation: {...}}
- [ ] 端到端测试：浏览器训练 + 查看 Feature Importance
- [ ] 清理：删除 `/tests` 下测试代码（规则 5）

## 改动文件清单

- `quantlab/ml/training/job.py`（+30 行）
- `quantlab/api/ml.py`（+15 行）
- `frontend/src/views/ml_lab/panels/TrainingCenter.vue`（+20 行，若有该文件）
- 测试代码（临时）

## 风险

- 树模型（LightGBM/XGBoost/RF）支持 gain；线性模型没有内置 gain，需要从 coef_ 推导
- SHAP 需要 `shap` 库依赖，需确认环境是否安装
- 已有 job 的 `feature_importance` 字段结构不变（dict[str, float]），新字段并存

## 验收标准

- 训练对话框可勾选方法
- 训练后 Feature Importance 面板显示与训练时勾选一致数量的方法 tab
- 旧 job 数据不报错
