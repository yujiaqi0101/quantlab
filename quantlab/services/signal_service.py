"""
SignalService — 信号业务入口

封装：信号构建、预览、可视化、前瞻收益、组合
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..signal.signal_engine import SignalEngine
from ..signal.builder import SignalBuilder
from ..signal.base import Signal

logger = logging.getLogger("quantlab.services.signal")


class SignalService:
    """
    信号服务（Facade）

    统一入口：
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

    # ---- 查询 ----

    def list_signals(self) -> List[Dict[str, Any]]:
        """列出所有已注册信号"""
        return self._engine.list_signals()

    def get_signal(self, name: str) -> Optional[Signal]:
        """获取信号"""
        return self._engine.get(name) if self._engine.has(name) else None

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
        return self._builder.build_threshold(
            factor_name, operator, value, direction, signal_name
        )

    def build_crossover(
        self,
        fast_factor: str,
        slow_factor: str,
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建交叉信号"""
        return self._builder.build_crossover(fast_factor, slow_factor, signal_name)

    def build_composite(
        self,
        signal_names: List[str],
        logic: str = "AND",
        signal_name: Optional[str] = None,
    ) -> Signal:
        """构建组合信号"""
        return self._builder.build_composite(signal_names, logic, signal_name)

    # ---- 预览 ----

    def preview(
        self,
        signal_name: str,
        factor_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """预览信号结果"""
        signal = self._engine.get(signal_name)
        if not signal:
            return {"error": f"Signal '{signal_name}' not found"}

        values = signal.generate(factor_data)
        total = len(values)
        long_count = int(np.sum(values == 1))
        short_count = int(np.sum(values == -1))
        neutral_count = int(np.sum(values == 0))

        return {
            "signal_name": signal_name,
            "total_bars": total,
            "long_count": long_count,
            "short_count": short_count,
            "neutral_count": neutral_count,
            "long_pct": round(long_count / total * 100, 1) if total else 0,
            "short_pct": round(short_count / total * 100, 1) if total else 0,
        }

    # ---- 前瞻收益 ----

    def forward_return(
        self,
        signal_name: str,
        factor_data: pd.DataFrame,
        close: pd.Series,
        forward_periods: List[int] = [1, 5, 10, 20],
    ) -> Dict[str, Any]:
        """前瞻收益分析"""
        signal = self._engine.get(signal_name)
        if not signal:
            return {"error": f"Signal '{signal_name}' not found"}

        values = signal.generate(factor_data)
        results = {}

        for period in forward_periods:
            fwd_return = close.pct_change(period).shift(-period)
            long_mask = values == 1
            long_returns = fwd_return[long_mask].dropna()

            results[f"fwd_{period}"] = {
                "long": {
                    "mean": round(float(long_returns.mean()), 6) if len(long_returns) else 0,
                    "win_rate": round(float((long_returns > 0).mean()), 4) if len(long_returns) else 0,
                    "count": len(long_returns),
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
