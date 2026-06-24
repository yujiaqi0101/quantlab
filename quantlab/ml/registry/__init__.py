"""
Model Registry — 模型注册中心

ML Lab：
  M4：模型注册中心 + 完整生命周期管理
  M6：Model Package 架构（模型 = 可持续进化的资产）

  M4 模块：
    第一部分：ModelRegistry          — Family 概念 + Champion 管理
    第二部分：ModelVersion            — lifecycle 状态 + lineage 字段
    第三部分：ModelStore              — 磁盘文件管理
    第四部分：ModelLineage            — 血统图
    第五部分：ChampionManager         — Champion/Challenger 自动 promote
    第六部分：ModelComparator         — 跨版本对比
    第七部分：LifecycleManager        — 状态机
    第八部分：ModelAuditLog           — 操作审计

  M6 新增模块：
    ModelPackage             — 完整模型包（manifest + model + snapshot + artifacts）
    ModelManifest            — 模型清单（manifest.yaml）
    FeatureSetSnapshot       — 特征定义快照
    LabelSetSnapshot         — 标签定义快照
    SnapshotManager          — 快照管理（捕获 + 验证）
    ArtifactStore            — 产物存储（importance/shap/walkforward）
    ChampionPointer          — 冠军指针（pointer.yaml，runtime load_champion）
    ModelPackageBuilder       — TrainingResult → ModelPackage
    .qlmodel 导入/导出        — zip 包格式，可分享/备份/部署
"""

from .registry import (
    ModelVersion, ModelRegistry, LifecycleStatus,
    get_model_registry,
)
from .model_store import (
    ModelStore, get_model_store, DEFAULT_MODELS_DIR,
)
from .lifecycle import (
    LifecycleManager, LifecycleEvent, VALID_TRANSITIONS,
)
from .lineage import (
    ModelLineage, LineageNode, LineageChange,
)
from .champion import (
    ChampionManager, ChampionResult,
)
from .model_compare import (
    ModelComparator, ComparisonRow, ComparisonReport,
)
from .audit import (
    ModelAuditLog, AuditEntry, AuditAction,
    get_audit_log,
)

# M6 新增：Model Package 架构
from .package import (
    ModelPackage, ModelManifest,
    FeatureSetSnapshot, LabelSetSnapshot,
    MANIFEST_FILE, MODEL_FILE, METRICS_FILE, VALIDATION_FILE,
    TRAINING_FILE, LINEAGE_FILE, SNAPSHOT_DIR, ARTIFACTS_DIR,
    QLMODEL_EXTENSION,
)
from .snapshot import (
    SnapshotManager, get_snapshot_manager,
)
from .artifacts import (
    ArtifactStore,
)
from .champion_pointer import (
    ChampionPointer, ChampionHistoryEntry,
)
from .builder import (
    ModelPackageBuilder, get_package_builder,
)
from .qlmodel import (
    export_package, export_from_store,
    import_package, import_to_registry,
)

__all__ = [
    # M4 第一/二部分：Registry + Version
    "ModelVersion",
    "ModelRegistry",
    "LifecycleStatus",
    "get_model_registry",
    # M4 第三部分：Store
    "ModelStore",
    "get_model_store",
    "DEFAULT_MODELS_DIR",
    # M4 第四部分：Lineage
    "ModelLineage",
    "LineageNode",
    "LineageChange",
    # M4 第五部分：Champion
    "ChampionManager",
    "ChampionResult",
    # M4 第六部分：Comparator
    "ModelComparator",
    "ComparisonRow",
    "ComparisonReport",
    # M4 第七部分：Lifecycle
    "LifecycleManager",
    "LifecycleEvent",
    "VALID_TRANSITIONS",
    # M4 第八部分：Audit
    "ModelAuditLog",
    "AuditEntry",
    "AuditAction",
    "get_audit_log",
    # M6：Model Package 架构
    "ModelPackage",
    "ModelManifest",
    "FeatureSetSnapshot",
    "LabelSetSnapshot",
    "SnapshotManager",
    "get_snapshot_manager",
    "ArtifactStore",
    "ChampionPointer",
    "ChampionHistoryEntry",
    "ModelPackageBuilder",
    "get_package_builder",
    # M6：.qlmodel 导入/导出
    "export_package",
    "export_from_store",
    "import_package",
    "import_to_registry",
    # M6：常量
    "MANIFEST_FILE",
    "MODEL_FILE",
    "METRICS_FILE",
    "VALIDATION_FILE",
    "TRAINING_FILE",
    "LINEAGE_FILE",
    "SNAPSHOT_DIR",
    "ARTIFACTS_DIR",
    "QLMODEL_EXTENSION",
]
