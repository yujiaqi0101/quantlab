"""
Signal Filters — V4.6 信号过滤器

在 Signal 输出后做后处理：
  - HoldFilter: 信号发出后至少持有 N 根 bar
  - ConfirmFilter: 信号需连续 N 根 bar 确认
  - CooldownFilter: 平仓后冷却 N 根 bar
  - StatefulSignal: 将脉冲信号转为持续状态

用法：
    raw_signal = threshold_signal.transform(rsi_series)
    filtered = HoldFilter(min_hold=5).apply(raw_signal)
    filtered = ConfirmFilter(confirm_bars=2).apply(raw_signal)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


class HoldFilter:
    """
    持仓过滤：信号发出后至少持有 min_hold 根 bar

    避免频繁交易（信号闪烁）
    """

    def __init__(self, min_hold: int = 5) -> None:
        self.min_hold = min_hold

    def apply(self, signal: pd.Series) -> pd.Series:
        result = signal.copy()
        current_pos = 0
        hold_count = 0
        values = result.values.copy()

        for i in range(len(values)):
            new_pos = int(values[i])
            if new_pos != 0 and new_pos != current_pos:
                if current_pos != 0 and hold_count < self.min_hold:
                    # 还没持有够，保持当前仓位
                    values[i] = current_pos
                    hold_count += 1
                else:
                    current_pos = new_pos
                    hold_count = 1
            elif current_pos != 0:
                hold_count += 1
                # 持仓期间保持仓位（除非有反向信号）
                if new_pos == 0 and hold_count < self.min_hold:
                    values[i] = current_pos

        return pd.Series(values, index=signal.index, dtype=float)


class ConfirmFilter:
    """
    确认过滤：信号需连续 confirm_bars 根 bar 确认

    避免假信号
    """

    def __init__(self, confirm_bars: int = 2) -> None:
        self.confirm_bars = confirm_bars

    def apply(self, signal: pd.Series) -> pd.Series:
        result = pd.Series(0, index=signal.index, dtype=float)
        values = signal.values
        current_pos = 0
        streak = 0

        for i in range(len(values)):
            v = int(values[i])
            if v == current_pos:
                streak += 1
            elif v != 0:
                streak = 1
                if streak >= self.confirm_bars:
                    current_pos = v
                    result.iloc[i] = v
            else:
                streak = 0
                current_pos = 0

            if streak >= self.confirm_bars and v != 0:
                result.iloc[i] = v
                current_pos = v

        return result


class CooldownFilter:
    """
    冷却过滤：平仓后冷却 cooldown_bars 根 bar 才能再次开仓

    避免反复进出
    """

    def __init__(self, cooldown_bars: int = 5) -> None:
        self.cooldown_bars = cooldown_bars

    def apply(self, signal: pd.Series) -> pd.Series:
        result = signal.copy()
        values = result.values.copy()
        cooldown_remaining = 0
        prev_pos = 0

        for i in range(len(values)):
            new_pos = int(values[i])
            if cooldown_remaining > 0:
                # 冷却中，强制空仓
                values[i] = 0
                cooldown_remaining -= 1
            elif new_pos != 0 and prev_pos == 0:
                # 新开仓
                prev_pos = new_pos
            elif new_pos == 0 and prev_pos != 0:
                # 平仓，开始冷却
                cooldown_remaining = self.cooldown_bars
                prev_pos = 0
            elif new_pos != 0 and new_pos != prev_pos:
                # 反向信号（先平仓再冷却）
                cooldown_remaining = self.cooldown_bars
                values[i] = 0
                prev_pos = 0

        return pd.Series(values, index=signal.index, dtype=float)


class StatefulSignal:
    """
    状态信号：将脉冲信号转为持续状态

    脉冲信号：只在触发 bar 有值（如交叉信号）
    状态信号：触发后保持直到反向信号

    用法：
        stateful = StatefulSignal().apply(cross_signal)
    """

    def apply(self, signal: pd.Series) -> pd.Series:
        result = pd.Series(0, index=signal.index, dtype=float)
        state = 0
        values = signal.values

        for i in range(len(values)):
            v = int(values[i])
            if v == 1:
                state = 1
            elif v == -1:
                state = -1
            # v == 0 时保持状态
            result.iloc[i] = state

        return result
