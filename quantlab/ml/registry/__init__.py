"""
Model Registry — 模型注册中心

ML Lab M4：模型注册中心 + 完整生命周期管理

  M4 第一部分：ModelRegistry          — Family 概念 + Champion 管理
  M4 第二部分：ModelVersion            — lifecycle 状态 + lineage 字段
  M4 第三部分：ModelStore              — 磁盘文件管理
  M4 第四部分：ModelLineage            — 血统图
  M4 第五部分：ChampionManager         — Champion/Challenger 自动 promote
  M4 第六部分：ModelComparator         — 跨版本对比
  M4 第七部分：LifecycleManager        — 状态机
  M4 第八部分：ModelAuditLog           — 操作审计
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
]
