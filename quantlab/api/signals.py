"""
Signal API — 信号平台 API

V2.0 重构：通过 SignalService 统一调用，API 层不直接碰 core

端点：
  GET  /api/v1/signals                    信号列表
  GET  /api/v1/signals/{name}             信号详情
  POST /api/v1/signals/build              构建信号
  POST /api/v1/signals/preview            信号预览
  POST /api/v1/signals/visualize          信号可视化
  POST /api/v1/signals/forward-return     前瞻收益
  POST /api/v1/signals/combine            信号组合
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

logger = logging.getLogger("quantlab.api.signals")

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


def _svc():
    return get_service("signal")


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

class BuildThresholdRequest(BaseModel):
    factor_name: str
    operator: str
    value: float
    direction: str = "long"
    signal_name: Optional[str] = None


class BuildCrossoverRequest(BaseModel):
    fast_factor: str
    slow_factor: str
    signal_name: Optional[str] = None


class BuildZeroCrossRequest(BaseModel):
    factor_name: str
    signal_name: Optional[str] = None


class BuildCompositeRequest(BaseModel):
    signal_names: List[str]
    logic: str = "AND"
    signal_name: Optional[str] = None


class PreviewRequest(BaseModel):
    signal_name: str
    dataset_id: str
    symbol: str = ""


class VisualizeRequest(BaseModel):
    signal_name: str
    dataset_id: str
    symbol: str = ""
    n_points: int = 500


class ForwardReturnRequest(BaseModel):
    signal_name: str
    dataset_id: str
    symbol: str = ""
    forward_periods: List[int] = [1, 5, 10, 20]


class CombineRequest(BaseModel):
    signal_names: List[str]
    logic: str = "AND"
    dataset_id: str
    symbol: str = ""
    signal_name: Optional[str] = None


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
async def api_list_signals() -> List[Dict[str, Any]]:
    """信号列表"""
    return _svc().list_signals()


@router.get("/{signal_name}")
async def api_get_signal(signal_name: str) -> Dict[str, Any]:
    """信号详情"""
    svc = _svc()
    sig = svc.get_signal(signal_name)
    if sig is None:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_name}' not found")
    return {
        "name": sig.name,
        "description": sig.description,
        "type": type(sig).__name__,
    }


@router.post("/build")
async def api_build_signal(req: BuildThresholdRequest | BuildCrossoverRequest | BuildZeroCrossRequest) -> Dict[str, Any]:
    """构建信号（阈值/交叉/零轴）"""
    svc = _svc()
    # 根据请求类型构建
    if isinstance(req, BuildThresholdRequest):
        sig = svc.build_threshold(req.factor_name, req.operator, req.value, req.direction, req.signal_name)
    elif isinstance(req, BuildCrossoverRequest):
        sig = svc.build_crossover(req.fast_factor, req.slow_factor, req.signal_name)
    elif isinstance(req, BuildZeroCrossRequest):
        sig = svc.build_zero_cross(req.factor_name, req.signal_name)
    else:
        raise HTTPException(status_code=400, detail="Unknown build request type")
    return {"name": sig.name, "type": type(sig).__name__}


@router.post("/build/threshold")
async def api_build_threshold(req: BuildThresholdRequest) -> Dict[str, Any]:
    """构建阈值信号"""
    svc = _svc()
    sig = svc.build_threshold(req.factor_name, req.operator, req.value, req.direction, req.signal_name)
    return {"name": sig.name, "type": type(sig).__name__}


@router.post("/build/crossover")
async def api_build_crossover(req: BuildCrossoverRequest) -> Dict[str, Any]:
    """构建交叉信号"""
    svc = _svc()
    sig = svc.build_crossover(req.fast_factor, req.slow_factor, req.signal_name)
    return {"name": sig.name, "type": type(sig).__name__}


@router.post("/build/zero-cross")
async def api_build_zero_cross(req: BuildZeroCrossRequest) -> Dict[str, Any]:
    """构建零轴交叉信号"""
    svc = _svc()
    sig = svc.build_zero_cross(req.factor_name, req.signal_name)
    return {"name": sig.name, "type": type(sig).__name__}


@router.post("/build/composite")
async def api_build_composite(req: BuildCompositeRequest) -> Dict[str, Any]:
    """构建组合信号"""
    svc = _svc()
    sig = svc.build_composite(req.signal_names, req.logic, req.signal_name)
    return {"name": sig.name, "type": type(sig).__name__}


@router.post("/preview")
async def api_preview_signal(req: PreviewRequest) -> Dict[str, Any]:
    """信号预览"""
    svc = _svc()
    if not svc.has_signal(req.signal_name):
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    return svc.preview(req.signal_name, df, dataset_id=req.dataset_id, symbol=symbol)


@router.post("/visualize")
async def api_visualize_signal(req: VisualizeRequest) -> Dict[str, Any]:
    """信号可视化"""
    svc = _svc()
    if not svc.has_signal(req.signal_name):
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)

    from ..signal.base import Signal, MultiFactorSignal
    from ..signal.threshold import ThresholdSignal
    from ..signal.crossover import CrossoverSignal, ZeroCrossoverSignal

    signal = svc.get_signal(req.signal_name)
    factor_values = svc.compute_factor_values(df, dataset_id=req.dataset_id, symbol=symbol)
    sig_values = svc.generate_signal(signal, factor_values)

    n = req.n_points
    if n > 0 and len(df) > n:
        step = max(1, len(df) // n)
        df_sampled = df.iloc[::step]
        sig_sampled = sig_values.iloc[::step]
    else:
        df_sampled = df
        sig_sampled = sig_values

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

    signal_data = _series_to_json(sig_sampled, max_points=0)

    return {
        "signal_name": req.signal_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "candles": candles,
        "signal": signal_data,
    }


@router.post("/forward-return")
async def api_forward_return(req: ForwardReturnRequest) -> Dict[str, Any]:
    """前瞻收益分析"""
    svc = _svc()
    if not svc.has_signal(req.signal_name):
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    return svc.forward_return(req.signal_name, df, dataset_id=req.dataset_id, symbol=symbol, forward_periods=req.forward_periods)


@router.post("/combine")
async def api_combine_signals(req: CombineRequest) -> Dict[str, Any]:
    """信号组合"""
    svc = _svc()

    for name in req.signal_names:
        if not svc.has_signal(name):
            raise HTTPException(status_code=404, detail=f"Signal '{name}' not found")

    sig = svc.build_composite(req.signal_names, req.logic, req.signal_name)

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    preview = svc.preview(sig.name, df, dataset_id=req.dataset_id, symbol=symbol)

    return {
        "combined_signal": sig.name,
        "type": type(sig).__name__,
        "logic": req.logic,
        "sub_signals": req.signal_names,
        "preview": preview,
    }
