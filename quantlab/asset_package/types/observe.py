"""
Observe Profile — 观察配置包

把观察指标配置从硬编码升级为可注册、可复用的 Package。

2 种实现：
  - StandardObserve: 标准观察（低频策略）
  - HFObserveProfile: 高频观察
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..base import AssetPackage, PackageType

logger = logging.getLogger("quantlab.asset_package.types.observe")


# ==================================================================
# ObserveProfile 基类
# ==================================================================

@dataclass
class ObserveProfile(AssetPackage):
    """观察配置包基类"""
    package_type: PackageType = PackageType.OBSERVE

    def get_metrics(self) -> List[str]:
        """返回需要监控的指标列表"""
        raise NotImplementedError("Subclass must implement get_metrics()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })


# ==================================================================
# 1. StandardObserve — 标准观察（低频）
# ==================================================================

@dataclass
class StandardObserve(ObserveProfile):
    """标准观察（低频策略）"""
    metrics: List[str] = field(default_factory=lambda: [
        "daily_return",
        "cumulative_return",
        "drawdown",
        "sharpe_ratio",
        "factor_exposure",
        "position_summary",
    ])

    def to_config(self) -> Dict[str, Any]:
        return {"metrics": self.metrics}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.metrics = config.get("metrics", [
            "daily_return", "cumulative_return", "drawdown",
            "sharpe_ratio", "factor_exposure", "position_summary",
        ])

    def get_metrics(self) -> List[str]:
        return self.metrics


# ==================================================================
# 2. HFObserveProfile — 高频观察
# ==================================================================

@dataclass
class HFObserveProfile(ObserveProfile):
    """高频观察（高频策略）"""
    metrics: List[str] = field(default_factory=lambda: [
        "order_timeline",
        "latency",
        "fill_rate",
        "slippage",
        "order_book_imbalance",
        "trade_frequency",
    ])

    def to_config(self) -> Dict[str, Any]:
        return {"metrics": self.metrics}

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.metrics = config.get("metrics", [
            "order_timeline", "latency", "fill_rate",
            "slippage", "order_book_imbalance", "trade_frequency",
        ])

    def get_metrics(self) -> List[str]:
        return self.metrics
