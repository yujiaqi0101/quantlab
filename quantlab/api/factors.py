"""
Factor API — 因子平台 API

V2.0 重构：通过 FactorService 统一调用，API 层不直接碰 core

端点：
  GET  /api/v1/factors                    因子列表
  GET  /api/v1/factors/{name}             因子详情
  GET  /api/v1/factors/categories         因子分类
  GET  /api/v1/factors/cache/stats        缓存统计
  POST /api/v1/factors/compute            计算因子值
  POST /api/v1/factors/batch-compute      批量计算
  POST /api/v1/factors/visualize          因子可视化
  POST /api/v1/factors/correlation        相关性矩阵
  POST /api/v1/factors/ic                 IC 分析
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..services import get_service
from ..dataset.registry import get_dataset_registry
from ..dataset.catalog import DataCatalog

logger = logging.getLogger("quantlab.api.factors")

router = APIRouter(prefix="/api/v1/factors", tags=["factors"])


def _svc():
    return get_service("factor")


# ---- 数据集初始化 ----
_catalog_initialized = False


def _ensure_catalog() -> None:
    global _catalog_initialized
    if _catalog_initialized:
        return
    try:
        catalog = DataCatalog()
        catalog.scan()
    except Exception:
        pass
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

def _load_symbol_data(dataset_id: str, symbol: str):
    """加载数据集中某个 symbol 的 OHLCV 数据"""
    _ensure_catalog()
    ds_registry = get_dataset_registry()
    meta = ds_registry.get(dataset_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    data = ds_registry.load(dataset_id)
    if not data:
        raise HTTPException(status_code=400, detail=f"Dataset '{dataset_id}' has no data")
    if not symbol:
        symbol = list(data.keys())[0]
    if symbol not in data:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    return data[symbol], symbol


def _series_to_json(series: pd.Series, max_points: int = 0) -> List[Dict[str, Any]]:
    if max_points > 0 and len(series) > max_points:
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
    return _svc().list_factors(category=category)


@router.get("/categories")
async def api_list_categories() -> List[str]:
    """因子分类列表"""
    return _svc().categories()


@router.get("/cache/stats")
async def api_cache_stats() -> Dict[str, Any]:
    """缓存统计"""
    return _svc().cache_stats()


@router.get("/{factor_name}")
async def api_get_factor(factor_name: str) -> Dict[str, Any]:
    """因子详情"""
    result = _svc().get_factor(factor_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Factor '{factor_name}' not found")
    return result


@router.post("/compute")
async def api_compute_factor(req: ComputeRequest) -> Dict[str, Any]:
    """计算因子值"""
    svc = _svc()
    if not svc.has_factor(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    series = svc.compute(req.factor_name, df, dataset_id=req.dataset_id, symbol=symbol, use_cache=req.use_cache)
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
    svc = _svc()
    for name in req.factor_names:
        if not svc.has_factor(name):
            raise HTTPException(status_code=404, detail=f"Factor '{name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    results = svc.compute_batch(req.factor_names, df, dataset_id=req.dataset_id, symbol=symbol, use_cache=req.use_cache)

    output = {}
    for name, series in results.items():
        output[name] = _series_to_json(series, max_points=500)

    return {"dataset_id": req.dataset_id, "symbol": symbol, "factors": output}


@router.post("/visualize")
async def api_visualize_factor(req: VisualizeRequest) -> Dict[str, Any]:
    """因子可视化数据"""
    svc = _svc()
    if not svc.has_factor(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    factor_series = svc.compute(req.factor_name, df, dataset_id=req.dataset_id, symbol=symbol)

    n = req.n_points
    if n > 0 and len(df) > n:
        step = max(1, len(df) // n)
        df_sampled = df.iloc[::step]
        factor_sampled = factor_series.iloc[::step]
    else:
        df_sampled = df
        factor_sampled = factor_series

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
    svc = _svc()
    for name in req.factor_names:
        if not svc.has_factor(name):
            raise HTTPException(status_code=404, detail=f"Factor '{name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    corr_matrix = svc.correlation(req.factor_names, df, symbol=symbol, dataset_id=req.dataset_id, method=req.method)

    labels = list(corr_matrix.columns)
    matrix = []
    for row_name in corr_matrix.index:
        row = []
        for col_name in corr_matrix.columns:
            val = corr_matrix.loc[row_name, col_name]
            row.append(round(float(val), 4) if not pd.isna(val) else None)
        matrix.append(row)

    return {"labels": labels, "matrix": matrix, "method": req.method}


@router.post("/ic")
async def api_factor_ic(req: ICRequest) -> Dict[str, Any]:
    """因子 IC 分析"""
    svc = _svc()
    if not svc.has_factor(req.factor_name):
        raise HTTPException(status_code=404, detail=f"Factor '{req.factor_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    result = svc.ic_analysis(
        req.factor_name, df,
        symbol=symbol,
        dataset_id=req.dataset_id,
        forward_period=req.forward_period,
        method=req.method,
    )

    return {
        "factor_name": req.factor_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "forward_period": req.forward_period,
        "ic_stats": result["ic_stats"],
        "rank_ic_stats": result["rank_ic_stats"],
        "turnover": result["turnover"],
        "coverage": result["coverage"],
        "ic_series": _series_to_json(result["ic_series"], max_points=200),
        "rank_ic_series": _series_to_json(result["rank_ic_series"], max_points=200),
    }
