"""
ChampionManager — 资产冠军管理

每个 Family 一个 Champion。

  Momentum_LGBM       Champion 1.2.0
  MeanReversion_RF    Champion 2.1.1
  CrossSection_XGB    Champion 3.0.0

集成 Validation Pipeline：
  只有 VALIDATED 状态的资产才能成为 Candidate
  Candidate 挑战 Champion → PROMOTE / REJECT

Promote 时旧 Champion 自动 ARCHIVED。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import AssetStatus, AssetType, QuantAsset

logger = logging.getLogger("quantlab.asset.champion")


@dataclass
class ChampionPointer:
    """
    冠军指针

    family → asset_id

    runtime 永远 get_champion(family)，策略无需修改。
    """
    family: str = ""
    champion_asset_id: str = ""
    promoted_at: str = ""
    previous_champion_id: str = ""        # 前任 Champion（用于回滚）
    promotion_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "champion_asset_id": self.champion_asset_id,
            "promoted_at": self.promoted_at,
            "previous_champion_id": self.previous_champion_id,
            "promotion_reason": self.promotion_reason,
        }


@dataclass
class ChampionHistoryEntry:
    """冠军历史记录"""
    family: str = ""
    asset_id: str = ""
    action: str = ""                     # PROMOTED / DEMOTED / ARCHIVED
    timestamp: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "asset_id": self.asset_id,
            "action": self.action,
            "timestamp": self.timestamp,
            "reason": self.reason,
        }


class ChampionManager:
    """
    冠军管理器

    用法：
        mgr = ChampionManager()
        mgr.promote("LGBM_Momentum", "ASSET-001", reason="Validation score 90")
        champion = mgr.get_champion("LGBM_Momentum")
        all_champions = mgr.get_all_champions()
    """

    def __init__(self) -> None:
        # family → ChampionPointer
        self._champions: Dict[str, ChampionPointer] = {}
        # family → List[ChampionHistoryEntry]
        self._history: Dict[str, List[ChampionHistoryEntry]] = {}

    # ------------------------------------------------------------------
    # Promote / Demote
    # ------------------------------------------------------------------

    def promote(
        self,
        family: str,
        asset_id: str,
        reason: str = "",
        asset: Optional[QuantAsset] = None,
    ) -> ChampionPointer:
        """
        提升资产为 Champion

        Args:
            family: 资产族名
            asset_id: 资产 ID
            reason: 提升原因
            asset: 资产对象（可选，用于状态更新）

        Returns:
            ChampionPointer
        """
        now = pd.Timestamp.now().isoformat()

        # 获取旧 Champion
        old_pointer = self._champions.get(family)
        old_champion_id = old_pointer.champion_asset_id if old_pointer else ""

        # 创建新指针
        pointer = ChampionPointer(
            family=family,
            champion_asset_id=asset_id,
            promoted_at=now,
            previous_champion_id=old_champion_id,
            promotion_reason=reason,
        )
        self._champions[family] = pointer

        # 更新资产状态
        if asset is not None:
            asset.status = AssetStatus.ACTIVE

        # 记录历史
        self._add_history(family, asset_id, "PROMOTED", reason, now)

        # 旧 Champion 归档
        if old_champion_id and old_champion_id != asset_id:
            self._add_history(family, old_champion_id, "ARCHIVED", "Replaced by new champion", now)

        logger.info(f"Champion promoted: {family} → {asset_id} (reason: {reason})")
        return pointer

    def demote(self, family: str, reason: str = "") -> bool:
        """
        降级当前 Champion（回滚到前任）

        Returns:
            True 如果降级成功
        """
        pointer = self._champions.get(family)
        if pointer is None:
            return False

        now = pd.Timestamp.now().isoformat()
        old_champion_id = pointer.champion_asset_id

        # 记录历史
        self._add_history(family, old_champion_id, "DEMOTED", reason, now)

        # 回滚到前任
        if pointer.previous_champion_id:
            pointer.champion_asset_id = pointer.previous_champion_id
            pointer.previous_champion_id = ""
            pointer.promoted_at = now
            pointer.promotion_reason = f"Rollback: {reason}"
            self._add_history(family, pointer.champion_asset_id, "PROMOTED", "Restored as champion", now)
            logger.info(f"Champion rolled back: {family} → {pointer.champion_asset_id}")
        else:
            # 没有前任，删除 Champion
            del self._champions[family]
            logger.info(f"Champion removed: {family} (no previous champion)")

        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_champion(self, family: str) -> Optional[ChampionPointer]:
        """获取指定 Family 的 Champion"""
        return self._champions.get(family)

    def get_champion_id(self, family: str) -> Optional[str]:
        """获取 Champion 的 asset_id"""
        pointer = self._champions.get(family)
        return pointer.champion_asset_id if pointer else None

    def get_all_champions(self) -> Dict[str, ChampionPointer]:
        """获取所有 Family 的 Champion"""
        return dict(self._champions)

    def list_families(self) -> List[str]:
        """列出所有有 Champion 的 Family"""
        return sorted(self._champions.keys())

    def has_champion(self, family: str) -> bool:
        """检查 Family 是否有 Champion"""
        return family in self._champions

    # ------------------------------------------------------------------
    # 历史
    # ------------------------------------------------------------------

    def get_history(self, family: str) -> List[ChampionHistoryEntry]:
        """获取 Family 的 Champion 历史"""
        return list(self._history.get(family, []))

    def _add_history(
        self,
        family: str,
        asset_id: str,
        action: str,
        reason: str,
        timestamp: str,
    ) -> None:
        if family not in self._history:
            self._history[family] = []
        self._history[family].append(
            ChampionHistoryEntry(
                family=family,
                asset_id=asset_id,
                action=action,
                timestamp=timestamp,
                reason=reason,
            )
        )

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_champions": len(self._champions),
            "champions": {
                family: pointer.to_dict()
                for family, pointer in self._champions.items()
            },
            "history": {
                family: [h.to_dict() for h in entries]
                for family, entries in self._history.items()
            },
        }
