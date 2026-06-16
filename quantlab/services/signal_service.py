"""
SignalService — 信号业务入口

V2.0 重构：统一封装信号构建、预览、可视化、前瞻收益、组合
API 层只调本 Service，不直接碰 SignalEngine / SignalBuilder
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..signal.signal_engine import SignalEngine
from ..signal.builder import SignalBuilder
from ..signal.base import Signal, MultiFactorSignal
from ..signal.threshold import ThresholdSignal
from ..signal.crossover import CrossoverSignal, ZeroCrossoverSignal
from ..signal.composite import AndSignal, OrSignal, MajoritySignal
from ..factor.registry import FactorRegistry
from ..factor.cache import FactorCache
from ..factor.technical import (
    MAFactor, RSIFactor, MomentumFactor, ATRFactor,
    BOLLUpperFactor, BOLLLowerFactor, VOLFactor,
)

logger = logging.getLogger("quantlab.services.signal")


class SignalService:
    """
    信号服务（Facade）

    统一入口：
      - 列出信号 / 详情
      - 构建 Threshold/Crossover/Composite 信号
      - 预览信号（Coverage/触发统计）
      - 信号可视化数据
      - 前瞻收益分析
      - 信号组合
    """

    def __init__(
        self,
        engine: Optional[SignalEngine] = None,
    ) -> None:
        self._engine = engine or SignalEngine()
        self._builder = SignalBuilder(self._engine)
        self._register_default_signals()

        # 因子相关（用于信号计算）
        self._factor_registry = FactorRegistry()
        self._register_builtin_factors()
        self._factor_cache = FactorCache(self._factor_registry)

    def _register_default_signals(self) -> None:
        """注册默认信号"""
        self._engine.register(ThresholdSignal("RSI14", 30, 70, "RSI_Oversold_Overbought"))
        self._engine.register(ThresholdSignal("RSI6", 20, 80, "RSI6_Extreme"))
        self._engine.register(ZeroCrossoverSignal("MOM20", "MOM20_ZeroCross"))
        self._engine.register(CrossoverSignal("MA5", "MA20", "MA_Cross_5_20"))

    def _register_builtin_factors(self) -> None:
        """注册内置因子"""
        for period in [5, 10, 20, 60]:
            self._factor_registry.register(lambda p=period: MAFactor(p))
        for period in [6, 14, 28]:
            self._factor_registry.register(lambda p=period: RSIFactor(p))
        for period in [5, 10, 20, 60]:
            self._factor_registry.register(lambda p=period: MomentumFactor(p))
        for period in [14, 28]:
            self._factor_registry.register(lambda p=period: ATRFactor(p))
        for period in [5, 20]:
            self._factor_registry.register(lambda p=period: VOLFactor(p))

    # ---- 查询 ----

    def list_signals(self) -> List[Dict[str, Any]]:
        """列出所有已注册信号"""
        result = []
        for name in self._engine.list():
            sig = self._engine.get(name)
            info: Dict[str, Any] = {
                "name": sig.name,
                "description": sig.description,
                "type": type(sig).__name__,
            }
            if isinstance(sig, ThresholdSignal):
                info["factor_name"] = sig.factor_name
                info["lower"] = sig.lower
                info["upper"] = sig.upper
            elif isinstance(sig, CrossoverSignal):
                info["fast_factor"] = sig.fast_factor_name
                info["slow_factor"] = sig.slow_factor_name
            elif isinstance(sig, ZeroCrossoverSignal):
                info["factor_name"] = sig.factor_name
            elif isinstance(sig, (AndSignal, OrSignal, MajoritySignal)):
                info["sub_signals"] = [s.name for s in sig._signals]
                info["logic"] = type(sig).__name__.replace("Signal", "")
            result.append(info)
        return result

    def get_signal(self, name: str) -> Optional[Signal]:
        """获取信号"""
        return self._engine.get(name) if self._engine.has(name) else None

    def has_signal(self, name: str) -> bool:
        """检查信号是否存在"""
        return self._engine.has(name)

    # ---- 构建 ----

    def build_threshold(
        self,
        factor_name: str,
        operator: str,
        value: float,
        direction: str = "long",
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建阈值信号"""
        return self._builder.build_threshold(factor_name, operator, value, direction, signal_name)

    def build_crossover(
        self,
        fast_factor: str,
        slow_factor: str,
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建交叉信号"""
        return self._builder.build_crossover(fast_factor, slow_factor, signal_name)

    def build_zero_cross(
        self,
        factor_name: str,
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建零轴交叉信号"""
        return self._builder.build_zero_cross(factor_name, signal_name)

    def build_composite(
        self,
        signal_names: List[str],
        logic: str = "AND",
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建组合信号"""
        return self._builder.build_composite(signal_names, logic, signal_name)

    # ---- 因子计算 ----

    def compute_factor_values(self, df: pd.DataFrame, dataset_id: str = "", symbol: str = "") -> Dict[str, pd.Series]:
        """计算所有注册因子的值"""
        factor_names = self._factor_registry.list()
        return self._factor_cache.compute_batch(factor_names, df, dataset_id=dataset_id, symbol=symbol)

    # ---- 信号生成 ----

    def generate_signal(self, signal: Signal, factor_values: Dict[str, pd.Series]) -> pd.Series:
        """根据信号类型生成信号值"""
        if isinstance(signal, (CrossoverSignal,)):
            return signal.transform_multi(factor_values)
        elif isinstance(signal, (MultiFactorSignal,)):
            return signal.transform_multi(factor_values)
        elif isinstance(signal, (ThresholdSignal, ZeroCrossoverSignal)):
            if hasattr(signal, "factor_name"):
                series = factor_values.get(signal.factor_name)
                if series is None:
                    raise ValueError(f"Factor '{signal.factor_name}' not available")
                return signal.transform(series)
        first_series = list(factor_values.values())[0]
        return signal.transform(first_series)

    # ---- 预览 ----

    def preview(
        self,
        signal_name: str,
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
    ) -> Dict[str, Any]:
        """预览信号结果"""
        signal = self._engine.get(signal_name)
        if not signal:
            return {"error": f"Signal '{signal_name}' not found"}

        factor_values = self.compute_factor_values(df, dataset_id, symbol)
        sig_values = self.generate_signal(signal, factor_values)

        total = len(sig_values)
        long_count = int((sig_values == 1).sum())
        short_count = int((sig_values == -1).sum())

        return {
            "signal_name": signal_name,
            "total_bars": total,
            "long_count": long_count,
            "short_count": short_count,
            "neutral_count": total - long_count - short_count,
            "coverage": round((long_count + short_count) / total, 4) if total > 0 else 0,
            "long_pct": round(long_count / total, 4) if total > 0 else 0,
            "short_pct": round(short_count / total, 4) if total > 0 else 0,
        }

    # ---- 前瞻收益 ----

    def forward_return(
        self,
        signal_name: str,
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        forward_periods: List[int] = None,
    ) -> Dict[str, Any]:
        """前瞻收益分析"""
        if forward_periods is None:
            forward_periods = [1, 5, 10, 20]

        signal = self._engine.get(signal_name)
        if not signal:
            return {"error": f"Signal '{signal_name}' not found"}

        factor_values = self.compute_factor_values(df, dataset_id, symbol)
        sig_values = self.generate_signal(signal, factor_values)
        close = df["close"]

        results = {}
        for period in forward_periods:
            fwd_return = close.pct_change(period).shift(-period)

            long_mask = sig_values == 1
            long_returns = fwd_return[long_mask].dropna()
            short_mask = sig_values == -1
            short_returns = fwd_return[short_mask].dropna()
            all_mask = sig_values != 0
            all_returns = fwd_return[all_mask].dropna()

            results[f"fwd_{period}"] = {
                "long": {
                    "mean": round(float(long_returns.mean()), 6) if len(long_returns) > 0 else 0,
                    "median": round(float(long_returns.median()), 6) if len(long_returns) > 0 else 0,
                    "win_rate": round(float((long_returns > 0).mean()), 4) if len(long_returns) > 0 else 0,
                    "count": len(long_returns),
                    "std": round(float(long_returns.std()), 6) if len(long_returns) > 1 else 0,
                },
                "short": {
                    "mean": round(float(short_returns.mean()), 6) if len(short_returns) > 0 else 0,
                    "median": round(float(short_returns.median()), 6) if len(short_returns) > 0 else 0,
                    "win_rate": round(float((short_returns > 0).mean()), 4) if len(short_returns) > 0 else 0,
                    "count": len(short_returns),
                    "std": round(float(short_returns.std()), 6) if len(short_returns) > 1 else 0,
                },
                "all": {
                    "mean": round(float(all_returns.mean()), 6) if len(all_returns) > 0 else 0,
                    "win_rate": round(float((all_returns > 0).mean()), 4) if len(all_returns) > 0 else 0,
                    "count": len(all_returns),
                },
            }

        return {"signal_name": signal_name, "forward_returns": results}

    # ---- 注册装饰器 ----

    def register_decorator(self):
        """返回 @register_signal 装饰器"""
        def decorator(cls):
            instance = cls()
            self._engine.register(instance)
            return cls
        return decorator
