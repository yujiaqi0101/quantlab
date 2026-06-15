"""
Crossover Signal — V4.6 交叉信号

快线上穿慢线 → 1 (买入)
快线下穿慢线 → -1 (卖出)
无交叉 → 0
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .base import Signal


class CrossoverSignal(Signal):
    """
    交叉信号（均线交叉等）

    fast 上穿 slow → 1
    fast 下穿 slow → -1
    """

    def __init__(
        self,
        fast_factor_name: str,
        slow_factor_name: str,
        signal_name: Optional[str] = None,
    ) -> None:
        self.fast_factor_name = fast_factor_name
        self.slow_factor_name = slow_factor_name
        self._name = signal_name or f"CROSS_{fast_factor_name}_{slow_factor_name}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Crossover: {self.fast_factor_name} crosses {self.slow_factor_name}"

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError(
            "CrossoverSignal 需要两个因子，请用 SignalEngine.transform_multi()。"
        )

    def transform_multi(self, factor_values: dict) -> pd.Series:
        fast = factor_values[self.fast_factor_name]
        slow = factor_values[self.slow_factor_name]
        # 当前差值和前一根差值
        diff = fast - slow
        prev_diff = diff.shift(1)
        signal = pd.Series(0, index=fast.index, dtype=float)
        # 上穿: 之前 fast < slow, 现在 fast > slow
        signal[(prev_diff <= 0) & (diff > 0)] = 1
        # 下穿: 之前 fast > slow, 现在 fast < slow
        signal[(prev_diff >= 0) & (diff < 0)] = -1
        return signal


class ZeroCrossoverSignal(Signal):
    """
    零轴交叉信号

    因子值上穿 0 → 1
    因子值下穿 0 → -1
    """

    def __init__(
        self,
        factor_name: str,
        signal_name: Optional[str] = None,
    ) -> None:
        self.factor_name = factor_name
        self._name = signal_name or f"ZERO_CROSS_{factor_name}"

    @property
    def name(self) -> str:
        return self._name

    def transform(self, series: pd.Series) -> pd.Series:
        prev = series.shift(1)
        signal = pd.Series(0, index=series.index, dtype=float)
        signal[(prev <= 0) & (series > 0)] = 1
        signal[(prev >= 0) & (series < 0)] = -1
        return signal
