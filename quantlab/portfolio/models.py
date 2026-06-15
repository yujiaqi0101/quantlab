"""
Portfolio Models — V4.6 Portfolio Construction 核心数据模型

TargetPosition: 单个标的的目标仓位
TargetPortfolio: 一组目标仓位 + 约束元数据

与旧 portfolio_construction.TargetPortfolio 的关系：
  - 旧 TargetPortfolio 只有 timestamp + weights dict
  - 新 TargetPortfolio 增加了约束、现金、来源追踪
  - 两者兼容，新代码推荐用 portfolio/models
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class TargetPosition:
    """
    单个标的的目标仓位

    weight: 目标权重 (0.0 ~ 1.0)
      0.0 = 空仓
      0.5 = 50% 仓位
      1.0 = 满仓
    """
    symbol: str
    weight: float

    def __post_init__(self):
        if self.weight < 0:
            raise ValueError(f"weight must be >= 0, got {self.weight}")

    @property
    def is_active(self) -> bool:
        return self.weight > 0


@dataclass
class TargetPortfolio:
    """
    目标组合

    一组 TargetPosition + 元数据

    Signal → Allocator → TargetPortfolio → RebalanceEngine → Orders
    """
    timestamp: Any = None
    positions: Dict[str, float] = field(default_factory=dict)
    cash_weight: float = 0.0          # 现金权重
    source: str = ""                   # 来源追踪（哪个策略/allocator 生成的）
    constraints_applied: List[str] = field(default_factory=list)  # 已应用的约束

    def __post_init__(self):
        for sym, w in self.positions.items():
            if w < 0:
                raise ValueError(f"weight for {sym} must be >= 0, got {w}")

    @property
    def symbols(self) -> List[str]:
        return list(self.positions.keys())

    @property
    def active_symbols(self) -> List[str]:
        return [s for s, w in self.positions.items() if w > 0]

    @property
    def total_weight(self) -> float:
        return sum(self.positions.values())

    @property
    def num_positions(self) -> int:
        return len(self.active_symbols)

    def get_weight(self, symbol: str) -> float:
        return self.positions.get(symbol, 0.0)

    def set_weight(self, symbol: str, weight: float) -> None:
        self.positions[symbol] = weight

    def remove_symbol(self, symbol: str) -> None:
        self.positions.pop(symbol, None)

    def to_weight_dict(self) -> Dict[str, float]:
        return dict(self.positions)

    @classmethod
    def from_weight_dict(
        cls,
        weights: Dict[str, float],
        timestamp: Any = None,
        source: str = "",
    ) -> "TargetPortfolio":
        return cls(
            timestamp=timestamp,
            positions={k: v for k, v in weights.items() if v > 0},
            cash_weight=max(0, 1.0 - sum(w for w in weights.values() if w > 0)),
            source=source,
        )

    def __repr__(self) -> str:
        active = {s: f"{w:.1%}" for s, w in self.positions.items() if w > 0}
        return f"TargetPortfolio(cash={self.cash_weight:.1%}, positions={active})"
