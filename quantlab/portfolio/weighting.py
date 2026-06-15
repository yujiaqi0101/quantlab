"""
Weighting Models — V4.6 仓位权重模型

WeightingModel ABC + 具体实现：
  - EqualWeightModel: 等权分配
  - FixedWeightModel: 固定权重
  - SignalWeightModel: 按信号强度加权
  - RiskParityModel: 按波动率倒数加权（简化版）

输入: signals Dict[symbol, signal_value]
输出: weights Dict[symbol, weight]
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional

import numpy as np
import pandas as pd


class WeightingModel(ABC):
    """权重模型基类"""

    @abstractmethod
    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        """
        根据信号分配权重

        输入: {symbol: signal_value}  signal ∈ {-1, 0, 1} 或连续值
        输出: {symbol: weight}  weight ∈ [0, 1]
        """
        pass


class EqualWeightModel(WeightingModel):
    """
    等权模型

    所有做多信号等权分配
    例: 3 个 symbol 信号=1 → 各 33.3%
    """

    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        active = {s: v for s, v in signals.items() if v > 0}
        if not active:
            return {}
        w = 1.0 / len(active)
        return {s: w for s in active}


class FixedWeightModel(WeightingModel):
    """
    固定权重模型

    每个做多信号分配固定权重
    例: weight=0.2, 3 个 signal=1 → 各 20%（总 60%，剩余 40% 现金）
    """

    def __init__(self, weight: float = 0.2) -> None:
        self.weight = weight

    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        return {s: self.weight for s, v in signals.items() if v > 0}


class SignalWeightModel(WeightingModel):
    """
    信号强度加权模型

    信号值越大，权重越高
    例: RSI=80 → weight 大, RSI=55 → weight 小
    """

    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        active = {s: v for s, v in signals.items() if v > 0}
        if not active:
            return {}
        total = sum(active.values())
        if total <= 0:
            return {}
        return {s: v / total for s, v in active.items()}


class RiskParityModel(WeightingModel):
    """
    简化风险平价模型

    按波动率倒数加权：波动率越低，权重越高
    需要外部提供 volatility 数据
    """

    def __init__(self, volatilities: Optional[Dict[str, float]] = None) -> None:
        self.volatilities = volatilities or {}

    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        active = {s: v for s, v in signals.items() if v > 0}
        if not active:
            return {}
        # 用波动率倒数
        inv_vols = {}
        for s in active:
            vol = self.volatilities.get(s, 0.01)  # 默认 1%
            inv_vols[s] = 1.0 / max(vol, 1e-9)
        total = sum(inv_vols.values())
        return {s: v / total for s, v in inv_vols.items()}


class TopNWeightModel(WeightingModel):
    """
    TopN 权重模型

    只取信号最强的 N 个，等权分配
    """

    def __init__(self, n: int = 2) -> None:
        self.n = n

    def allocate(self, signals: Dict[str, float]) -> Dict[str, float]:
        # 按 signal 值排序取 top N
        sorted_sigs = sorted(
            ((s, v) for s, v in signals.items() if v > 0),
            key=lambda x: x[1],
            reverse=True,
        )
        top_n = sorted_sigs[:self.n]
        if not top_n:
            return {}
        w = 1.0 / len(top_n)
        return {s: w for s, _ in top_n}
