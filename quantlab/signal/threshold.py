"""
Threshold Signal — V4.6 阈值信号

因子值超过/低于阈值时产生信号

例如：
  RSI < 30 → 1 (买入)
  RSI > 70 → -1 (卖出)
  其他 → 0
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from .base import Signal


class ThresholdSignal(Signal):
    """
    阈值信号

    factor < lower → 1 (做多)
    factor > upper → -1 (做空/平仓)
    其他 → 0
    """

    def __init__(
        self,
        factor_name: str,
        lower: float,
        upper: float,
        signal_name: Optional[str] = None,
    ) -> None:
        self.factor_name = factor_name
        self.lower = lower
        self.upper = upper
        self._name = signal_name or f"THRESH_{factor_name}_{lower}_{upper}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Threshold: {self.factor_name} < {self.lower} → 1, > {self.upper} → -1"

    def transform(self, series: pd.Series) -> pd.Series:
        signal = pd.Series(0, index=series.index, dtype=float)
        signal[series < self.lower] = 1
        signal[series > self.upper] = -1
        return signal


class BandSignal(Signal):
    """
    带状信号（布林带等）

    factor < lower_band → 1
    factor > upper_band → -1
    """

    def __init__(
        self,
        factor_name: str,
        upper_factor_name: str,
        lower_factor_name: str,
        signal_name: Optional[str] = None,
    ) -> None:
        self.factor_name = factor_name
        self.upper_factor_name = upper_factor_name
        self.lower_factor_name = lower_factor_name
        self._name = signal_name or f"BAND_{factor_name}"

    @property
    def name(self) -> str:
        return self._name

    def transform(self, series: pd.Series) -> pd.Series:
        # 单因子模式: 需要上下轨，用 MultiFactorSignal 代替
        raise NotImplementedError(
            "BandSignal 需要上下轨因子，请用 SignalEngine.transform_multi()。"
        )

    def transform_multi(self, factor_values: dict) -> pd.Series:
        price = factor_values[self.factor_name]
        upper = factor_values[self.upper_factor_name]
        lower = factor_values[self.lower_factor_name]
        signal = pd.Series(0, index=price.index, dtype=float)
        signal[price < lower] = 1
        signal[price > upper] = -1
        return signal
