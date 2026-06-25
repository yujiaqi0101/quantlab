"""
组合构建层 (portfolio_construction)
==================================

把策略信号转换为目标持仓权重。

类:
    PortfolioConstructor — 抽象基类
    EqualWeight          — score>0 的标的等权
    TopN                 — 取 score 降序前 N 等权 (动量轮动)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict

import pandas as pd

__all__ = ["TargetPortfolio", "PortfolioConstructor", "EqualWeight", "TopN"]


@dataclass
class TargetPortfolio:
    """目标持仓: {symbol: weight}。"""
    timestamp: pd.Timestamp
    weights: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        for w in self.weights.values():
            if w < 0:
                raise ValueError(f"权重不能为负: {w}")

    @property
    def symbols(self) -> list:
        return [s for s, w in self.weights.items() if w > 0]

    @property
    def total_weight(self) -> float:
        return sum(self.weights.values())


class PortfolioConstructor(ABC):
    """组合构造器抽象基类。"""

    @abstractmethod
    def construct(self, scores: pd.Series, timestamp: pd.Timestamp) -> TargetPortfolio:
        """根据截面信号 scores 构造目标组合。

        Args:
            scores: 当期截面信号 (index=symbol)，NaN 视为不参与
            timestamp: 当前时间戳

        Returns:
            TargetPortfolio 目标持仓
        """
        ...


class EqualWeight(PortfolioConstructor):
    """score>0 的标的等权 1/N。"""

    def construct(self, scores: pd.Series, timestamp: pd.Timestamp) -> TargetPortfolio:
        picked = scores[scores > 0].dropna()
        if picked.empty:
            return TargetPortfolio(timestamp=timestamp, weights={})
        w = 1.0 / len(picked)
        return TargetPortfolio(
            timestamp=timestamp,
            weights={s: w for s in picked.index},
        )


class TopN(PortfolioConstructor):
    """取 score 降序前 N 个等权 1/N。

    用于动量轮动 / 行业 ETF 轮动。
    """

    def __init__(self, n: int = 2):
        if n < 1:
            raise ValueError(f"n 必须 >= 1, 实际: {n}")
        self.n = n

    def construct(self, scores: pd.Series, timestamp: pd.Timestamp) -> TargetPortfolio:
        valid = scores.dropna()
        if valid.empty:
            return TargetPortfolio(timestamp=timestamp, weights={})
        picked = valid.sort_values(ascending=False).head(self.n)
        if picked.empty:
            return TargetPortfolio(timestamp=timestamp, weights={})
        w = 1.0 / len(picked)
        return TargetPortfolio(
            timestamp=timestamp,
            weights={s: w for s in picked.index},
        )
