# Asset Registry 架构升级计划

## 背景

将 Model Registry 升级为 **Asset Registry（资产注册中心）**，统一管理所有量化资产：
Dataset / FeatureSet / LabelSet / ModelPackage / StrategyPackage / RiskProfile / DeploymentProfile。

核心理念：QuantLab 从「量化工具」升级为「量化资产管理系统（Quant Asset Operating System）」。

## 现状分析

### 已有资产（可复用）
- `quantlab/ml/registry/registry.py` — `ModelRegistry` + `ModelVersion`（Family + Lifecycle + Champion）
- `quantlab/ml/registry/model_store.py` — `ModelStore`（磁盘文件管理）
- `quantlab/ml/registry/lineage.py` — `ModelLineage`（血统图）
- `quantlab/ml/registry/champion.py` — `ChampionManager`（冠军挑战）
- `quantlab/ml/registry/package.py` — `ModelPackage` + `ModelManifest`
- `quantlab/ml/storage/` — `MLStore`（SQLite）+ `ParquetStore`
- `quantlab/ml/dataset/dataset.py` — `Dataset`
- `quantlab/ml/feature/set.py` — `FeatureSet`

### 缺失
- 统一的 `QuantAsset` 基类
- 统一的 `AssetRegistry` 入口
- `AssetStorage` 存储抽象（Registry/Storage 分离）
- `VersionManager`（SemVer 语义化版本）
- `LineageManager`（跨资产类型 DAG）
- `ChampionManager`（每 Family 一个 Champion，已部分存在但仅限 Model）

## 目标架构

```
                Asset Registry
================================================
Asset Base (QuantAsset)
────────────────────────────────
Dataset Registry
Feature Registry
Label Registry
Model Registry
Strategy Registry
Deployment Registry
────────────────────────────────
Version Manager
Artifact Store
Lineage Manager
Champion Manager
Dependency Manager
Storage Adapter
================================================
                Asset Explorer (UI)
```

## 设计原则

1. **Registry 是索引，不是存储**：Registry 只保存 `asset_id / location / hash / status`，真正数据放 Storage
2. **统一 Asset 基类**：所有资产继承 `QuantAsset`，拥有 `id / name / version / hash / created_at / author / tags / status`
3. **SemVer 语义化版本**：`Major.Minor.Patch`（FeatureSet 变更 → Major，参数调整 → Minor，Bug 修复 → Patch）
4. **Lineage DAG**：跨资产类型追溯（Dataset → FeatureSet → LabelSet → TrainingRun → ValidationRun → ModelPackage → StrategyPackage）
5. **Validation 门禁**：Registry 绝对不允许直接注册未验证的模型
6. **每 Family 一个 Champion**：`Momentum_LGBM` / `MeanReversion_RF` / `CrossSection_XGB` 各自独立

## 实施计划

### Phase 1: QuantAsset 基类 + AssetType 枚举
- 创建 `quantlab/asset/__init__.py`
- 创建 `quantlab/asset/base.py`：
  - `AssetType` 枚举：DATASET / FEATURE_SET / LABEL_SET / MODEL_PACKAGE / STRATEGY_PACKAGE / RISK_PROFILE / DEPLOYMENT_PROFILE
  - `AssetStatus` 枚举：DRAFT / ACTIVE / ARCHIVED / DEPRECATED
  - `QuantAsset` 抽象基类：id / name / version / hash / created_at / author / tags / status / asset_type
- **Checklist**：
  - [ ] AssetType 包含 7 种资产类型
  - [ ] QuantAsset 提供 `to_manifest()` / `compute_hash()` 抽象方法
  - [ ] 单元测试：实例化、序列化

### Phase 2: AssetStorage 存储层（Registry/Storage 分离）
- 创建 `quantlab/asset/storage.py`：
  - `AssetStorage` 类：统一存储接口
  - 目录结构：`storage/{datasets,features,labels,models,strategies,artifacts}/`
  - `save(asset_type, asset_id, data)` / `load(asset_type, asset_id)` / `exists()` / `delete()`
  - `get_location(asset_type, asset_id)` → 返回存储路径
- **设计**：Registry 调用 Storage 获取 location，不直接读写数据
- **Checklist**：
  - [ ] 7 种资产类型各有独立存储目录
  - [ ] save/load 往返测试
  - [ ] location 查询正确

### Phase 3: VersionManager（SemVer 语义化版本）
- 创建 `quantlab/asset/version.py`：
  - `SemanticVersion` 类：major / minor / patch
  - `bump_major()` / `bump_minor()` / `bump_patch()`
  - `compare(v1, v2)` / `parse("1.2.0")` / `__str__`
  - 版本规则：
    - FeatureSet 改变 → Major
    - 参数调整 → Minor
    - Bug 修复 → Patch
- **Checklist**：
  - [ ] SemVer 解析、比较、递增
  - [ ] Family 下版本唯一性检查

### Phase 4: LineageManager（DAG 血缘追溯）
- 创建 `quantlab/asset/lineage.py`：
  - `LineageNode`：asset_id / asset_type / name / version
  - `LineageEdge`：from_asset / to_asset / relation_type
  - `LineageGraph`：DAG 图
  - `add_edge(parent, child, relation)` / `get_ancestors(asset_id)` / `get_descendants(asset_id)` / `get_path(from, to)`
  - 跨资产类型：Dataset → FeatureSet → LabelSet → ModelPackage → StrategyPackage
- **Checklist**：
  - [ ] DAG 添加边、查询祖先/后代
  - [ ] 环检测
  - [ ] 路径查询

### Phase 5: ChampionManager（每 Family 一个 Champion）
- 创建 `quantlab/asset/champion.py`：
  - `ChampionPointer`：family → asset_id（每 Family 一个 Champion）
  - `promote(family, asset_id)` / `get_champion(family)` / `get_all_champions()`
  - 集成 Validation Pipeline：只有 VALIDATED 状态的资产才能成为 Candidate
  - 集成 Challenge 模块：Candidate 挑战 Champion
- **Checklist**：
  - [ ] 多 Family 独立 Champion
  - [ ] Promote 时旧 Champion 自动 ARCHIVED
  - [ ] 与 Challenge 模块集成

### Phase 6: AssetRegistry 统一入口 + ModelRegistry 迁移
- 创建 `quantlab/asset/registry.py`：
  - `AssetRegistry`：统一入口
  - `register(asset)` / `get(asset_id)` / `list(asset_type)` / `search()`
  - `get_champion(family)` / `set_champion(family, asset_id)`
  - `get_lineage(asset_id)` / `add_lineage(parent, child)`
  - 内部组合：VersionManager + LineageManager + ChampionManager + AssetStorage
- 创建 `quantlab/asset/adapters/model_adapter.py`：
  - `ModelAssetAdapter`：将现有 `ModelPackage` 适配为 `QuantAsset`
  - 保持向后兼容：`get_model_registry()` 仍可用
- **Checklist**：
  - [ ] AssetRegistry 统一注册/查询
  - [ ] ModelPackage 适配为 QuantAsset
  - [ ] 向后兼容现有 ModelRegistry API

### Phase 7: 后端 API 端点
- 在 `quantlab/api/` 新增 `asset.py`：
  - `GET /api/v1/asset/list?type=MODEL_PACKAGE`
  - `GET /api/v1/asset/{asset_id}`
  - `GET /api/v1/asset/{asset_id}/manifest`
  - `GET /api/v1/asset/{asset_id}/lineage`
  - `GET /api/v1/asset/champions`
  - `GET /api/v1/asset/{asset_id}/artifacts`
- **Checklist**：
  - [ ] 6 个端点注册
  - [ ] TestClient 冒烟测试

### Phase 8: 前端 Asset Explorer UI
- 创建 `frontend/src/views/ml_lab/panels/AssetExplorer.vue`：
  - 左侧：资产树（Datasets / Features / Labels / Models / Strategies）
  - 右侧：Manifest / Validation / Metrics / Artifacts / Dependencies / Lineage
- 在 `MLLab.vue` 添加 Asset Explorer 入口
- **Checklist**：
  - [ ] 资产树展示
  - [ ] 资产详情面板
  - [ ] Lineage 可视化

### Phase 9: 端到端测试
- 创建 `tests/test_asset_registry_e2e.py`：
  - QuantAsset 实例化
  - AssetStorage 往返
  - SemVer 版本管理
  - Lineage DAG
  - Champion 多 Family
  - AssetRegistry 统一入口
  - ModelPackage 适配
  - API 路由
- **Checklist**：
  - [ ] 10+ 测试全部通过
  - [ ] 向后兼容性验证

## 关键约束

1. **向后兼容**：现有 `ModelRegistry` / `ModelStore` / `ModelPackage` API 保持可用
2. **不破坏数据库**：现有 SQLite/Parquet 数据不迁移，新增 Asset 层在其之上
3. **Validation 门禁**：AssetRegistry.register() 对 MODEL_PACKAGE 类型强制检查 VALIDATED 状态
4. **不创建模拟数据**：所有测试使用合成数据，不写入数据库

## 实施顺序

Phase 1 → 2 → 3 → 4 → 5 → 6 → 7 → 9 → 8

Phase 1-6 为核心后端，Phase 7 为 API，Phase 9 为测试，Phase 8 为前端。
