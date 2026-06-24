"""
Champion Pointer — 冠军指针（M6）

  不要 best_model.pkl
  而是 Champion Pointer：

    LGBM_Momentum/
    ├── versions/
    │   ├── v1/
    │   ├── v2/
    │   └── v3/
    └── champion.yaml      ← 指针文件

  champion.yaml:
    family: LGBM_Momentum
    champion_version: 3
    champion_version_id: MV-xxx
    champion_name: LGBM_Momentum_v3
    promoted_at: 2026-06-24T10:00:00
    history:
      - version: 1, promoted_at: ..., retired_at: ...
      - version: 2, promoted_at: ..., retired_at: ...
      - version: 3, promoted_at: ...

  Runtime 永远：
    load_champion() → v3
  以后 v4 更好，只更新 pointer.yaml
  策略完全不用修改。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

logger = logging.getLogger("quantlab.ml.registry.champion_pointer")


@dataclass
class ChampionHistoryEntry:
    """Champion 历史条目"""
    version: int = 0
    version_id: str = ""
    name: str = ""
    promoted_at: str = ""
    retired_at: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "version_id": self.version_id,
            "name": self.name,
            "promoted_at": self.promoted_at,
            "retired_at": self.retired_at,
            "metrics": self.metrics,
        }


@dataclass
class ChampionPointer:
    """
    Champion 指针文件

    存储在 {family}/champion.yaml

    用法：
        ptr = ChampionPointer(family="LGBM_Momentum")
        ptr.set_champion(version_number=3, version_id="MV-xxx", name="LGBM_Momentum_v3")
        ptr.save("/path/to/family_dir/champion.yaml")
        ptr2 = ChampionPointer.load("/path/to/family_dir/champion.yaml")
        print(ptr2.champion_version)  # 3
    """
    family: str = ""
    champion_version: int = 0
    champion_version_id: str = ""
    champion_name: str = ""
    promoted_at: str = ""
    history: List[ChampionHistoryEntry] = field(default_factory=list)

    def set_champion(
        self,
        version_number: int,
        version_id: str,
        name: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """设置新 Champion（自动归档旧 Champion 到 history）"""
        # 归档旧 Champion
        if self.champion_version_id and self.champion_version != version_number:
            old_entry = ChampionHistoryEntry(
                version=self.champion_version,
                version_id=self.champion_version_id,
                name=self.champion_name,
                promoted_at=self.promoted_at,
                retired_at=pd.Timestamp.now().isoformat(),
            )
            self.history.append(old_entry)

        # 设置新 Champion
        self.champion_version = version_number
        self.champion_version_id = version_id
        self.champion_name = name
        self.promoted_at = pd.Timestamp.now().isoformat()

        # 添加到 history（当前 Champion 也记录）
        current_entry = ChampionHistoryEntry(
            version=version_number,
            version_id=version_id,
            name=name,
            promoted_at=self.promoted_at,
            metrics=metrics or {},
        )
        # 移除同版本的旧记录（如果有）
        self.history = [h for h in self.history if h.version != version_number]
        self.history.append(current_entry)

    def get_current(self) -> Optional[ChampionHistoryEntry]:
        """获取当前 Champion 的历史条目"""
        for h in self.history:
            if h.version == self.champion_version and not h.retired_at:
                return h
        return None

    def rollback_to(self, version_number: int) -> bool:
        """
        回滚到指定版本（将指定版本重新设为 Champion）

        Returns:
            True 如果回滚成功
        """
        target = None
        for h in self.history:
            if h.version == version_number:
                target = h
                break
        if target is None:
            return False

        # 归档当前 Champion
        if self.champion_version != version_number:
            old_entry = ChampionHistoryEntry(
                version=self.champion_version,
                version_id=self.champion_version_id,
                name=self.champion_name,
                promoted_at=self.promoted_at,
                retired_at=pd.Timestamp.now().isoformat(),
            )
            self.history.append(old_entry)

        # 设置目标为 Champion
        self.champion_version = target.version
        self.champion_version_id = target.version_id
        self.champion_name = target.name
        self.promoted_at = pd.Timestamp.now().isoformat()
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "champion_version": self.champion_version,
            "champion_version_id": self.champion_version_id,
            "champion_name": self.champion_name,
            "promoted_at": self.promoted_at,
            "history": [h.to_dict() for h in self.history],
        }

    def save(self, path: str) -> None:
        """保存为 champion.yaml"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        logger.info(f"Champion pointer saved: {self.family} → v{self.champion_version}")

    @classmethod
    def load(cls, path: str) -> "ChampionPointer":
        """从 champion.yaml 加载"""
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        history = [
            ChampionHistoryEntry(
                version=h.get("version", 0),
                version_id=h.get("version_id", ""),
                name=h.get("name", ""),
                promoted_at=h.get("promoted_at", ""),
                retired_at=h.get("retired_at", ""),
                metrics=h.get("metrics", {}),
            )
            for h in data.get("history", [])
        ]
        return cls(
            family=data.get("family", ""),
            champion_version=data.get("champion_version", 0),
            champion_version_id=data.get("champion_version_id", ""),
            champion_name=data.get("champion_name", ""),
            promoted_at=data.get("promoted_at", ""),
            history=history,
        )

    @classmethod
    def load_for_family(cls, family_dir: str, family: str = "") -> "ChampionPointer":
        """加载指定族的 Champion 指针"""
        path = os.path.join(family_dir, "champion.yaml")
        ptr = cls.load(path)
        if not ptr.family and family:
            ptr.family = family
        return ptr
