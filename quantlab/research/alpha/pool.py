"""
Candidate Pool — Alpha 候选池

筛选条件：
  IC > 0.03
  IR > 0.5
  Coverage > 0.05

满足条件的 Alpha 进入候选池，状态变为 candidate
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .alpha import Alpha, AlphaStatus
from .store import AlphaStore

logger = logging.getLogger("quantlab.alpha.pool")


class CandidatePool:
    """
    候选池

    自动筛选优秀 Alpha 进入候选池
    """

    DEFAULT_CRITERIA = {
        "ic_min": 0.03,
        "ir_min": 0.5,
        "coverage_min": 0.05,
        "win_rate_min": 0.0,
    }

    def __init__(
        self,
        store: Optional[AlphaStore] = None,
        criteria: Optional[Dict[str, float]] = None,
    ) -> None:
        self._store = store or AlphaStore()
        self._criteria = criteria or self.DEFAULT_CRITERIA.copy()

    def screen(
        self,
        alphas: Optional[List[Alpha]] = None,
    ) -> List[Alpha]:
        """
        筛选候选 Alpha

        参数:
            alphas  要筛选的 Alpha 列表，None 则从 store 加载全部已评估的

        返回:
            通过筛选的 Alpha 列表
        """
        if alphas is None:
            alphas = self._store.list_alphas(status="evaluated")

        candidates = []
        for alpha in alphas:
            if self._passes(alpha):
                alpha.status = AlphaStatus.CANDIDATE
                self._store.save(alpha)
                candidates.append(alpha)

        logger.info(f"screened {len(candidates)} candidates from {len(alphas)} alphas")
        return candidates

    def get_candidates(
        self,
        factor_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Alpha]:
        """获取候选池 Alpha"""
        alphas = self._store.list_alphas(status="candidate", limit=limit)
        if factor_name:
            alphas = [a for a in alphas if a.factor_name == factor_name]
        return alphas

    def remove_from_pool(self, alpha_id: str) -> bool:
        """从候选池移除（状态改回 evaluated）"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return False
        alpha.status = AlphaStatus.EVALUATED
        self._store.save(alpha)
        return True

    def promote_to_production(self, alpha_id: str) -> bool:
        """提升为生产"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return False
        alpha.status = AlphaStatus.PRODUCTION
        self._store.save(alpha)
        logger.info(f"alpha '{alpha.name}' promoted to production")
        return True

    def _passes(self, alpha: Alpha) -> bool:
        """检查是否通过筛选"""
        m = alpha.metrics
        c = self._criteria

        if m.ic < c.get("ic_min", 0.03):
            return False
        if m.ir < c.get("ir_min", 0.5):
            return False
        if m.coverage < c.get("coverage_min", 0.05):
            return False
        if m.win_rate < c.get("win_rate_min", 0.0):
            return False

        return True

    def set_criteria(self, criteria: Dict[str, float]) -> None:
        """更新筛选条件"""
        self._criteria = criteria

    def get_criteria(self) -> Dict[str, float]:
        """获取当前筛选条件"""
        return dict(self._criteria)

    def get_pool_stats(self) -> Dict[str, Any]:
        """候选池统计"""
        candidates = self._store.list_alphas(status="candidate", limit=10000)
        if not candidates:
            return {"count": 0, "factors": [], "avg_ic": 0, "avg_ir": 0}

        ics = [a.metrics.ic for a in candidates]
        irs = [a.metrics.ir for a in candidates]
        factors = list(set(a.factor_name for a in candidates))

        return {
            "count": len(candidates),
            "factors": factors,
            "avg_ic": round(sum(ics) / len(ics), 4),
            "avg_ir": round(sum(irs) / len(irs), 4),
        }
