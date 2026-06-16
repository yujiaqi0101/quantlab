"""
Signal Builder — V4.7 可视化信号构建器

用户无需写代码，通过选择因子 + 操作符 + 阈值即可构建信号。

支持：
  1. Threshold: factor < value → 1, factor > value → -1
  2. Crossover: fast_factor crosses slow_factor
  3. ZeroCross: factor crosses zero
  4. Band: factor < lower_band or factor > upper_band
  5. Composite: AND / OR / NOT / Majority 组合多个信号

用法（API 驱动）：
    builder = SignalBuilder(registry=FactorRegistry(), engine=SignalEngine())

    # 单因子阈值信号
    signal = builder.build_threshold("RSI14", "<", 30, direction="long")
    # → ThresholdSignal("RSI14", lower=30, upper=70)

    # 交叉信号
    signal = builder.build_crossover("MA5", "MA20")
    # → CrossoverSignal("MA5", "MA20")

    # 组合信号
    signal = builder.build_composite(["rsi_long", "mom_long"], "AND")
    # → AndSignal(...)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .base import Signal, MultiFactorSignal
from .threshold import ThresholdSignal
from .crossover import CrossoverSignal, ZeroCrossoverSignal
from .composite import AndSignal, OrSignal, NotSignal, MajoritySignal
from .signal_engine import SignalEngine

logger = logging.getLogger("quantlab.signal.builder")


class SignalBuilder:
    """
    可视化信号构建器

    核心能力：
      - 从参数构建 Signal 对象（无需写代码）
      - 即时预览信号结果
      - 保存信号定义到注册中心
    """

    def __init__(self, engine: SignalEngine) -> None:
        self.engine = engine

    def build_threshold(
        self,
        factor_name: str,
        operator: str,
        value: float,
        direction: str = "long",
        signal_name: Optional[str] = None,
    ) -> Signal:
        """
        构建阈值信号

        参数:
            factor_name  因子名称
            operator     比较操作符: "<", "<=", ">", ">=", "=="
            value        阈值
            direction    "long" 或 "short" 或 "both"
            signal_name  自定义信号名
        """
        if direction == "long":
            if operator in ("<", "<="):
                lower, upper = value, 999999
            elif operator in (">", ">="):
                lower, upper = -999999, value
            else:
                lower, upper = value, value
            sig = ThresholdSignal(
                factor_name, lower, upper,
                signal_name=signal_name or f"{factor_name}_{operator}_{value}_LONG",
            )
        elif direction == "short":
            if operator in ("<", "<="):
                lower, upper = -999999, value
            elif operator in (">", ">="):
                lower, upper = value, 999999
            else:
                lower, upper = value, value
            sig = ThresholdSignal(
                factor_name, lower, upper,
                signal_name=signal_name or f"{factor_name}_{operator}_{value}_SHORT",
            )
        else:
            # both: 需要上下阈值
            if operator in ("<", "<="):
                sig = ThresholdSignal(
                    factor_name, value, 999999,
                    signal_name=signal_name or f"{factor_name}_{operator}_{value}",
                )
            else:
                sig = ThresholdSignal(
                    factor_name, -999999, value,
                    signal_name=signal_name or f"{factor_name}_{operator}_{value}",
                )

        self.engine.register(sig)
        return sig

    def build_crossover(
        self,
        fast_factor: str,
        slow_factor: str,
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建交叉信号"""
        sig = CrossoverSignal(
            fast_factor, slow_factor,
            signal_name=signal_name or f"CROSS_{fast_factor}_{slow_factor}",
        )
        self.engine.register(sig)
        return sig

    def build_zero_cross(
        self,
        factor_name: str,
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建零轴交叉信号"""
        sig = ZeroCrossoverSignal(
            factor_name,
            signal_name=signal_name or f"ZERO_CROSS_{factor_name}",
        )
        self.engine.register(sig)
        return sig

    def build_composite(
        self,
        signal_names: List[str],
        logic: str = "AND",
        signal_name: Optional[str] = None,
    ) -> Signal:
        """
        构建组合信号

        参数:
            signal_names  子信号名称列表
            logic         "AND" / "OR" / "MAJORITY"
            signal_name   自定义信号名
        """
        signals = [self.engine.get(name) for name in signal_names]

        if logic == "AND":
            sig = AndSignal(*signals, name=signal_name)
        elif logic == "OR":
            sig = OrSignal(*signals, name=signal_name)
        elif logic == "MAJORITY":
            sig = MajoritySignal(*signals, name=signal_name)
        else:
            raise ValueError(f"Unknown logic: {logic}")

        self.engine.register(sig)
        return sig

    def preview(
        self,
        signal: Signal,
        factor_values: Dict[str, pd.Series],
        n: int = 20,
    ) -> Dict[str, Any]:
        """
        预览信号结果

        返回:
            signal_name   信号名称
            values        信号值序列
            coverage      覆盖率
            trigger_count 触发次数
            trigger_pct   触发比例
        """
        # 生成信号
        if isinstance(signal, MultiFactorSignal) or isinstance(signal, CrossoverSignal):
            sig_values = signal.transform_multi(factor_values)
        elif isinstance(signal, ThresholdSignal) or isinstance(signal, ZeroCrossoverSignal):
            if hasattr(signal, "factor_name"):
                series = factor_values.get(signal.factor_name)
                if series is None:
                    raise KeyError(f"factor {signal.factor_name} not found")
                sig_values = signal.transform(series)
            else:
                sig_values = signal.transform(list(factor_values.values())[0])
        else:
            sig_values = signal.transform(list(factor_values.values())[0])

        total = len(sig_values)
        long_count = int((sig_values == 1).sum())
        short_count = int((sig_values == -1).sum())
        neutral_count = int((sig_values == 0).sum())

        return {
            "signal_name": signal.name,
            "total_bars": total,
            "long_count": long_count,
            "short_count": short_count,
            "neutral_count": neutral_count,
            "coverage": round((long_count + short_count) / total, 4) if total > 0 else 0,
            "long_pct": round(long_count / total, 4) if total > 0 else 0,
            "short_pct": round(short_count / total, 4) if total > 0 else 0,
        }
