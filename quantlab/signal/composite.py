"""
Composite Signals — V4.6 信号组合

支持多信号逻辑组合：
  - AndSignal: 所有信号一致才触发
  - OrSignal: 任一信号触发即触发
  - NotSignal: 取反
  - MajoritySignal: 多数投票

用法：
    rsi_sig = ThresholdSignal("RSI14", 30, 70)
    mom_sig = ZeroCrossoverSignal("MOM20")

    # 两个信号都看多才做多
    combined = AndSignal(rsi_sig, mom_sig, name="RSI_AND_MOM")

    # 任一看多就做多
    combined = OrSignal(rsi_sig, mom_sig, name="RSI_OR_MOM")
"""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from .base import Signal


class AndSignal(Signal):
    """
    AND 信号：所有子信号一致才触发

    Long  = 所有信号 == 1
    Short = 所有信号 == -1
    """

    def __init__(
        self,
        *signals: Signal,
        name: Optional[str] = None,
    ) -> None:
        if len(signals) < 2:
            raise ValueError("AndSignal requires at least 2 signals")
        self._signals = signals
        self._name = name or f"AND_{'_'.join(s.name for s in signals)}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"AND({', '.join(s.name for s in self._signals)})"

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError("AndSignal 需要多信号输入，请用 SignalEngine")

    def transform_multi_signal(
        self,
        signal_values: List[pd.Series],
    ) -> pd.Series:
        """
        组合多个已生成的信号

        signal_values: 每个子信号的 Series（值域 {-1, 0, 1}）
        """
        if len(signal_values) != len(self._signals):
            raise ValueError(
                f"expected {len(self._signals)} signal values, "
                f"got {len(signal_values)}"
            )
        result = pd.Series(0, index=signal_values[0].index, dtype=float)
        # Long: 所有 == 1
        long_mask = pd.Series(True, index=result.index)
        for sv in signal_values:
            long_mask = long_mask & (sv == 1)
        # Short: 所有 == -1
        short_mask = pd.Series(True, index=result.index)
        for sv in signal_values:
            short_mask = short_mask & (sv == -1)
        result[long_mask] = 1
        result[short_mask] = -1
        return result


class OrSignal(Signal):
    """
    OR 信号：任一信号触发即触发

    Long  = 任一信号 == 1
    Short = 任一信号 == -1
    """

    def __init__(
        self,
        *signals: Signal,
        name: Optional[str] = None,
    ) -> None:
        if len(signals) < 2:
            raise ValueError("OrSignal requires at least 2 signals")
        self._signals = signals
        self._name = name or f"OR_{'_'.join(s.name for s in signals)}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"OR({', '.join(s.name for s in self._signals)})"

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError("OrSignal 需要多信号输入，请用 SignalEngine")

    def transform_multi_signal(
        self,
        signal_values: List[pd.Series],
    ) -> pd.Series:
        result = pd.Series(0, index=signal_values[0].index, dtype=float)
        # Long: 任一 == 1
        long_mask = pd.Series(False, index=result.index)
        for sv in signal_values:
            long_mask = long_mask | (sv == 1)
        # Short: 任一 == -1
        short_mask = pd.Series(False, index=result.index)
        for sv in signal_values:
            short_mask = short_mask | (sv == -1)
        # 冲突时优先 Long（可配置）
        result[long_mask] = 1
        result[short_mask & ~long_mask] = -1
        return result


class NotSignal(Signal):
    """
    NOT 信号：取反

    1  → -1
    -1 →  1
     0 →  0
    """

    def __init__(self, signal: Signal, name: Optional[str] = None) -> None:
        self._signal = signal
        self._name = name or f"NOT_{signal.name}"

    @property
    def name(self) -> str:
        return self._name

    def transform(self, series: pd.Series) -> pd.Series:
        return -series


class MajoritySignal(Signal):
    """
    多数投票信号

    多数看多 → 1
    多数看空 → -1
    平局 → 0
    """

    def __init__(
        self,
        *signals: Signal,
        name: Optional[str] = None,
    ) -> None:
        if len(signals) < 2:
            raise ValueError("MajoritySignal requires at least 2 signals")
        self._signals = signals
        self._name = name or f"MAJ_{'_'.join(s.name for s in signals)}"

    @property
    def name(self) -> str:
        return self._name

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError("MajoritySignal 需要多信号输入，请用 SignalEngine")

    def transform_multi_signal(
        self,
        signal_values: List[pd.Series],
    ) -> pd.Series:
        # 每根 bar 统计多/空/平票数
        result = pd.Series(0, index=signal_values[0].index, dtype=float)
        for i in result.index:
            votes = [sv.loc[i] for sv in signal_values]
            longs = sum(1 for v in votes if v == 1)
            shorts = sum(1 for v in votes if v == -1)
            if longs > shorts:
                result.loc[i] = 1
            elif shorts > longs:
                result.loc[i] = -1
        return result
