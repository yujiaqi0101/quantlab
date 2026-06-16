"""
Alpha Portfolio — 从 Alpha Pool 构建组合

流程：
  Alpha Pool → Weighting → Portfolio

支持：
  - Equal Weight
  - IC Weight
  - Risk Parity（简化版）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import Alpha
from .store import AlphaStore

logger = logging.getLogger("quantlab.alpha.portfolio")


class AlphaPortfolio:
    """
    Alpha 组合构建

    用法：
        portfolio = AlphaPortfolio(store)
        weights = portfolio.construct(method="ic_weight")
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()

    def construct(
        self,
        alphas: Optional[List[Alpha]] = None,
        method: str = "equal",
        max_alphas: int = 20,
    ) -> Dict[str, Any]:
        """
        构建组合权重

        参数:
            alphas     Alpha 列表，None 则从候选池取
            method     权重方法: "equal" / "ic_weight" / "score_weight"
            max_alphas 最多使用多少个 Alpha

        返回:
            {
                "alphas": [{"name": "RSI14_LT_30", "weight": 0.1, "ic": 0.05}, ...],
                "method": "ic_weight",
                "total_alphas": 10,
            }
        """
        if alphas is None:
            alphas = self._store.list_alphas(status="candidate", limit=max_alphas)

        if not alphas:
            return {"alphas": [], "method": method, "total_alphas": 0}

        # 按 score 排序取 top N
        alphas.sort(key=lambda a: a.metrics.score, reverse=True)
        alphas = alphas[:max_alphas]

        # 计算权重
        if method == "equal":
            weights = self._equal_weight(alphas)
        elif method == "ic_weight":
            weights = self._ic_weight(alphas)
        elif method == "score_weight":
            weights = self._score_weight(alphas)
        else:
            weights = self._equal_weight(alphas)

        result_alphas = []
        for alpha, w in zip(alphas, weights):
            result_alphas.append({
                "alpha_id": alpha.alpha_id,
                "name": alpha.name,
                "factor_name": alpha.factor_name,
                "weight": round(w, 4),
                "ic": alpha.metrics.ic,
                "ir": alpha.metrics.ir,
                "score": alpha.metrics.score,
            })

        return {
            "alphas": result_alphas,
            "method": method,
            "total_alphas": len(result_alphas),
        }

    def _equal_weight(self, alphas: List[Alpha]) -> List[float]:
        """等权"""
        n = len(alphas)
        return [1.0 / n] * n

    def _ic_weight(self, alphas: List[Alpha]) -> List[float]:
        """IC 加权"""
        ics = [max(a.metrics.ic, 0) for a in alphas]
        total = sum(ics) or 1.0
        return [ic / total for ic in ics]

    def _score_weight(self, alphas: List[Alpha]) -> List[float]:
        """Score 加权"""
        scores = [max(a.metrics.score, 0) for a in alphas]
        total = sum(scores) or 1.0
        return [s / total for s in scores]
