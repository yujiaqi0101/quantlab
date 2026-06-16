"""
Alpha Ranking — 评分排序

评分公式：
  score = w_ic * normalize(ic) + w_ir * normalize(ir) + w_sharpe * normalize(sharpe) + w_stability * normalize(stability)

输出 Alpha Leaderboard
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .alpha import Alpha, AlphaMetrics
from .store import AlphaStore

logger = logging.getLogger("quantlab.alpha.ranking")


class AlphaRanking:
    """
    Alpha 排名

    支持多种排名方式：
      - 综合评分（默认）
      - 单指标排名（ic, ir, sharpe, coverage）
      - 自定义权重
    """

    DEFAULT_WEIGHTS = {
        "ic": 0.30,
        "ir": 0.30,
        "sharpe": 0.20,
        "stability": 0.20,
    }

    def __init__(
        self,
        store: Optional[AlphaStore] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._store = store or AlphaStore()
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()

    def get_leaderboard(
        self,
        metric: str = "score",
        limit: int = 20,
        factor_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取排行榜

        参数:
            metric       排名指标: score / ic / rank_ic / ir / coverage / sharpe
            limit        返回数量
            factor_name  限定因子

        返回:
            [{"rank": 1, "alpha_id": "xxx", "name": "RSI14_LT_30", "ic": 0.05, ...}, ...]
        """
        alphas = self._store.list_alphas(limit=1000)
        if factor_name:
            alphas = [a for a in alphas if a.factor_name == factor_name]

        # 排序
        reverse = True
        if metric == "score":
            alphas.sort(key=lambda a: a.metrics.score, reverse=True)
        elif metric == "ic":
            alphas.sort(key=lambda a: a.metrics.ic, reverse=True)
        elif metric == "rank_ic":
            alphas.sort(key=lambda a: a.metrics.rank_ic, reverse=True)
        elif metric == "ir":
            alphas.sort(key=lambda a: a.metrics.ir, reverse=True)
        elif metric == "coverage":
            alphas.sort(key=lambda a: a.metrics.coverage, reverse=True)
        elif metric == "sharpe":
            alphas.sort(key=lambda a: a.metrics.sharpe, reverse=True)
        else:
            alphas.sort(key=lambda a: a.metrics.score, reverse=True)

        result = []
        for i, alpha in enumerate(alphas[:limit]):
            d = alpha.to_dict()
            d["rank"] = i + 1
            result.append(d)

        return result

    def rescore(self, alphas: Optional[List[Alpha]] = None) -> List[Alpha]:
        """
        重新计算评分

        参数:
            alphas  要重算的 Alpha 列表，None 则从 store 加载全部

        返回:
            重新评分后的 Alpha 列表
        """
        if alphas is None:
            alphas = self._store.list_alphas(limit=10000)

        for alpha in alphas:
            alpha.metrics.score = self._compute_score(alpha.metrics)
            self._store.save(alpha)

        logger.info(f"rescored {len(alphas)} alphas")
        return alphas

    def _compute_score(self, metrics: AlphaMetrics) -> float:
        """计算综合评分"""
        w = self._weights

        ic_score = min(max(metrics.ic / 0.1, 0), 1)
        ir_score = min(max(metrics.ir / 1.0, 0), 1)
        sharpe_score = min(max(metrics.sharpe / 2.0, 0), 1)
        stability_score = metrics.ic_positive_ratio

        score = (
            w.get("ic", 0.3) * ic_score
            + w.get("ir", 0.3) * ir_score
            + w.get("sharpe", 0.2) * sharpe_score
            + w.get("stability", 0.2) * stability_score
        )

        return round(float(score), 4)

    def set_weights(self, weights: Dict[str, float]) -> None:
        """更新评分权重"""
        self._weights = weights
