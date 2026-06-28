"""
模块 7: Position Allocator

建议权重（不是最终 portfolio）。
权重归一化到 [0, 1]，且所有 LONG 权重之和 + 所有 SHORT 权重之和 ≤ 1.0。
holding_period 在此模块一并设定（默认 5 天，可配置）。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np

from .signal import Signal, SignalDirection, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.allocator")


class PositionAllocator(ABC):
    """仓位分配器抽象基类"""

    name: str = "base"

    def __init__(self, holding_period: int = 5) -> None:
        self.holding_period = int(holding_period)

    @abstractmethod
    def allocate(self, signal_set: SignalSet) -> SignalSet:
        ...

    def _finalize(self, signal_set: SignalSet) -> None:
        """设定 holding_period 并归一化权重（多空总和 ≤ 1.0）"""
        longs = signal_set.longs()
        shorts = signal_set.shorts()
        long_w = sum(s.suggested_weight for s in longs)
        short_w = sum(s.suggested_weight for s in shorts)
        total_w = long_w + short_w
        # 多空权重总和 ≤ 1.0
        if total_w > 1.0:
            scale = 1.0 / total_w
            for s in longs:
                s.suggested_weight *= scale
            for s in shorts:
                s.suggested_weight *= scale
        # 设 holding_period
        for s in signal_set.signals:
            s.holding_period = self.holding_period
            s.metadata["allocator_method"] = self.name
            s.metadata["holding_period"] = self.holding_period

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "holding_period": self.holding_period}


class EqualWeightAllocator(PositionAllocator):
    """等权"""

    name = "equal_weight"

    def allocate(self, signal_set: SignalSet) -> SignalSet:
        longs = signal_set.longs()
        shorts = signal_set.shorts()
        long_w = 1.0 / len(longs) if longs else 0.0
        short_w = 1.0 / len(shorts) if shorts else 0.0
        for s in signal_set.signals:
            if s.direction == SignalDirection.LONG:
                s.suggested_weight = long_w
            elif s.direction == SignalDirection.SHORT:
                s.suggested_weight = short_w
            else:
                s.suggested_weight = 0.0
        self._finalize(signal_set)
        return signal_set


class ConfidenceWeightAllocator(PositionAllocator):
    """按 confidence 加权"""

    name = "confidence_weight"

    def allocate(self, signal_set: SignalSet) -> SignalSet:
        longs = signal_set.longs()
        shorts = signal_set.shorts()
        long_total = sum(s.confidence for s in longs) or 1.0
        short_total = sum(s.confidence for s in shorts) or 1.0
        for s in signal_set.signals:
            if s.direction == SignalDirection.LONG:
                s.suggested_weight = s.confidence / long_total
            elif s.direction == SignalDirection.SHORT:
                s.suggested_weight = s.confidence / short_total
            else:
                s.suggested_weight = 0.0
        self._finalize(signal_set)
        return signal_set


class KellyAllocator(PositionAllocator):
    """Kelly 公式: f = (p*b - q) / b，简化版用 confidence"""

    name = "kelly"

    def __init__(self, holding_period: int = 5, max_weight: float = 0.25) -> None:
        super().__init__(holding_period)
        self.max_weight = float(max_weight)

    def allocate(self, signal_set: SignalSet) -> SignalSet:
        for s in signal_set.signals:
            if s.direction == SignalDirection.NEUTRAL:
                s.suggested_weight = 0.0
                continue
            p = max(0.01, min(0.99, s.confidence))
            q = 1 - p
            # 简化 Kelly：假设赔率 b = expected_return / scale
            b = max(0.1, abs(s.expected_return) * 20)  # 经验缩放
            f = (p * b - q) / b
            f = max(0.0, min(self.max_weight, f))
            s.suggested_weight = float(f)
        self._finalize(signal_set)
        return signal_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "holding_period": self.holding_period, "max_weight": self.max_weight}


class VolatilityScalingAllocator(PositionAllocator):
    """波动率倒数加权"""

    name = "volatility_scaling"

    def __init__(
        self,
        holding_period: int = 5,
        target_volatility: float = 0.15,
        volatility_provider=None,
    ) -> None:
        super().__init__(holding_period)
        self.target_volatility = float(target_volatility)
        self.volatility_provider = volatility_provider

    def allocate(self, signal_set: SignalSet) -> SignalSet:
        longs = signal_set.longs()
        shorts = signal_set.shorts()
        long_w = self._compute_weights(longs)
        short_w = self._compute_weights(shorts)
        w_map: Dict[str, float] = {}
        for s, w in zip(longs, long_w):
            w_map[s.signal_id] = w
        for s, w in zip(shorts, short_w):
            w_map[s.signal_id] = w
        for s in signal_set.signals:
            s.suggested_weight = w_map.get(s.signal_id, 0.0)
        self._finalize(signal_set)
        return signal_set

    def _compute_weights(self, signals: List[Signal]) -> List[float]:
        if not signals:
            return []
        vols: List[float] = []
        for s in signals:
            if self.volatility_provider:
                try:
                    v = float(self.volatility_provider(s.symbol))
                    v = max(1e-6, v)
                except Exception:
                    v = self.target_volatility
            else:
                # 无数据源时用 confidence 反比作伪波动
                v = max(1e-6, 1.0 - s.confidence)
            vols.append(v)
        inv_vols = [1.0 / v for v in vols]
        total = sum(inv_vols) or 1.0
        return [iv / total for iv in inv_vols]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "holding_period": self.holding_period,
            "target_volatility": self.target_volatility,
        }


class RiskParityAllocator(PositionAllocator):
    """风险平价 — 简化版（等风险贡献）"""

    name = "risk_parity"

    def __init__(self, holding_period: int = 5, volatility_provider=None) -> None:
        super().__init__(holding_period)
        self.volatility_provider = volatility_provider

    def allocate(self, signal_set: SignalSet) -> SignalSet:
        # 简化：等价于波动率倒数加权
        vol_alloc = VolatilityScalingAllocator(
            holding_period=self.holding_period,
            volatility_provider=self.volatility_provider,
        )
        return vol_alloc.allocate(signal_set)

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "holding_period": self.holding_period}


# ---- 工厂 ----

_ALLOCATORS = {
    "equal_weight": EqualWeightAllocator,
    "confidence_weight": ConfidenceWeightAllocator,
    "kelly": KellyAllocator,
    "volatility_scaling": VolatilityScalingAllocator,
    "risk_parity": RiskParityAllocator,
}


def get_allocator(method: str = "equal_weight", **params) -> PositionAllocator:
    cls = _ALLOCATORS.get(method.lower(), EqualWeightAllocator)
    import inspect
    sig = inspect.signature(cls.__init__)
    valid = {k: v for k, v in params.items() if k in sig.parameters}
    return cls(**valid)
