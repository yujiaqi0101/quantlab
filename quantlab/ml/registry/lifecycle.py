"""
Lifecycle Manager — 模型生命周期管理

ML Lab M6：完整状态机管理

  状态（M6 完整版）：
    DRAFT       草稿
    TRAINING    训练中
    VALIDATING  验证中
    VALIDATED   已验证
    CANDIDATE   候选（通过验证）
    CHAMPION    冠军（上线）
    ARCHIVED    归档（Champion 被替换后，可回滚）
    RETIRED     退役（M4 兼容）
    DEPRECATED  废弃

  合法转换：
    DRAFT      → TRAINING
    TRAINING   → VALIDATING / DEPRECATED
    VALIDATING → VALIDATED / RETIRED
    VALIDATED  → CANDIDATE / ARCHIVED
    CANDIDATE  → CHAMPION / ARCHIVED
    CHAMPION   → ARCHIVED          （被新 Champion 替换）
    ARCHIVED   → CHAMPION / DEPRECATED  （可回滚为 Champion）
    RETIRED    → (终态)
    DEPRECATED → (终态)

  例如：
    LGBM_v4
    VALIDATING
        ↓ 通过验证
    VALIDATED
        ↓ 候选
    CANDIDATE
        ↓ 上线
    CHAMPION
        ↓ 被替换
    ARCHIVED
        ↓ 不再使用
    DEPRECATED
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .registry import ModelVersion, ModelRegistry, LifecycleStatus

logger = logging.getLogger("quantlab.ml.registry.lifecycle")


# 合法状态转换（M6 完整版）
VALID_TRANSITIONS: Dict[LifecycleStatus, List[LifecycleStatus]] = {
    LifecycleStatus.DRAFT: [LifecycleStatus.TRAINING, LifecycleStatus.DEPRECATED],
    LifecycleStatus.TRAINING: [LifecycleStatus.VALIDATING, LifecycleStatus.DEPRECATED],
    LifecycleStatus.VALIDATING: [LifecycleStatus.VALIDATED, LifecycleStatus.RETIRED],
    LifecycleStatus.VALIDATED: [LifecycleStatus.CANDIDATE, LifecycleStatus.ARCHIVED],
    LifecycleStatus.CANDIDATE: [LifecycleStatus.CHAMPION, LifecycleStatus.ARCHIVED],
    LifecycleStatus.CHAMPION: [LifecycleStatus.ARCHIVED],
    LifecycleStatus.ARCHIVED: [LifecycleStatus.CHAMPION, LifecycleStatus.DEPRECATED],  # 可回滚
    LifecycleStatus.RETIRED: [],  # 终态
    LifecycleStatus.DEPRECATED: [],  # 终态
}


@dataclass
class LifecycleEvent:
    """生命周期事件"""
    version_id: str = ""
    from_status: str = ""
    to_status: str = ""
    timestamp: str = ""
    reason: str = ""
    operator: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "operator": self.operator,
        }


class LifecycleManager:
    """
    生命周期管理器

    用法：
        mgr = LifecycleManager(registry)
        mgr.transition(version_id, LifecycleStatus.VALIDATING, reason="开始验证")
        mgr.transition(version_id, LifecycleStatus.CANDIDATE, reason="验证通过")
        mgr.promote(version_id, reason="上线")
        mgr.retire(version_id, reason="收益下降")
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self._events: List[LifecycleEvent] = []

    def transition(
        self,
        version_id: str,
        to_status: LifecycleStatus,
        reason: str = "",
        operator: str = "system",
    ) -> bool:
        """
        状态转换

        Args:
            version_id: 版本 ID
            to_status: 目标状态
            reason: 转换原因
            operator: 操作者

        Returns:
            是否成功
        """
        version = self.registry.get_version(version_id)
        if version is None:
            logger.error(f"Version not found: {version_id}")
            return False

        from_status = version.lifecycle
        if not self._is_valid_transition(from_status, to_status):
            logger.error(
                f"Invalid transition: {from_status.value} → {to_status.value} "
                f"for {version_id}"
            )
            return False

        # 特殊处理：CHAMPION 转换需要通过 ChampionManager
        if to_status == LifecycleStatus.CHAMPION:
            return self.promote(version_id, reason, operator)

        # 执行转换
        version.lifecycle = to_status
        if to_status == LifecycleStatus.RETIRED and not version.retired_at:
            version.retired_at = pd.Timestamp.now().isoformat()

        # 记录事件
        event = LifecycleEvent(
            version_id=version_id,
            from_status=from_status.value,
            to_status=to_status.value,
            timestamp=pd.Timestamp.now().isoformat(),
            reason=reason,
            operator=operator,
        )
        self._events.append(event)

        logger.info(
            f"Lifecycle: {version.name} {from_status.value} → {to_status.value} "
            f"({reason})"
        )
        return True

    def promote(
        self,
        version_id: str,
        reason: str = "",
        operator: str = "system",
    ) -> bool:
        """
        提升为 Champion

        会自动退役旧 Champion
        """
        version = self.registry.get_version(version_id)
        if version is None:
            return False

        from_status = version.lifecycle
        if from_status not in (LifecycleStatus.CANDIDATE, LifecycleStatus.CHAMPION):
            logger.error(
                f"Cannot promote from {from_status.value}, "
                f"need CANDIDATE"
            )
            return False

        # 通过 registry 设置 champion（会自动退役旧 champion）
        success = self.registry.set_champion(version.family, version_id)
        if success:
            event = LifecycleEvent(
                version_id=version_id,
                from_status=from_status.value,
                to_status=LifecycleStatus.CHAMPION.value,
                timestamp=pd.Timestamp.now().isoformat(),
                reason=reason or "Promoted to champion",
                operator=operator,
            )
            self._events.append(event)
            logger.info(f"Promoted: {version.name} → CHAMPION ({reason})")
        return success

    def retire(
        self,
        version_id: str,
        reason: str = "",
        operator: str = "system",
    ) -> bool:
        """退役模型"""
        return self.transition(
            version_id, LifecycleStatus.RETIRED, reason, operator
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_events(
        self,
        version_id: Optional[str] = None,
    ) -> List[LifecycleEvent]:
        """获取生命周期事件"""
        if version_id:
            return [e for e in self._events if e.version_id == version_id]
        return list(self._events)

    def get_current_status(self, version_id: str) -> Optional[LifecycleStatus]:
        """获取当前状态"""
        version = self.registry.get_version(version_id)
        return version.lifecycle if version else None

    def list_by_status(self, status: LifecycleStatus) -> List[ModelVersion]:
        """按状态列出模型"""
        return self.registry.list_versions(lifecycle=status)

    def get_status_summary(self) -> Dict[str, int]:
        """状态统计"""
        summary = {s.value: 0 for s in LifecycleStatus}
        for v in self.registry.list_versions():
            summary[v.lifecycle.value] = summary.get(v.lifecycle.value, 0) + 1
        return summary

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _is_valid_transition(
        from_status: LifecycleStatus,
        to_status: LifecycleStatus,
    ) -> bool:
        """检查状态转换是否合法"""
        if from_status == to_status:
            return True  # 同状态允许（幂等）
        allowed = VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self._events],
            "status_summary": self.get_status_summary(),
        }
