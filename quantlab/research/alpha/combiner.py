"""
Alpha Combiner — Alpha 组合

支持：
  - AND 组合：两个信号同时为 1
  - OR 组合：任一信号为 1
  - Weighted 组合：加权信号值
  - Majority 组合：多数信号方向一致
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import Alpha, AlphaType

logger = logging.getLogger("quantlab.alpha.combiner")


class AlphaCombiner:
    """
    Alpha 组合器

    用法：
        combiner = AlphaCombiner()
        combined_signal = combiner.combine(
            method="weighted",
            signals={"RSI14_LT_30": sig1, "MOM20_GT_0": sig2},
            weights={"RSI14_LT_30": 0.5, "MOM20_GT_0": 0.5},
        )
    """

    def combine(
        self,
        method: str,
        signals: Dict[str, pd.Series],
        weights: Optional[Dict[str, float]] = None,
        threshold: float = 0.0,
    ) -> pd.Series:
        """
        组合多个 Alpha 信号

        参数:
            method    组合方法: "and" / "or" / "weighted" / "majority"
            signals   {alpha_name: signal_series}
            weights   权重（weighted 方法用）
            threshold 阈值（weighted 方法用，> threshold → 1）

        返回:
            组合后的信号 Series
        """
        if not signals:
            return pd.Series(dtype=float)

        if method == "and":
            return self._combine_and(signals)
        elif method == "or":
            return self._combine_or(signals)
        elif method == "weighted":
            return self._combine_weighted(signals, weights or {}, threshold)
        elif method == "majority":
            return self._combine_majority(signals)
        else:
            raise ValueError(f"unknown combine method: {method}")

    def create_composite_alpha(
        self,
        alpha_ids: List[str],
        method: str = "weighted",
        weights: Optional[Dict[str, float]] = None,
        name: Optional[str] = None,
    ) -> Alpha:
        """
        创建组合 Alpha 对象

        参数:
            alpha_ids  要组合的 Alpha ID 列表
            method     组合方法
            weights    权重
            name       组合 Alpha 名称

        返回:
            Alpha (alpha_type=COMPOSITE)
        """
        if weights is None:
            # 等权
            n = len(alpha_ids)
            weights = {aid: 1.0 / n for aid in alpha_ids}

        components = [
            {"alpha_id": aid, "weight": w}
            for aid, w in weights.items()
        ]

        return Alpha(
            alpha_type=AlphaType.COMPOSITE,
            name=name or f"Composite_{method}_{len(alpha_ids)}",
            signal_expr=f"COMBINE_{method}",
            components=components,
            combine_method=method,
        )

    def _combine_and(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """AND 组合：所有信号同时为 1"""
        df = pd.DataFrame(signals)
        result = pd.Series(0, index=df.index, dtype=float)

        # 做多：所有信号 == 1
        long_mask = (df == 1).all(axis=1)
        # 做空：所有信号 == -1
        short_mask = (df == -1).all(axis=1)

        result[long_mask] = 1
        result[short_mask] = -1
        return result

    def _combine_or(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """OR 组合：任一信号为 1"""
        df = pd.DataFrame(signals)
        result = pd.Series(0, index=df.index, dtype=float)

        long_mask = (df == 1).any(axis=1)
        short_mask = (df == -1).any(axis=1)

        result[long_mask] = 1
        result[short_mask] = -1
        return result

    def _combine_weighted(
        self,
        signals: Dict[str, pd.Series],
        weights: Dict[str, float],
        threshold: float = 0.0,
    ) -> pd.Series:
        """加权组合"""
        df = pd.DataFrame(signals)

        # 归一化权重
        total_w = sum(weights.values()) or 1.0
        for name in df.columns:
            w = weights.get(name, 1.0 / len(df.columns)) / total_w
            df[name] = df[name] * w

        combined = df.sum(axis=1)

        # 转为信号
        result = pd.Series(0, index=combined.index, dtype=float)
        result[combined > threshold] = 1
        result[combined < -threshold] = -1

        return result

    def _combine_majority(self, signals: Dict[str, pd.Series]) -> pd.Series:
        """多数投票"""
        df = pd.DataFrame(signals)

        long_count = (df == 1).sum(axis=1)
        short_count = (df == -1).sum(axis=1)
        n = len(df.columns)

        result = pd.Series(0, index=df.index, dtype=float)
        result[long_count > n / 2] = 1
        result[short_count > n / 2] = -1

        return result
