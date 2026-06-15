"""
SignalEngine — V4.6 信号引擎

职责：
  - 管理信号注册
  - 批量转换因子值 → 信号
  - 支持单 symbol / 多 symbol
  - 输出最终信号 DataFrame (值域 {-1, 0, 1})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

import pandas as pd

from .base import Signal, MultiFactorSignal

logger = logging.getLogger("quantlab.signal.engine")


class SignalEngine:
    """
    信号引擎

    用法：
        engine = SignalEngine()
        engine.register(ThresholdSignal("RSI14", 30, 70))
        engine.register(CrossoverSignal("MA5", "MA20"))

        # 单 symbol
        signals = engine.transform_single(factor_values, "THRESH_RSI14_30_70")

        # 多 symbol
        result = engine.transform_all(factor_values_by_symbol, "THRESH_RSI14_30_70")
    """

    def __init__(self) -> None:
        self._signals: Dict[str, Signal] = {}

    def register(self, signal: Signal) -> Signal:
        """注册信号实例"""
        self._signals[signal.name] = signal
        logger.info(f"signal registered: {signal.name}")
        return signal

    def get(self, name: str) -> Signal:
        if name not in self._signals:
            raise KeyError(f"signal not registered: {name}")
        return self._signals[name]

    def list(self) -> List[str]:
        return list(self._signals.keys())

    # ------------------------------------------------------------------
    # 单 symbol
    # ------------------------------------------------------------------
    def transform_single(
        self,
        factor_values: Dict[str, pd.Series],
        signal_name: str,
    ) -> pd.Series:
        """单 symbol: 因子值 -> 信号"""
        sig = self._signals[signal_name]

        # 多因子信号（CrossoverSignal, BandSignal, MultiFactorSignal）
        if hasattr(sig, "transform_multi"):
            return sig.transform_multi(factor_values)

        # 单因子信号（ThresholdSignal, ZeroCrossoverSignal）
        if hasattr(sig, "factor_name"):
            series = factor_values.get(sig.factor_name)
            if series is None:
                raise KeyError(f"factor {sig.factor_name} not in factor_values")
            return sig.transform(series)

        raise ValueError(f"unknown signal type: {type(sig)}")

    # ------------------------------------------------------------------
    # 多 symbol
    # ------------------------------------------------------------------
    def transform_all(
        self,
        factor_values_by_symbol: Dict[str, Dict[str, pd.Series]],
        signal_name: str,
    ) -> pd.DataFrame:
        """
        多 symbol: 因子值 → 信号

        factor_values_by_symbol: {symbol: {factor_name: Series}}
        返回: DataFrame(index=时间, columns=symbols), 值域 {-1, 0, 1}
        """
        result: Dict[str, pd.Series] = {}
        for sym, factors in factor_values_by_symbol.items():
            result[sym] = self.transform_single(factors, signal_name)
        return pd.DataFrame(result)

    # ------------------------------------------------------------------
    # 批量
    # ------------------------------------------------------------------
    def transform_all_signals(
        self,
        factor_values_by_symbol: Dict[str, Dict[str, pd.Series]],
    ) -> Dict[str, pd.DataFrame]:
        """所有注册信号都转换"""
        results: Dict[str, pd.DataFrame] = {}
        for sig_name in self._signals:
            results[sig_name] = self.transform_all(
                factor_values_by_symbol, sig_name
            )
        return results
