"""
FactorEngine — V4.6 因子计算引擎

职责：
  - 批量计算多个因子
  - 自动处理依赖（CompositeFactor）
  - 支持单 symbol / 多 symbol
  - 与 FeatureStore 集成缓存
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import Factor, CompositeFactor
from .registry import FactorRegistry

logger = logging.getLogger("quantlab.factor.engine")


class FactorEngine:
    """
    因子计算引擎

    用法：
        registry = FactorRegistry()
        registry.register(RSI14Factor)
        registry.register(Momentum20Factor)

        engine = FactorEngine(registry)

        # 单 symbol
        factors = engine.compute("RSI14", df_aapl)

        # 多 symbol
        results = engine.compute_all("RSI14", data)
        # → {"AAPL": Series, "MSFT": Series, ...}

        # 批量
        results = engine.compute_batch(["RSI14", "MOM20"], df_aapl)
    """

    def __init__(self, registry: FactorRegistry) -> None:
        self.registry = registry

    # ------------------------------------------------------------------
    # 单 symbol
    # ------------------------------------------------------------------
    def compute(self, factor_name: str, df: pd.DataFrame) -> pd.Series:
        """计算单个因子（单 symbol）"""
        factor_cls = self.registry.get(factor_name)
        factor = factor_cls()
        return factor.compute(df)

    def compute_batch(
        self,
        factor_names: List[str],
        df: pd.DataFrame,
    ) -> Dict[str, pd.Series]:
        """批量计算多个因子（单 symbol）"""
        results: Dict[str, pd.Series] = {}
        # 先算非 Composite 的
        for name in factor_names:
            cls = self.registry.get(name)
            inst = cls()
            if not isinstance(inst, CompositeFactor):
                results[name] = inst.compute(df)

        # 再算 Composite 的（需要依赖）
        for name in factor_names:
            cls = self.registry.get(name)
            inst = cls()
            if isinstance(inst, CompositeFactor):
                results[name] = inst.combine(results)

        return results

    # ------------------------------------------------------------------
    # 多 symbol
    # ------------------------------------------------------------------
    def compute_all(
        self,
        factor_name: str,
        data: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        计算单个因子（所有 symbol）

        返回: DataFrame(index=时间, columns=symbols)
        """
        result: Dict[str, pd.Series] = {}
        for sym, df in data.items():
            result[sym] = self.compute(factor_name, df)
        return pd.DataFrame(result)

    def compute_all_batch(
        self,
        factor_names: List[str],
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, pd.DataFrame]:
        """
        批量计算多个因子（所有 symbol）

        返回: {factor_name: DataFrame(index=时间, columns=symbols)}
        """
        results: Dict[str, pd.DataFrame] = {}
        # 先算非 Composite
        for name in factor_names:
            cls = self.registry.get(name)
            inst = cls()
            if not isinstance(inst, CompositeFactor):
                results[name] = self.compute_all(name, data)

        # 再算 Composite
        for name in factor_names:
            cls = self.registry.get(name)
            inst = cls()
            if isinstance(inst, CompositeFactor):
                # 把 DataFrame 转成 per-symbol Series dict
                combined: Dict[str, pd.Series] = {}
                for sym in data:
                    dep_values = {
                        fn: results[fn][sym] for fn in inst.dependencies
                        if fn in results
                    }
                    combined[sym] = inst.combine(dep_values)
                results[name] = pd.DataFrame(combined)

        return results

    # ------------------------------------------------------------------
    # 便捷：compute → DataFrame (宽表)
    # ------------------------------------------------------------------
    def compute_wide(
        self,
        factor_names: List[str],
        data: Dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        计算多个因子，返回宽表

        index=时间, columns=MultiIndex(factor, symbol)
        """
        all_results = self.compute_all_batch(factor_names, data)
        if not all_results:
            return pd.DataFrame()
        # 拼成 MultiIndex
        panels = {}
        for fname, df in all_results.items():
            panels[fname] = df

        return pd.concat(panels, axis=1, names=["factor", "symbol"])
