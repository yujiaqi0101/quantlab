"""
FactorService — 因子业务入口

V2.0 重构：统一封装因子注册、计算、IC分析、可视化
API 层只调本 Service，不直接碰 FactorRegistry / FactorEngine / FactorCache
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..factor.registry import FactorRegistry
from ..factor.factor_engine import FactorEngine
from ..factor.cache import FactorCache
from ..factor.ic_analysis import (
    compute_ic,
    compute_ic_stats,
    compute_factor_correlation,
    compute_turnover,
    compute_coverage,
)
from ..factor.technical import (
    MAFactor, RSIFactor, MomentumFactor, ATRFactor,
    BOLLUpperFactor, BOLLLowerFactor, VOLFactor,
)

logger = logging.getLogger("quantlab.services.factor")


class FactorService:
    """
    因子服务（Facade）

    统一入口：
      - 列出因子 / 分类 / 详情
      - 计算因子值（含缓存）
      - IC 分析 / 相关性
      - 可视化数据
    """

    def __init__(
        self,
        registry: Optional[FactorRegistry] = None,
        engine: Optional[FactorEngine] = None,
    ) -> None:
        self._registry = registry or FactorRegistry()
        self._engine = engine or FactorEngine(self._registry)
        self._cache = FactorCache(self._registry)
        self._register_builtin_factors()

    def _register_builtin_factors(self) -> None:
        """注册所有内置因子"""
        for period in [5, 10, 20, 60]:
            self._registry.register(lambda p=period: MAFactor(p))
        for period in [6, 14, 28]:
            self._registry.register(lambda p=period: RSIFactor(p))
        for period in [5, 10, 20, 60]:
            self._registry.register(lambda p=period: MomentumFactor(p))
        for period in [14, 28]:
            self._registry.register(lambda p=period: ATRFactor(p))
        for period in [20]:
            self._registry.register(lambda p=period: BOLLUpperFactor(p))
            self._registry.register(lambda p=period: BOLLLowerFactor(p))
        for period in [5, 20]:
            self._registry.register(lambda p=period: VOLFactor(p))

    # ---- 查询 ----

    def list_factors(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有因子"""
        if category:
            names = self._registry.list_by_category(category)
            result = []
            for name in names:
                cls = self._registry.get(name)
                inst = cls()
                result.append({
                    "name": inst.name,
                    "category": inst.category,
                    "description": inst.description,
                })
            return result
        return self._registry.info()

    def get_factor(self, name: str) -> Optional[Dict[str, Any]]:
        """获取因子详情"""
        if not self._registry.has(name):
            return None
        cls = self._registry.get(name)
        inst = cls()
        return {
            "name": inst.name,
            "category": inst.category,
            "description": inst.description,
            "class": cls.__name__,
        }

    def categories(self) -> List[str]:
        """列出因子分类"""
        return self._registry.categories()

    def has_factor(self, name: str) -> bool:
        """检查因子是否存在"""
        return self._registry.has(name)

    # ---- 计算 ----

    def compute(
        self,
        factor_name: str,
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        use_cache: bool = True,
    ) -> pd.Series:
        """计算因子值（含缓存）"""
        return self._cache.compute(
            factor_name, df,
            dataset_id=dataset_id,
            symbol=symbol,
            use_cache=use_cache,
        )

    def compute_batch(
        self,
        factor_names: List[str],
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        use_cache: bool = True,
    ) -> Dict[str, pd.Series]:
        """批量计算因子值"""
        return self._cache.compute_batch(
            factor_names, df,
            dataset_id=dataset_id,
            symbol=symbol,
            use_cache=use_cache,
        )

    # ---- IC 分析 ----

    def ic_analysis(
        self,
        factor_name: str,
        df: pd.DataFrame,
        symbol: str = "",
        dataset_id: str = "",
        forward_period: int = 1,
        method: str = "spearman",
    ) -> Dict[str, Any]:
        """IC 分析"""
        factor_series = self.compute(factor_name, df, dataset_id=dataset_id, symbol=symbol)
        returns = df["close"].pct_change(forward_period).shift(-forward_period)

        factor_df = factor_series.to_frame(symbol or "default")
        returns_df = returns.to_frame(symbol or "default")

        ic_series = compute_ic(factor_df, returns_df, method=method)
        ic_stats = compute_ic_stats(ic_series)

        rank_ic_series = compute_ic(factor_df, returns_df, method="spearman")
        rank_ic_stats = compute_ic_stats(rank_ic_series)

        turnover_series = compute_turnover(factor_df)
        turnover_val = float(turnover_series.dropna().mean()) if len(turnover_series.dropna()) > 0 else 0

        coverage_series = compute_coverage(factor_df)
        coverage_val = float(coverage_series.mean()) if len(coverage_series) > 0 else 0

        return {
            "ic_stats": ic_stats,
            "rank_ic_stats": rank_ic_stats,
            "turnover": round(turnover_val, 4),
            "coverage": round(coverage_val, 4),
            "ic_series": ic_series,
            "rank_ic_series": rank_ic_series,
        }

    # ---- 相关性 ----

    def correlation(
        self,
        factor_names: List[str],
        df: pd.DataFrame,
        symbol: str = "",
        dataset_id: str = "",
        method: str = "spearman",
    ) -> Any:
        """因子相关性矩阵"""
        results = self.compute_batch(factor_names, df, dataset_id=dataset_id, symbol=symbol)
        factor_data = {name: series.to_frame(symbol or "default") for name, series in results.items()}
        return compute_factor_correlation(factor_data, method=method)

    # ---- 缓存统计 ----

    def cache_stats(self) -> Dict[str, Any]:
        """缓存统计"""
        return self._cache.stats()

    # ---- 注册 ----

    def register(self, factor_cls: type) -> type:
        """注册因子类"""
        return self._registry.register(factor_cls)

    def register_decorator(self):
        """返回 @register_factor 装饰器"""
        return self._registry.register
