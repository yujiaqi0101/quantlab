"""
Alpha Decay — 信号衰减分析

测试 Signal(t) 对 Return(t+1), Return(t+5), Return(t+10), Return(t+20) 的预测能力

输出 Decay Curve，判断 Alpha 半衰期
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import Alpha

logger = logging.getLogger("quantlab.alpha.decay")


class AlphaDecay:
    """
    Alpha 衰减分析

    用法：
        decay = AlphaDecay()
        result = decay.analyze(alpha, factor_values, price_df)
        # result = {"1d": 0.8%, "5d": 0.5%, "10d": 0.1%, "20d": -0.1%, "half_life": 10}
    """

    DEFAULT_PERIODS = [1, 2, 3, 5, 10, 20, 40, 60]

    def __init__(self, periods: Optional[List[int]] = None) -> None:
        self._periods = periods or self.DEFAULT_PERIODS

    def analyze(
        self,
        alpha: Alpha,
        factor_values: pd.Series,
        price_df: pd.DataFrame,
        periods: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        分析 Alpha 衰减

        参数:
            alpha         Alpha 对象
            factor_values 因子值 Series
            price_df      价格 DataFrame
            periods       前瞻周期列表

        返回:
            {"1d": 0.008, "5d": 0.005, ..., "half_life": 10, "decay_curve": [...]}
        """
        from .evaluator import AlphaEvaluator

        if periods is None:
            periods = self._periods

        evaluator = AlphaEvaluator()
        signals = evaluator._generate_signals(alpha, factor_values)

        if signals is None or signals.empty:
            return {"decay_curve": [], "half_life": None}

        close = price_df["close"] if "close" in price_df.columns else price_df.iloc[:, 0]

        # 计算各周期前瞻收益
        decay_points = []
        for p in periods:
            forward_ret = close.shift(-p) / close - 1
            aligned = forward_ret.reindex(signals.index)
            long_mask = signals == 1

            rets = aligned[long_mask].dropna()
            if rets.empty:
                decay_points.append({"period": p, "forward_return": 0.0})
            else:
                decay_points.append({
                    "period": p,
                    "forward_return": round(float(rets.mean()), 6),
                })

        # 计算半衰期
        half_life = self._estimate_half_life(decay_points)

        return {
            "alpha_id": alpha.alpha_id,
            "alpha_name": alpha.name,
            "decay_curve": decay_points,
            "half_life": half_life,
        }

    def analyze_batch(
        self,
        alphas: List[Alpha],
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量衰减分析

        返回:
            {alpha_id: decay_result}
        """
        results = {}
        for alpha in alphas:
            fv = factor_data.get(alpha.factor_name)
            if fv is None:
                continue
            results[alpha.alpha_id] = self.analyze(alpha, fv, price_df)
        return results

    def _estimate_half_life(self, decay_points: List[Dict[str, Any]]) -> Optional[float]:
        """
        估算半衰期

        找到 forward_return 降到峰值一半的周期
        """
        if len(decay_points) < 2:
            return None

        # 取第一个正收益作为峰值
        peak_ret = None
        for dp in decay_points:
            if dp["forward_return"] > 0:
                peak_ret = dp["forward_return"]
                break

        if peak_ret is None or peak_ret <= 0:
            return None

        half_ret = peak_ret / 2

        # 线性插值找半衰期
        for i in range(len(decay_points) - 1):
            r1 = decay_points[i]["forward_return"]
            r2 = decay_points[i + 1]["forward_return"]
            p1 = decay_points[i]["period"]
            p2 = decay_points[i + 1]["period"]

            if r1 >= half_ret >= r2:
                # 线性插值
                if abs(r1 - r2) < 1e-9:
                    return float(p1)
                t = (r1 - half_ret) / (r1 - r2)
                half_life = p1 + t * (p2 - p1)
                return round(float(half_life), 1)

        # 如果没有衰减到一半，返回最大周期
        return float(decay_points[-1]["period"])
