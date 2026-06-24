# 资产管理系统完整接入计划

**日期**: 2026-06-24
**目标**: 将 ML Lab 的所有产物（Dataset / FeatureSet / LabelSet / Model / Strategy）自动注册到 AssetRegistry，并建立完整的血缘链路，让 Asset Explorer 界面有数据可看。

---

## 一、现状诊断

### 1.1 Asset 系统已就绪
- `quantlab/asset/` 模块完整：AssetRegistry + AssetStorage + VersionManager + LineageManager + ChampionManager
- API 层完整：`/api/v1/asset/*` 提供注册、查询、血缘、Champion 全套接口
- 前端 AssetExplorer.vue 完整：摘要卡片 + 资产树 + 详情(Manifest/Validation/Metrics/Lineage) + Champions 面板
- 资产类型已定义：DatasetAsset / FeatureSetAsset / LabelSetAsset / ModelPackageAsset / StrategyPackageAsset

### 1.2 问题：没有数据源接入
| 模块 | 创建入口 | 是否注册到 AssetRegistry |
|------|---------|------------------------|
| Dataset | `DatasetManager.create_dataset()` | ❌ 未注册 |
| FeatureSet | `FeatureSetRegistry.register()` | ❌ 未注册 |
| LabelSet | `LabelSetRegistry.register()` | ❌ 未注册 |
| Model | `_upgrade_raw_model_status()` (Validation PASS) | ❌ 只注册到 ModelRegistry，未注册到 AssetRegistry |
| Strategy | `MLStrategyBuilder.build()` | ❌ 未注册 |

### 1.3 问题：AssetRegistry 重启后索引丢失
- `AssetStorage` 会把 manifest 持久化到文件系统（`storage/assets/<type>/<family>/<asset_id>/manifest.json`）
- 但 `AssetRegistry._assets` 是内存索引，**重启后不会从文件系统恢复**
- 导致即使注册过资产，重启后界面仍然为空

### 1.4 问题：血缘关系未建立
- 各模块创建时没有调用 `reg.add_lineage()` 建立上下游关系
- Asset Explorer 的 Lineage tab 永远为空

---

## 二、设计目标

### 2.1 完整血缘链路
```
Dataset (数据集)
  │ DERIVED_FROM
  ├── FeatureSet (特征集)
  │     │ TRAINED_ON
  │     └── Model (模型)
  │           │ PACKAGED_FROM
  │           └── Strategy (策略)
  └── LabelSet (标签集)
        │ TRAINED_ON
        └── Model (模型) ← 同上
```

### 2.2 自动注册原则
- **创建即注册**：每个产物创建时自动注册到 AssetRegistry
- **幂等性**：重复注册相同内容不会创建新资产（通过 hash 去重）
- **不破坏现有流程**：资产注册失败不应阻断主流程（try-except 容错）

### 2.3 持久化原则
- AssetRegistry 启动时从文件系统恢复索引
- 注册时同步写入文件系统（已有）
- 血缘关系也要持久化

---

## 三、Tasks List

### Phase 1: AssetRegistry 持久化恢复（基础设施）

**目标**：解决重启后索引丢失问题

- [ ] **Task 1.1**: AssetRegistry 新增 `_load_from_storage()` 方法
  - 启动时扫描 `storage/assets/` 目录
  - 读取所有 manifest.json，重建内存索引
  - 重建 VersionManager / LineageManager / ChampionManager 状态
- [ ] **Task 1.2**: LineageManager 持久化
  - 血缘关系保存到 `storage/assets/_lineage/lineage.json`
  - 启动时加载
- [ ] **Task 1.3**: ChampionManager 持久化
  - Champion 指针保存到 `storage/assets/_champions/champions.json`
  - 启动时加载
- [ ] **Task 1.4**: 测试重启恢复
  - 注册资产 → 重启 Registry → 确认索引恢复

### Phase 2: Dataset 自动注册

**目标**：Dataset 创建时自动注册为 DATASET 资产

- [ ] **Task 2.1**: 新增 `register_dataset_asset(ds: Dataset)` 辅助函数
  - 位置：`quantlab/asset/auto_register.py`（新建）
  - 将 Dataset 转为 DatasetAsset 并注册
  - try-except 容错，失败只记日志不阻断
- [ ] **Task 2.2**: 在 `DatasetManager.create_dataset()` 末尾调用自动注册
- [ ] **Task 2.3**: 数据加载后更新资产（n_rows / n_cols / date_range）
  - 在 `DatasetManager.load_csv()` / `load_parquet()` 成功后更新
- [ ] **Task 2.4**: 测试 Dataset 自动注册

### Phase 3: FeatureSet 自动注册 + 血缘

**目标**：FeatureSet 创建时注册 + 建立到 Dataset 的血缘

- [ ] **Task 3.1**: 新增 `register_feature_set_asset(fs: FeatureSet, dataset_id: str)` 辅助函数
- [ ] **Task 3.2**: 在 `FeatureSetRegistry.register()` 末尾调用自动注册
  - 注意：FeatureSet 需要关联的 dataset_id（从创建上下文获取）
- [ ] **Task 3.3**: 建立 FeatureSet → Dataset 的 DERIVED_FROM 血缘
- [ ] **Task 3.4**: 测试 FeatureSet 自动注册 + 血缘

### Phase 4: LabelSet 自动注册 + 血缘

**目标**：LabelSet 创建时注册 + 建立到 Dataset 的血缘

- [ ] **Task 4.1**: 新增 `register_label_set_asset(ls: LabelSet, dataset_id: str)` 辅助函数
- [ ] **Task 4.2**: 在 `LabelSetRegistry.register()` 末尾调用自动注册
- [ ] **Task 4.3**: 建立 LabelSet → Dataset 的 DERIVED_FROM 血缘
- [ ] **Task 4.4**: 测试 LabelSet 自动注册 + 血缘

### Phase 5: Model 自动注册 + 血缘

**目标**：Validation PASS 后注册 ModelPackage + 建立到 FeatureSet/LabelSet/Dataset 的血缘

- [ ] **Task 5.1**: 修改 `_upgrade_raw_model_status()`，PASS 时额外注册到 AssetRegistry
  - 将 ModelVersion 转为 ModelPackageAsset
  - validation_passed=True, validation_score, validation_grade
- [ ] **Task 5.2**: 建立 Model → FeatureSet 的 TRAINED_ON 血缘
- [ ] **Task 5.3**: 建立 Model → LabelSet 的 TRAINED_ON 血缘
- [ ] **Task 5.4**: 建立 Model → Dataset 的 TRAINED_ON 血缘
- [ ] **Task 5.5**: 测试 Model 自动注册 + 血缘

### Phase 6: Strategy 自动注册 + 血缘

**目标**：Strategy 构建时注册 + 建立到 Model 的血缘

- [ ] **Task 6.1**: 新增 `register_strategy_asset(strategy, model_asset_id)` 辅助函数
- [ ] **Task 6.2**: 在 `MLStrategyBuilder.build()` 末尾调用自动注册
- [ ] **Task 6.3**: 建立 Strategy → Model 的 PACKAGED_FROM 血缘
- [ ] **Task 6.4**: 测试 Strategy 自动注册 + 血缘

### Phase 7: 端到端测试 + Champion 晋升

**目标**：完整链路验证 + Champion 功能

- [ ] **Task 7.1**: 端到端测试：创建 Dataset → FeatureSet → 训练 → Validation PASS → 注册 Model → 构建 Strategy
  - 验证 Asset Explorer 能看到所有资产
  - 验证血缘链完整：Dataset → FeatureSet → Model → Strategy
- [ ] **Task 7.2**: Champion 晋升测试
  - 同一 Family 训练多个版本
  - 手动设置 Champion
  - 验证 Asset Explorer 显示 Champion ★

---

## 四、Checklist

### 数据库结构一致性（AGENTS.md 规则5）
- [ ] AssetRegistry 持久化使用文件系统（manifest.json），不涉及数据库表结构变更
- [ ] LineageManager / ChampionManager 新增 JSON 持久化文件，不影响现有数据库

### 代码质量
- [ ] 所有自动注册使用 try-except 容错，失败不阻断主流程
- [ ] 幂等性：重复注册相同内容（相同 hash）不创建新资产
- [ ] 日志清晰：每次注册/建立血缘都记录日志

### 测试覆盖
- [ ] Phase 1: 重启恢复测试
- [ ] Phase 2-6: 每个模块的自动注册 + 血缘测试
- [ ] Phase 7: 端到端完整链路测试

### 不破坏现有功能
- [ ] Dataset / FeatureSet / LabelSet 创建流程不变
- [ ] Training → Validation → ModelRegistry 链路不变
- [ ] Strategy 构建流程不变

---

## 五、技术方案

### 5.1 新建文件：`quantlab/asset/auto_register.py`
统一管理所有自动注册逻辑，避免散落在各模块：
```python
def register_dataset_asset(ds: Dataset) -> Optional[str]
def register_feature_set_asset(fs: FeatureSet, dataset_id: str) -> Optional[str]
def register_label_set_asset(ls: LabelSet, dataset_id: str) -> Optional[str]
def register_model_asset(version: ModelVersion, result: PipelineResult) -> Optional[str]
def register_strategy_asset(strategy, model_asset_id: str) -> Optional[str]
```

### 5.2 AssetRegistry 恢复逻辑
```python
def _load_from_storage(self):
    """启动时从文件系统恢复索引"""
    manifests = self.storage.list_all()
    for manifest in manifests:
        asset = self._manifest_to_asset(manifest)
        if asset:
            self._assets[asset.asset_id] = asset
            # 重建 version / lineage / champion
```

### 5.3 幂等性设计
- 注册前先按 hash 查找已有资产
- 如果 hash 匹配，返回已有 asset_id，不创建新资产
- 避免重复注册产生重复资产

### 5.4 血缘关系持久化
- LineageManager 的 edges 保存到 `storage/assets/_lineage/lineage.json`
- ChampionManager 的 pointers 保存到 `storage/assets/_champions/champions.json`
- 启动时加载这两个文件恢复状态

---

## 六、风险与注意事项

1. **性能**：自动注册会增加少量开销（hash 计算 + 文件写入），但可接受
2. **向后兼容**：旧数据（已存在的 Dataset/FeatureSet）不会自动注册，需要手动触发或重新创建
3. **Strategy 模块**：当前 Strategy 构建流程较复杂，需确认 model_asset_id 的获取方式
4. **FeatureSet 的 dataset_id**：FeatureSet 创建时不一定知道关联的 dataset_id，需要从上下文传入或后续补充
