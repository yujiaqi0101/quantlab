"""
Factor Cache — 因子计算缓存

基于 ResearchCache 的因子专用缓存层。

缓存 key 设计：
  factor:{dataset_id}:{symbol}:{factor_name}:{params_hash}

例如：
  factor:crypto_btcusdt:BTCUSDT:RSI14:abc123

命中缓存时直接返回，未命中则计算后缓存。
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..research.cache import ResearchCache
from .base import Factor, CompositeFactor
from .registry import FactorRegistry
from .factor_engine import FactorEngine

logger = logging.getLogger("quantlab.factor.cache")


class FactorCache:
    """
    因子缓存

    两层：
      1. ResearchCache（内存 + 磁盘）
      2. FactorEngine（计算）

    用法：
        cache = FactorCache(registry)
        series = cache.compute("RSI14", df, dataset_id="crypto", symbol="BTCUSDT")
    """

    def __init__(
        self,
        registry: FactorRegistry,
        cache_dir: str = "storage/factor_cache",
    ) -> None:
        self.registry = registry
        self.engine = FactorEngine(registry)
        self._cache = ResearchCache(cache_dir=cache_dir)

    def _make_key(
        self,
        factor_name: str,
        dataset_id: str,
        symbol: str,
        params: Optional[Dict] = None,
    ) -> str:
        """生成缓存 key"""
        params_str = json.dumps(params or {}, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"factor:{dataset_id}:{symbol}:{factor_name}:{params_hash}"

    def compute(
        self,
        factor_name: str,
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        use_cache: bool = True,
    ) -> pd.Series:
        """
        计算因子值（带缓存）

        参数:
            factor_name  因子名称
            df           OHLCV DataFrame
            dataset_id   数据集 ID（用于缓存 key）
            symbol       标的符号（用于缓存 key）
            use_cache    是否使用缓存
        """
        if not use_cache or not dataset_id or not symbol:
            return self.engine.compute(factor_name, df)

        key = self._make_key(factor_name, dataset_id, symbol)
        cached = self._cache.get(key)
        if cached is not None:
            if isinstance(cached, pd.DataFrame) and len(cached.columns) == 1:
                return cached.iloc[:, 0]
            if isinstance(cached, pd.Series):
                return cached
            logger.warning(f"cache type mismatch for {key}, recomputing")

        # 计算
        result = self.engine.compute(factor_name, df)

        # 缓存
        self._cache.put(
            key, result,
            category="factor",
            version="1",
            metadata={"factor": factor_name, "dataset": dataset_id, "symbol": symbol},
        )

        return result

    def compute_batch(
        self,
        factor_names: List[str],
        df: pd.DataFrame,
        dataset_id: str = "",
        symbol: str = "",
        use_cache: bool = True,
    ) -> Dict[str, pd.Series]:
        """批量计算多个因子（带缓存）"""
        results: Dict[str, pd.Series] = {}

        # 先从缓存取
        uncached: List[str] = []
        for name in factor_names:
            if use_cache and dataset_id and symbol:
                key = self._make_key(name, dataset_id, symbol)
                cached = self._cache.get(key)
                if cached is not None:
                    if isinstance(cached, pd.DataFrame) and len(cached.columns) == 1:
                        results[name] = cached.iloc[:, 0]
                    elif isinstance(cached, pd.Series):
                        results[name] = cached
                    else:
                        uncached.append(name)
                else:
                    uncached.append(name)
            else:
                uncached.append(name)

        # 计算未缓存的
        if uncached:
            computed = self.engine.compute_batch(uncached, df)
            for name, series in computed.items():
                results[name] = series
                if use_cache and dataset_id and symbol:
                    key = self._make_key(name, dataset_id, symbol)
                    self._cache.put(
                        key, series,
                        category="factor",
                        version="1",
                        metadata={"factor": name, "dataset": dataset_id, "symbol": symbol},
                    )

        return results

    def invalidate(self, factor_name: str, dataset_id: str, symbol: str) -> bool:
        """使某个因子的缓存失效"""
        key = self._make_key(factor_name, dataset_id, symbol)
        return self._cache.invalidate(key)

    def stats(self) -> Dict[str, Any]:
        return self._cache.stats()
