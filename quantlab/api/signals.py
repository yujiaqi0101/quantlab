"""
Signal API — 信号研究平台 API

端点：
  GET  /api/v1/signals                    信号列表
  POST /api/v1/signals/build              构建信号（可视化 Builder）
  POST /api/v1/signals/preview            预览信号（Coverage/触发统计）
  POST /api/v1/signals/visualize          信号可视化（价格+信号时间线）
  POST /api/v1/signals/forward-return     信号前瞻收益分析
  POST /api/v1/signals/combine            组合信号（AND/OR/MAJORITY）
  GET  /api/v1/signals/operators          可用操作符列表
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..signal.base import Signal, MultiFactorSignal
from ..signal.threshold import ThresholdSignal
from ..signal.crossover import CrossoverSignal, ZeroCrossoverSignal
from ..signal.composite import AndSignal, OrSignal, MajoritySignal
from ..signal.signal_engine import SignalEngine
from ..signal.builder import SignalBuilder
from ..factor.registry import FactorRegistry
from ..factor.cache import FactorCache
from ..factor.technical import (
    MAFactor, RSIFactor, MomentumFactor, ATRFactor,
    BOLLUpperFactor, BOLLLowerFactor, VOLFactor,
)
from ..dataset.registry import get_dataset_registry
from ..dataset.catalog import DataCatalog

logger = logging.getLogger("quantlab.api.signals")

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


# ---- 初始化 ----
_engine: Optional[SignalEngine] = None
_builder: Optional[SignalBuilder] = None
_factor_registry: Optional[FactorRegistry] = None
_factor_cache: Optional[FactorCache] = None


def _get_engine() -> SignalEngine:
    global _engine
    if _engine is None:
        _engine = SignalEngine()
        # 注册一些默认信号
        _engine.register(ThresholdSignal("RSI14", 30, 70, "RSI_Oversold_Overbought"))
        _engine.register(ThresholdSignal("RSI6", 20, 80, "RSI6_Extreme"))
        _engine.register(ZeroCrossoverSignal("MOM20", "MOM20_ZeroCross"))
        _engine.register(CrossoverSignal("MA5", "MA20", "MA_Cross_5_20"))
    return _engine


def _get_builder() -> SignalBuilder:
    global _builder
    if _builder is None:
        _builder = SignalBuilder(_get_engine())
    return _builder


def _get_factor_registry() -> FactorRegistry:
    global _factor_registry
    if _factor_registry is None:
        _factor_registry = FactorRegistry()
        for period in [5, 10, 20, 60]:
            _factor_registry.register(lambda p=period: MAFactor(p))
        for period in [6, 14, 28]:
            _factor_registry.register(lambda p=period: RSIFactor(p))
        for period in [5, 10, 20, 60]:
            _factor_registry.register(lambda p=period: MomentumFactor(p))
        for period in [14, 28]:
            _factor_registry.register(lambda p=period: ATRFactor(p))
        for period in [5, 20]:
            _factor_registry.register(lambda p=period: VOLFactor(p))
    return _factor_registry


def _get_factor_cache() -> FactorCache:
    global _factor_cache
    if _factor_cache is None:
        _factor_cache = FactorCache(_get_factor_registry())
    return _factor_cache


_catalog_initialized = False


def _ensure_catalog() -> None:
    global _catalog_initialized
    if _catalog_initialized:
        return
    catalog = DataCatalog()
    catalog.scan()
    _catalog_initialized = True


# ---- Request Models ----

class BuildThresholdRequest(BaseModel):
    factor_name: str
    operator: str          # "<", "<=", ">", ">=", "=="
    value: float
    direction: str = "long"  # "long", "short", "both"
    signal_name: Optional[str] = None


class BuildCrossoverRequest(BaseModel):
    fast_factor: str
    slow_factor: str
    signal_name: Optional[str] = None


class BuildZeroCrossRequest(BaseModel):
    factor_name: str
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
    logic: str = "AND"    # "AND", "OR", "MAJORITY"
    signal_name: Optional[str] = None
    dataset_id: str = ""
    symbol: str = ""


# ---- Helpers ----

def _load_symbol_data(dataset_id: str, symbol: str):
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


def _compute_factor_values(df: pd.DataFrame, dataset_id: str, symbol: str) -> Dict[str, pd.Series]:
    """计算所有注册因子的值"""
    cache = _get_factor_cache()
    factor_names = _get_factor_registry().list()
    return cache.compute_batch(factor_names, df, dataset_id=dataset_id, symbol=symbol)


def _generate_signal(signal: Signal, factor_values: Dict[str, pd.Series]) -> pd.Series:
    """根据信号类型生成信号值"""
    if isinstance(signal, (CrossoverSignal,)):
        return signal.transform_multi(factor_values)
    elif isinstance(signal, (MultiFactorSignal,)):
        return signal.transform_multi(factor_values)
    elif isinstance(signal, (ThresholdSignal, ZeroCrossoverSignal)):
        if hasattr(signal, "factor_name"):
            series = factor_values.get(signal.factor_name)
            if series is None:
                raise HTTPException(status_code=400, detail=f"Factor '{signal.factor_name}' not available")
            return signal.transform(series)
    # fallback
    first_series = list(factor_values.values())[0]
    return signal.transform(first_series)


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
    engine = _get_engine()
    result = []
    for name in engine.list():
        sig = engine.get(name)
        info: Dict[str, Any] = {
            "name": sig.name,
            "description": sig.description,
            "type": type(sig).__name__,
        }
        if isinstance(sig, ThresholdSignal):
            info["factor_name"] = sig.factor_name
            info["lower"] = sig.lower
            info["upper"] = sig.upper
        elif isinstance(sig, CrossoverSignal):
            info["fast_factor"] = sig.fast_factor_name
            info["slow_factor"] = sig.slow_factor_name
        elif isinstance(sig, ZeroCrossoverSignal):
            info["factor_name"] = sig.factor_name
        elif isinstance(sig, (AndSignal, OrSignal, MajoritySignal)):
            info["sub_signals"] = [s.name for s in sig._signals]
            info["logic"] = type(sig).__name__.replace("Signal", "")
        result.append(info)
    return result


@router.get("/operators")
async def api_list_operators() -> List[Dict[str, Any]]:
    """可用操作符列表"""
    return [
        {"value": "<", "label": "less than (<)", "type": "threshold"},
        {"value": "<=", "label": "less or equal (<=)", "type": "threshold"},
        {"value": ">", "label": "greater than (>)", "type": "threshold"},
        {"value": ">=", "label": "greater or equal (>=)", "type": "threshold"},
        {"value": "==", "label": "equal (==)", "type": "threshold"},
        {"value": "crosses", "label": "crosses above", "type": "crossover"},
        {"value": "crosses_below", "label": "crosses below", "type": "crossover"},
        {"value": "zero_cross", "label": "crosses zero", "type": "zero_cross"},
    ]


@router.post("/build")
async def api_build_signal(req: BuildThresholdRequest) -> Dict[str, Any]:
    """构建阈值信号"""
    builder = _get_builder()
    sig = builder.build_threshold(
        req.factor_name, req.operator, req.value,
        direction=req.direction,
        signal_name=req.signal_name,
    )
    return {
        "name": sig.name,
        "description": sig.description,
        "type": type(sig).__name__,
    }


@router.post("/build/crossover")
async def api_build_crossover(req: BuildCrossoverRequest) -> Dict[str, Any]:
    """构建交叉信号"""
    builder = _get_builder()
    sig = builder.build_crossover(req.fast_factor, req.slow_factor, signal_name=req.signal_name)
    return {
        "name": sig.name,
        "description": sig.description,
        "type": type(sig).__name__,
    }


@router.post("/build/zero-cross")
async def api_build_zero_cross(req: BuildZeroCrossRequest) -> Dict[str, Any]:
    """构建零轴交叉信号"""
    builder = _get_builder()
    sig = builder.build_zero_cross(req.factor_name, signal_name=req.signal_name)
    return {
        "name": sig.name,
        "description": sig.description,
        "type": type(sig).__name__,
    }


@router.post("/preview")
async def api_preview_signal(req: PreviewRequest) -> Dict[str, Any]:
    """预览信号（Coverage/触发统计）"""
    engine = _get_engine()
    if req.signal_name not in engine._signals:
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    factor_values = _compute_factor_values(df, req.dataset_id, symbol)
    signal = engine.get(req.signal_name)
    sig_values = _generate_signal(signal, factor_values)

    total = len(sig_values)
    long_count = int((sig_values == 1).sum())
    short_count = int((sig_values == -1).sum())

    return {
        "signal_name": req.signal_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "total_bars": total,
        "long_count": long_count,
        "short_count": short_count,
        "neutral_count": total - long_count - short_count,
        "coverage": round((long_count + short_count) / total, 4) if total > 0 else 0,
        "long_pct": round(long_count / total, 4) if total > 0 else 0,
        "short_pct": round(short_count / total, 4) if total > 0 else 0,
    }


@router.post("/visualize")
async def api_visualize_signal(req: VisualizeRequest) -> Dict[str, Any]:
    """信号可视化（价格+信号时间线）"""
    engine = _get_engine()
    if req.signal_name not in engine._signals:
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    factor_values = _compute_factor_values(df, req.dataset_id, symbol)
    signal = engine.get(req.signal_name)
    sig_values = _generate_signal(signal, factor_values)

    # 降采样
    n = req.n_points
    if n > 0 and len(df) > n:
        step = max(1, len(df) // n)
        df_s = df.iloc[::step]
        sig_s = sig_values.iloc[::step]
    else:
        df_s = df
        sig_s = sig_values

    # K 线数据
    candles = []
    for idx, row in df_s.iterrows():
        ts = str(idx) if not isinstance(idx, pd.Timestamp) else idx.isoformat()
        candles.append({
            "t": ts,
            "o": round(float(row.get("open", 0)), 4),
            "h": round(float(row.get("high", 0)), 4),
            "l": round(float(row.get("low", 0)), 4),
            "c": round(float(row.get("close", 0)), 4),
            "v": round(float(row.get("volume", 0)), 2),
        })

    # 信号数据
    signal_data = _series_to_json(sig_s, max_points=0)

    return {
        "signal_name": req.signal_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "candles": candles,
        "signal": signal_data,
    }


@router.post("/forward-return")
async def api_forward_return(req: ForwardReturnRequest) -> Dict[str, Any]:
    """信号前瞻收益分析"""
    engine = _get_engine()
    if req.signal_name not in engine._signals:
        raise HTTPException(status_code=404, detail=f"Signal '{req.signal_name}' not found")

    df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
    factor_values = _compute_factor_values(df, req.dataset_id, symbol)
    signal = engine.get(req.signal_name)
    sig_values = _generate_signal(signal, factor_values)

    close = df["close"]
    results = {}

    for period in req.forward_periods:
        fwd_return = close.pct_change(period).shift(-period)

        # Long 信号的前瞻收益
        long_mask = sig_values == 1
        long_returns = fwd_return[long_mask].dropna()

        # Short 信号的前瞻收益
        short_mask = sig_values == -1
        short_returns = fwd_return[short_mask].dropna()

        # 所有触发信号的前瞻收益
        all_mask = sig_values != 0
        all_returns = fwd_return[all_mask].dropna()

        results[f"fwd_{period}"] = {
            "long": {
                "mean": round(float(long_returns.mean()), 6) if len(long_returns) > 0 else 0,
                "median": round(float(long_returns.median()), 6) if len(long_returns) > 0 else 0,
                "win_rate": round(float((long_returns > 0).mean()), 4) if len(long_returns) > 0 else 0,
                "count": len(long_returns),
                "std": round(float(long_returns.std()), 6) if len(long_returns) > 1 else 0,
            },
            "short": {
                "mean": round(float(short_returns.mean()), 6) if len(short_returns) > 0 else 0,
                "median": round(float(short_returns.median()), 6) if len(short_returns) > 0 else 0,
                "win_rate": round(float((short_returns > 0).mean()), 4) if len(short_returns) > 0 else 0,
                "count": len(short_returns),
                "std": round(float(short_returns.std()), 6) if len(short_returns) > 1 else 0,
            },
            "all": {
                "mean": round(float(all_returns.mean()), 6) if len(all_returns) > 0 else 0,
                "win_rate": round(float((all_returns > 0).mean()), 4) if len(all_returns) > 0 else 0,
                "count": len(all_returns),
            },
        }

    return {
        "signal_name": req.signal_name,
        "dataset_id": req.dataset_id,
        "symbol": symbol,
        "forward_returns": results,
    }


@router.post("/combine")
async def api_combine_signals(req: CombineRequest) -> Dict[str, Any]:
    """组合信号"""
    engine = _get_engine()
    for name in req.signal_names:
        if name not in engine._signals:
            raise HTTPException(status_code=404, detail=f"Signal '{name}' not found")

    builder = _get_builder()
    sig = builder.build_composite(req.signal_names, logic=req.logic, signal_name=req.signal_name)

    result: Dict[str, Any] = {
        "name": sig.name,
        "description": sig.description,
        "type": type(sig).__name__,
        "sub_signals": req.signal_names,
        "logic": req.logic,
    }

    # 如果提供了 dataset，顺便预览
    if req.dataset_id:
        df, symbol = _load_symbol_data(req.dataset_id, req.symbol)
        factor_values = _compute_factor_values(df, req.dataset_id, symbol)

        # 先生成所有子信号
        sub_signal_values = []
        for name in req.signal_names:
            sub_sig = engine.get(name)
            sub_val = _generate_signal(sub_sig, factor_values)
            sub_signal_values.append(sub_val)

        # 组合
        if isinstance(sig, (AndSignal, OrSignal, MajoritySignal)):
            combined = sig.transform_multi_signal(sub_signal_values)
        else:
            combined = sub_signal_values[0]

        total = len(combined)
        long_count = int((combined == 1).sum())
        short_count = int((combined == -1).sum())

        result["preview"] = {
            "total_bars": total,
            "long_count": long_count,
            "short_count": short_count,
            "coverage": round((long_count + short_count) / total, 4) if total > 0 else 0,
        }

    return result
