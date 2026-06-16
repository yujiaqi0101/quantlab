"""
Factor API — 因子平台 API

端点：
  GET  /api/v1/factors                    因子列表（支持按分类过滤）
  GET  /api/v1/factors/{name}             因子详情（参数、描述）
  POST /api/v1/factors/compute            计算因子值
  POST /api/v1/factors/visualize          因子可视化数据（价格+因子叠加）
  POST /api/v1/factors/correlation        因子相关性矩阵
  POST /api/v1/factors/ic                 因子 IC 分析
  GET  /api/v1/factors/categories         因子分类列表
  GET  /api/v1/factors/cache/stats        缓存统计
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..factor.base import Factor
from ..factor.registry import FactorRegistry
from ..factor.cache import FactorCache
from ..factor.ic_analysis import (
    compute_ic,
    compute_ic_stats,
    compute_factor_correlation,
    compute_factor_ic_report,
    compute_turnover,
    compute_coverage,
)
from ..factor.technical import (
    MAFactor, RSIFactor, MomentumFactor, ATRFactor,
    BOLLUpperFactor, BOLLLowerFactor, VOLFactor,
)
from ..dataset.registry import get_dataset_registry
from ..dataset.catalog import DataCatalog

logger = logging.getLogger("quantlab.api.factors")

router = APIRouter(prefix="/api/v1/factors", tags=["factors"])


# ---- 初始化 Registry + Cache ----
_registry: Optional[FactorRegistry] = None
_cache: Optional[FactorCache] = None


def _get_registry() -> FactorRegistry:
    global _registry
    if _registry is None:
        _registry = FactorRegistry()
        _register_builtin_factors(_registry)
    return _registry


def _get_cache() -> FactorCache:
    global _cache
    if _cache is None:
        _cache = FactorCache(_get_registry())
    return _cache


def _register_builtin_factors(registry: FactorRegistry) -> None:
    """注册所有内置因子"""
    for period in [5, 10, 20, 60]:
        registry.register(lambda p=period: MAFactor(p))
    for period in [6, 14, 28]:
        registry.register(lambda p=period: RSIFactor(p))
    for period in [5, 10, 20, 60]:
        registry.register(lambda p=period: MomentumFactor(p))
    for period in [14, 28]:
        registry.register(lambda p=period: ATRFactor(p))
    for period in [20]:
        registry.register(lambda p=period: BOLLUpperFactor(p))
        registry.register(lambda p=period: BOLLLowerFactor(p))
    for period in [5, 20]:
        registry.register(lambda p=period: VOLFactor(p))


# ---- 确保数据集目录已扫描 ----
_catalog_initialized = False


def _ensure_catalog() -> None:
    global _catalog_initialized
    if _catalog_initialized:
        return
    catalog = DataCatalog()
    catalog.scan()
    _catalog_initialized = True


# ---- Request Models ----

class ComputeRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: str = ""
    use_cache: bool = True


class BatchComputeRequest(BaseModel):
    factor_names: List[str]
    dataset_id: str
    symbol: str = ""
    use_cache: bool = True


class VisualizeRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: str = ""
    n_points: int = 500


class CorrelationRequest(BaseModel):
    factor_names: List[str]
    dataset_id: str
    symbol: str = ""
    method: str = "spearman"


class ICRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: str = ""
    forward_period: int = 1
    method: str = "spearman"


# ---- Helpers ----

def _load_symbol_data(dataset_id: str, symbol: str) -> pd.DataFrame:
    """加载数据集中某个 symbol 的 OHLCV 数据"""
    _ensure_catalog()
    ds_registry = get_dataset_registry()
    meta = ds_registry.get(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    data = ds_registry.load(dataset_id)
    if not data:
        raise HTTPException(status_code=400, detail=f"Dataset '{dataset_id}' has no data")

    # 如果没指定 symbol，取第一个
    if not symbol:
        symbol = list(data.keys())[0]

    if symbol not in data:
        available = list(data.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Symbol '{symbol}' not found in dataset. Available: {available}",
        )

    return data[symbol], symbol


def _series_to_json(series: pd.Series, max_points: int = 0) -> List[Dict[str, Any]]:
    """将 pd.Series 转为 JSON 可序列化的列表"""
    if max_points > 0 and len(series) > max_points:
        # 降采样
        step = max(1, len(series) // max_points)
        series = series.iloc[::step]

    result = []
    for idx, val in series.items():
        if pd.isna(val):
            continue
        ts = str(idx) if not isinstance(idx, pd.Timestamp) else idx.isoformat()
        result.append({"t": ts, "v": round(float(val), 6)})
    return result


# ---- API Endpoints ----

@router.get("")
async def api_list_factors(
    category: Optional[str] = Query(None, description="按分类过滤"),
) -> List[Dict[str, Any]]:
    """因子列表"""
    registry = _get_registry()
    if category:
        names = registry.list_by_category(category)
        result = []
        for name in names:
            cls = registry.get(name)
            inst = cls()
            result.append({
                "name": inst.name,
                "category": inst.category,
                "description": inst.description,
            })
        return result
    return registry.info()


@router.get("/categories")
async def api_list_categories() -> List[str]:
    """因子分类列表"""
    registry = _get_registry()
    return registry.categories()


@router.get("/cache/stats")
async def api_cache_stats() -> Dict[str, Any]:
    """缓存统计"""
    cache = _get_cache()
    return cache.stats()


@router.get("/{factor_name}")
async def api_get_factor(factor_name: str) -> Dict[str, Any]:
    """因子详情"""
    registry = _get_registry()
    if not registry.has(factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{factor_name}' not found")
    cls = registry.get(factor_name)
    inst = cls()
    return {
        "name": inst.name,
        "category": inst.category,
        "description": inst.description,
        "class": cls.__name__,
    }


@router.post("/compute")
async def api_compute_factor(req: ComputeRequest) -> Dict[str, Any]:
    """计算因子值"""
    registry = _get_registry()
    if not registry.has(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    cache = _get_cache()
    series = cache.compute(
        req.factor_name, df,
        dataset_id=req.dataset_id,
        symbol=symbol,
        use_cache=req.use_cache,
    )

    values = _series_to_json(series, max_points=500)

    return {
        "factor_name": req.factor_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "count": len(values),
        "values": values,
    }


@router.post("/batch-compute")
async def api_batch_compute(req: BatchComputeRequest) -> Dict[str, Any]:
    """批量计算多个因子"""
    registry = _get_registry()
    for name in req.factor_names:
        if not registry.has(name):
            raise HTTPException(status_code=404, detail=f"Factor '{name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    cache = _get_cache()
    results = cache.compute_batch(
        req.factor_names, df,
        dataset_id=req.dataset_id,
        symbol=symbol,
        use_cache=req.use_cache,
    )

    output = {}
    for name, series in results.items():
        output[name] = _series_to_json(series, max_points=500)

    return {
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "factors": output,
    }


@router.post("/visualize")
async def api_visualize_factor(req: VisualizeRequest) -> Dict[str, Any]:
    """
    因子可视化数据

    返回价格 K 线数据 + 因子值，前端叠加显示
    """
    registry = _get_registry()
    if not registry.has(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    cache = _get_cache()
    factor_series = cache.compute(
        req.factor_name, df,
        dataset_id=req.dataset_id,
        symbol=symbol,
    )

    # 降采样
    n = req.n_points
    if n > 0 and len(df) > n:
        step = max(1, len(df) // n)
        df_sampled = df.iloc[::step]
        factor_sampled = factor_series.iloc[::step]
    else:
        df_sampled = df
        factor_sampled = factor_series

    # K 线数据
    candles = []
    for idx, row in df_sampled.iterrows():
        ts = str(idx) if not isinstance(idx, pd.Timestamp) else idx.isoformat()
        candles.append({
            "t": ts,
            "o": round(float(row.get("open", 0)), 4),
            "h": round(float(row.get("high", 0)), 4),
            "l": round(float(row.get("low", 0)), 4),
            "c": round(float(row.get("close", 0)), 4),
            "v": round(float(row.get("volume", 0)), 2),
        })

    # 因子数据
    factor_data = _series_to_json(factor_sampled, max_points=0)

    return {
        "factor_name": req.factor_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "candles": candles,
        "factor": factor_data,
    }


@router.post("/correlation")
async def api_factor_correlation(req: CorrelationRequest) -> Dict[str, Any]:
    """因子相关性矩阵"""
    registry = _get_registry()
    for name in req.factor_names:
        if not registry.has(name):
            raise HTTPException(status_code=404, detail=f"Factor '{name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    cache = _get_cache()
    results = cache.compute_batch(
        req.factor_names, df,
        dataset_id=req.dataset_id,
        symbol=symbol,
    )

    # 构建因子数据 dict（每个因子是单 symbol Series → 转成 DataFrame 格式）
    factor_data = {}
    for name, series in results.items():
        factor_data[name] = series.to_frame(symbol)

    corr_matrix = compute_factor_correlation(factor_data, method=req.method)

    # 转为 JSON
    labels = list(corr_matrix.columns)
    matrix = []
    for i, row_name in enumerate(corr_matrix.index):
        row = []
        for col_name in corr_matrix.columns:
            val = corr_matrix.loc[row_name, col_name]
            row.append(round(float(val), 4) if not pd.isna(val) else None)
        matrix.append(row)

    return {
        "labels": labels,
        "matrix": matrix,
        "method": req.method,
    }


@router.post("/ic")
async def api_factor_ic(req: ICRequest) -> Dict[str, Any]:
    """因子 IC 分析"""
    registry = _get_registry()
    if not registry.has(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    cache = _get_cache()
    factor_series = cache.compute(
        req.factor_name, df,
        dataset_id=req.dataset_id,
        symbol=symbol,
    )

    # 计算下期收益率
    returns = df["close"].pct_change(req.forward_period).shift(-req.forward_period)

    # 构建 DataFrame 格式（单 symbol）
    factor_df = factor_series.to_frame(symbol)
    returns_df = returns.to_frame(symbol)

    # IC 计算
    ic_series = compute_ic(factor_df, returns_df, method=req.method)
    ic_stats = compute_ic_stats(ic_series)

    # Rank IC
    rank_ic_series = compute_ic(factor_df, returns_df, method="spearman")
    rank_ic_stats = compute_ic_stats(rank_ic_series)

    # Turnover
    turnover_series = compute_turnover(factor_df)
    turnover_val = float(turnover_series.dropna().mean()) if len(turnover_series.dropna()) > 0 else 0

    # Coverage
    coverage_series = compute_coverage(factor_df)
    coverage_val = float(coverage_series.mean()) if len(coverage_series) > 0 else 0

    # IC 时序数据
    ic_values = _series_to_json(ic_series, max_points=200)
    rank_ic_values = _series_to_json(rank_ic_series, max_points=200)

    return {
        "factor_name": req.factor_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "forward_period": req.forward_period,
        "ic_stats": ic_stats,
        "rank_ic_stats": rank_ic_stats,
        "turnover": round(turnover_val, 4),
        "coverage": round(coverage_val, 4),
        "ic_series": ic_values,
        "rank_ic_series": rank_ic_values,
    }
