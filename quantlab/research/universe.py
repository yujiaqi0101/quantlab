"""
UniverseRegistry — 标的池注册表

UniverseDefinition:
  - 静态成员: ["BTC", "ETH"]
  - 动态规则: top_n_by_volume(n=10, min_volume=1000)
  - rebalance: 每日/每周/每月
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, List, Optional, Set

import pandas as pd

from .frame import ResearchFrame


class RebalanceFreq(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    STATIC = "static"  # 不再平衡


@dataclass
class UniverseDefinition:
    id: str
    members: List[str] = field(default_factory=list)
    rule: Optional[str] = None  # "top_n_by_volume"
    rule_params: dict = field(default_factory=dict)
    rebalance: RebalanceFreq = RebalanceFreq.STATIC

    def resolve(self, panel: Optional[pd.DataFrame] = None) -> List[str]:
        """解析标的池成员。"""
        if self.rule is None:
            return list(self.members)
        if panel is None:
            return list(self.members)
        if self.rule == "top_n_by_volume":
            n = self.rule_params.get("n", 10)
            min_vol = self.rule_params.get("min_volume", 0)
            # 按 symbol 聚合 volume
            if "volume" not in panel.columns:
                return list(self.members)
            vol = panel.groupby(level="symbol")["volume"].mean()
            vol = vol[vol >= min_vol].sort_values(ascending=False)
            return list(vol.head(n).index)
        return list(self.members)


class UniverseRegistry:
    """标的池注册表。"""

    def __init__(self) -> None:
        self._store: dict = {}
        self._lock = threading.RLock()

    def register(self, universe: UniverseDefinition) -> "UniverseRegistry":
        with self._lock:
            self._store[universe.id] = universe
        return self

    def get(self, universe_id: str) -> Optional[UniverseDefinition]:
        with self._lock:
            return self._store.get(universe_id)

    def list(self) -> List[str]:
        with self._lock:
            return list(self._store.keys())

    def resolve(self, universe_id: str, panel: Optional[pd.DataFrame] = None) -> List[str]:
        with self._lock:
            u = self._store.get(universe_id)
            if u is None:
                return []
            return u.resolve(panel)


def get_universe_registry() -> UniverseRegistry:
    """全局 UniverseRegistry。"""
    global _universe_registry
    if _universe_registry is None:
        _universe_registry = UniverseRegistry()
        # 内置 crypto universe
        _universe_registry.register(
            UniverseDefinition(id="crypto_top10", members=["BTC", "ETH", "BNB"])
        )
        _universe_registry.register(
            UniverseDefinition(
                id="crypto_top_n_volume",
                rule="top_n_by_volume",
                rule_params={"n": 10, "min_volume": 1000},
                rebalance=RebalanceFreq.DAILY,
            )
        )
    return _universe_registry


_universe_registry: Optional[UniverseRegistry] = None


__all__ = [
    "UniverseDefinition",
    "UniverseRegistry",
    "RebalanceFreq",
    "get_universe_registry",
]
