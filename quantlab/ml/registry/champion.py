"""
Champion Manager — 冠军模型管理

ML Lab M4 第五部分：专业量化必须有

  概念：
    Champion   = 当前最佳模型（上线）
    Challenger = 新模型（挑战者）

  自动比较：
    Sharpe / IC / MaxDD

  如果 Challenger > Champion：
    Promote → 成为新 Champion
  否则：
    Reject  → 退役

  未来部署永远引用：
    registry.get_champion()
  而不是：
    load("lgbm_v4.pkl")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .registry import ModelVersion, ModelRegistry, LifecycleStatus

logger = logging.getLogger("quantlab.ml.registry.champion")


@dataclass
class ChampionResult:
    """Champion 挑战结果"""
    family: str = ""
    challenger_id: str = ""
    champion_id: str = ""
    promoted: bool = False
    reason: str = ""
    comparison: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "challenger_id": self.challenger_id,
            "champion_id": self.champion_id,
            "promoted": self.promoted,
            "reason": self.reason,
            "comparison": self.comparison,
        }


class ChampionManager:
    """
    Champion 管理器

    用法：
        mgr = ChampionManager(registry)
        result = mgr.challenge(
            challenger_id="MV-new",
            metrics=["sharpe", "ic"],
            higher_is_better=True,
        )
        if result.promoted:
            print("新模型上线！")
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def challenge(
        self,
        challenger_id: str,
        metrics: Optional[List[str]] = None,
        threshold: float = 0.0,
        operator: str = "system",
    ) -> ChampionResult:
        """
        Challenger 挑战 Champion

        Args:
            challenger_id: 挑战者版本 ID
            metrics: 比较指标（默认 ["sharpe", "ic"]）
            threshold: 挑战者必须超过冠军的阈值（0 表示严格大于）
            operator: 操作者

        Returns:
            ChampionResult
        """
        if metrics is None:
            metrics = ["sharpe", "ic"]

        challenger = self.registry.get_version(challenger_id)
        if challenger is None:
            return ChampionResult(
                challenger_id=challenger_id,
                reason="Challenger not found",
            )

        family = challenger.family
        current_champion = self.registry.get_champion(family)

        result = ChampionResult(
            family=family,
            challenger_id=challenger_id,
            champion_id=current_champion.version_id if current_champion else "",
        )

        # 如果当前没有 Champion，直接 promote
        if current_champion is None:
            success = self.registry.set_champion(family, challenger_id)
            result.promoted = success
            result.reason = "No existing champion, auto-promoted"
            logger.info(f"Auto-promoted (no existing champion): {challenger.name}")
            return result

        # 比较 metrics
        comparison: Dict[str, Any] = {}
        all_better = True
        for metric in metrics:
            champ_val = float(current_champion.metrics.get(metric, 0))
            chall_val = float(challenger.metrics.get(metric, 0))
            is_better = chall_val > champ_val + threshold
            comparison[metric] = {
                "champion": champ_val,
                "challenger": chall_val,
                "diff": chall_val - champ_val,
                "challenger_better": is_better,
            }
            if not is_better:
                all_better = False

        result.comparison = comparison

        if all_better:
            # Promote
            success = self.registry.set_champion(family, challenger_id)
            result.promoted = success
            result.reason = (
                f"Challenger better in all metrics: {metrics}"
            )
            logger.info(
                f"Champion promoted: {family} "
                f"{current_champion.name} → {challenger.name}"
            )
        else:
            # Reject
            challenger.lifecycle = LifecycleStatus.RETIRED
            challenger.retired_at = pd.Timestamp.now().isoformat()
            failed_metrics = [
                m for m in metrics
                if not comparison[m]["challenger_better"]
            ]
            result.reason = (
                f"Challenger not better in: {failed_metrics}"
            )
            logger.info(
                f"Challenger rejected: {challenger.name} "
                f"(failed: {failed_metrics})"
            )

        return result

    def get_champion(self, family: str) -> Optional[ModelVersion]:
        """获取当前 Champion"""
        return self.registry.get_champion(family)

    def get_all_champions(self) -> Dict[str, ModelVersion]:
        """获取所有族的 Champion"""
        return self.registry.get_all_champions()

    def get_challengers(self, family: str) -> List[ModelVersion]:
        """获取指定族的候选挑战者（CANDIDATE 状态）"""
        return self.registry.list_versions(
            family=family,
            lifecycle=LifecycleStatus.CANDIDATE,
        )

    def force_promote(
        self,
        version_id: str,
        reason: str = "",
        operator: str = "system",
    ) -> bool:
        """
        强制提升（不比较 metrics）

        用于手动上线
        """
        version = self.registry.get_version(version_id)
        if version is None:
            return False
        success = self.registry.set_champion(version.family, version_id)
        if success:
            logger.info(
                f"Force promoted: {version.name} ({reason})"
            )
        return success

    def get_champion_history(self, family: str) -> List[Dict[str, Any]]:
        """
        获取 Champion 历史（通过 lifecycle 事件推断）

        返回所有曾经是 CHAMPION 的版本（按 promoted_at 排序）
        """
        versions = self.registry.get_family(family)
        champions = [
            v for v in versions
            if v.lifecycle in (LifecycleStatus.CHAMPION, LifecycleStatus.RETIRED)
            and v.promoted_at
        ]
        champions.sort(key=lambda v: v.promoted_at)
        return [
            {
                "version_id": v.version_id,
                "name": v.name,
                "version_number": v.version_number,
                "promoted_at": v.promoted_at,
                "retired_at": v.retired_at,
                "metrics": v.metrics,
                "is_current": v.lifecycle == LifecycleStatus.CHAMPION,
            }
            for v in champions
        ]
