"""
Factors API — 因子工作室后端
=============================

端点 (均以 /api/v1/factors 为前缀):
  GET  /factors                 因子列表 (?category=xxx)
  GET  /factors/categories      分类列表
  GET  /factors/{name}          单个因子详情
  POST /factors/compute         计算因子值
  POST /factors/visualize       因子 + K线可视化数据
  POST /factors/ic              IC 分析
  POST /factors/correlation     多因子相关性矩阵
  GET  /factors/cache/stats     缓存统计
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..factor import get_registry
from ..factor.cache import get_factor_cache
from ..ml.dataset import get_dataset_manager
from ..factors.context import FactorContext

logger = logging.getLogger("quantlab.api.factors")

router = APIRouter(prefix="/api/v1/factors", tags=["factors"])


# ---------- 请求/响应模型 ----------

class ComputeRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class VisualizeRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    limit: int = 500


class ICRequest(BaseModel):
    factor_name: str
    dataset_id: str
    symbol: Optional[str] = None
    forward_period: int = 1
    params: Dict[str, Any] = Field(default_factory=dict)


class CorrelationRequest(BaseModel):
    factor_names: List[str]
    dataset_id: str
    symbol: Optional[str] = None


# ---------- 工具: 从数据集构建 FactorContext ----------

def _load_ctx_from_dataset(dataset_id: str, symbol: Optional[str] = None) -> tuple:
    """从 dataset 加载数据，返回 (FactorContext, full_df, target_symbol)。"""
    mgr = get_dataset_manager()
    ds = mgr.get_dataset(dataset_id)
    if ds is None:
        raise HTTPException(404, f"Dataset {dataset_id} not found")
    df = ds.get_data()
    if df is None:
        mgr.load_dataset_data(dataset_id)
        df = ds.get_data()
    if df is None or len(df) == 0:
        raise HTTPException(400, f"Dataset {dataset_id} has no data")

    # 标准化列名（小写）
    df = df.copy()
    df.columns = [c.lower() for c in df.columns]

    # 日期索引
    if not isinstance(df.index, pd.DatetimeIndex):
        for date_col in ("datetime", "date", "trade_date", "timestamp"):
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.set_index(date_col)
                break

    # 处理 symbol 列（多标的长表）→ 按 symbol 分组构建多标的 FactorContext（支持截面因子）
    if "symbol" in df.columns:
        # 用 groupby 高效切分
        panel: Dict[str, pd.DataFrame] = {}
        for sym, sub in df.groupby("symbol"):
            sym_s = str(sym)
            sub = sub.drop(columns=["symbol"], errors="ignore").sort_index()
            sub = sub[~sub.index.duplicated(keep="last")]
            if len(sub) > 0:
                panel[sym_s] = sub

        if not panel:
            raise HTTPException(400, "dataset has no symbols")
        all_symbols = sorted(panel.keys())
        target = symbol if (symbol and symbol in all_symbols) else all_symbols[0]

        ctx = _build_ctx_from_panel(panel)
        return ctx, df, target

    # 单标的数据集
    sym_list = ds.symbols if ds.symbols else [ds.name]
    target = symbol if (symbol and symbol in sym_list) else sym_list[0]
    ctx = _build_ctx_from_panel({target: df})
    return ctx, df, target


def _build_ctx_from_panel(panel: Dict[str, pd.DataFrame]) -> FactorContext:
    """从 {symbol: df(含OHLCV)} 构造 FactorContext，必要列缺失时降级处理。"""
    try:
        return FactorContext.from_dict(panel)
    except KeyError as e:
        # 数据集可能只有部分列（如没有 amount），尝试兜底
        sample = next(iter(panel.values()))
        logger.warning("FactorContext.from_dict failed: %s, available cols: %s", e, list(sample.columns))
        required = ["open", "high", "low", "close", "volume"]
        # 如果确实缺 OHLCV 列，抛错
        for col in required:
            if col not in sample.columns:
                raise HTTPException(400, f"Dataset missing required column '{col}' for factor calculation")
        return FactorContext.from_dict(panel)


def _extract_symbol_series(factor_df: pd.DataFrame, symbol: str) -> pd.Series:
    """从 date × symbol 面板中取单个标的序列，symbol 不在列里时取第一列。"""
    if symbol in factor_df.columns:
        return factor_df[symbol]
    return factor_df.iloc[:, 0]


# ---------- 端点 ----------

@router.get("")
async def list_factors(category: Optional[str] = None):
    """因子列表，返回前端需要的 FactorInfo[]"""
    reg = get_registry()
    factors = reg.list_factors(category)
    return [f.to_dict() for f in factors]


@router.get("/categories")
async def list_categories():
    """分类列表"""
    reg = get_registry()
    return reg.list_categories()


@router.get("/cache/stats")
async def cache_stats():
    """缓存统计"""
    return get_factor_cache().stats()


@router.get("/{name}")
async def get_factor(name: str):
    info = get_registry().get(name)
    if info is None:
        raise HTTPException(404, f"Factor {name} not found")
    return info.to_dict()


@router.post("/compute")
async def compute_factor(req: ComputeRequest):
    """计算因子值，返回 {dates: [...], values: {symbol: [...]}}"""
    reg = get_registry()
    info = reg.get(req.factor_name)
    if info is None:
        raise HTTPException(404, f"Factor {req.factor_name} not found")

    cache = get_factor_cache()
    cached = cache.get(req.factor_name, req.dataset_id, req.symbol or "")
    if cached is not None:
        result_df = cached
    else:
        ctx, _, sym = _load_ctx_from_dataset(req.dataset_id, req.symbol)
        try:
            result_df = info.compute(ctx, **req.params)
        except Exception as e:
            raise HTTPException(500, f"Factor compute failed: {e}")
        cache.set(req.factor_name, req.dataset_id, result_df, req.symbol or "")

    # 序列化为前端可接受的 JSON
    out = {
        "factor_name": req.factor_name,
        "dates": [d.strftime("%Y-%m-%dT%H:%M:%S") for d in result_df.index],
        "values": {col: _series_to_list(result_df[col]) for col in result_df.columns},
    }
    return out


@router.post("/visualize")
async def visualize_factor(req: VisualizeRequest):
    """返回K线 + 因子值两个序列，供前端图表渲染。"""
    reg = get_registry()
    info = reg.get(req.factor_name)
    if info is None:
        raise HTTPException(404, f"Factor {req.factor_name} not found")

    ctx, full_df, symbol = _load_ctx_from_dataset(req.dataset_id, req.symbol)
    try:
        factor_df = info.compute(ctx, **req.params)
    except Exception as e:
        raise HTTPException(500, f"Factor compute failed: {e}")

    factor_series = _extract_symbol_series(factor_df, symbol)
    # OHLC: 单标的
    if "symbol" in full_df.columns:
        ohlcv = full_df[full_df["symbol"] == symbol].sort_index()
    else:
        ohlcv = full_df

    # 对齐并截断到 limit
    common_idx = factor_series.dropna().index.intersection(ohlcv.index)
    if len(common_idx) == 0:
        common_idx = ohlcv.index[-req.limit:]
    common_idx = common_idx[-req.limit:]

    candles = []
    factor_points = []
    for d in common_idx:
        ts = d.strftime("%Y-%m-%dT%H:%M:%S")
        row = ohlcv.loc[d]
        try:
            o = float(row.get("open", np.nan))
            h = float(row.get("high", np.nan))
            l = float(row.get("low", np.nan))
            c = float(row.get("close", np.nan))
        except Exception:
            continue
        candles.append({"t": ts, "o": o, "h": h, "l": l, "c": c})
        fv = factor_series.loc[d] if d in factor_series.index else np.nan
        factor_points.append({"t": ts, "v": None if pd.isna(fv) else float(fv)})

    return {
        "factor_name": req.factor_name,
        "symbol": symbol,
        "candles": candles,
        "factor": factor_points,
    }


@router.post("/ic")
async def factor_ic(req: ICRequest):
    """计算 IC（Pearson 相关）与 Rank IC（Spearman）——单标的时用滚动收益自相关近似。"""
    reg = get_registry()
    info = reg.get(req.factor_name)
    if info is None:
        raise HTTPException(404, f"Factor {req.factor_name} not found")

    ctx, _, symbol = _load_ctx_from_dataset(req.dataset_id, req.symbol)
    try:
        factor_df = info.compute(ctx, **req.params)
    except Exception as e:
        raise HTTPException(500, f"Factor compute failed: {e}")

    f = _extract_symbol_series(factor_df, symbol).dropna()
    close = ctx.close[symbol] if symbol in ctx.close.columns else ctx.close.iloc[:, 0]
    # forward return
    forward_ret = close.shift(-req.forward_period) / close - 1

    # 截面IC：对每一期计算因子值与forward return的相关；
    # 单标的场景下用滚动窗口（窗口内因子值与收益相关）近似。
    # 多标的则做截面 IC。
    n_symbols = factor_df.shape[1]
    ic_list: List[float] = []
    ric_list: List[float] = []
    ic_dates: List[str] = []

    if n_symbols > 1:
        # 截面 IC
        aligned = pd.concat(
            {"f": factor_df, "r": forward_ret.to_frame() if isinstance(forward_ret, pd.Series) else forward_ret},
            axis=1,
        )
        for d in factor_df.index:
            try:
                if isinstance(forward_ret, pd.Series):
                    r = forward_ret.reindex(factor_df.columns)
                    f_row = factor_df.loc[d]
                else:
                    r = forward_ret.loc[d]
                    f_row = factor_df.loc[d]
                df_pair = pd.DataFrame({"f": f_row, "r": r}).dropna()
                if len(df_pair) < 5:
                    continue
                ic = df_pair["f"].corr(df_pair["r"], method="pearson")
                ric = df_pair["f"].corr(df_pair["r"], method="spearman")
                if pd.isna(ic) or pd.isna(ric):
                    continue
                ic_list.append(float(ic))
                ric_list.append(float(ric))
                ic_dates.append(d.strftime("%Y-%m-%dT%H:%M:%S"))
            except Exception:
                continue
    else:
        # 单标的 → 时序 IC：用滚动窗口 60 期计算因子和 forward return 的相关
        win = min(60, len(f) // 2)
        if win < 10:
            win = max(10, len(f) // 3)
        df_pair = pd.DataFrame({"f": f, "r": forward_ret}).dropna()
        for end in range(win, len(df_pair)):
            sub = df_pair.iloc[end - win:end]
            if len(sub) < 10:
                continue
            ic = sub["f"].corr(sub["r"], method="pearson")
            ric = sub["f"].corr(sub["r"], method="spearman")
            if pd.isna(ic) or pd.isna(ric):
                continue
            ic_list.append(float(ic))
            ric_list.append(float(ric))
            ic_dates.append(df_pair.index[end].strftime("%Y-%m-%dT%H:%M:%S"))

    if not ic_list:
        raise HTTPException(400, "Not enough data to compute IC")

    ic_arr = np.array(ic_list)
    ric_arr = np.array(ric_list)

    def _stats(arr: np.ndarray) -> Dict[str, float]:
        return {
            "mean_ic": float(np.nanmean(arr)),
            "std_ic": float(np.nanstd(arr)),
            "ic_ir": float(np.nanmean(arr) / (np.nanstd(arr) + 1e-12)),
            "ic_positive": float((arr > 0).mean()),
            "count": int(len(arr)),
        }

    # turnover: 因子方向变化比例（近似）
    sign_change = (np.sign(f).diff().fillna(0) != 0).mean() if len(f) > 1 else 0.0

    ic_series = [{"t": t, "v": v} for t, v in zip(ic_dates, ic_list)]
    ric_series = [{"t": t, "v": v} for t, v in zip(ic_dates, ric_list)]

    return {
        "factor_name": req.factor_name,
        "forward_period": req.forward_period,
        "ic_stats": _stats(ic_arr),
        "rank_ic_stats": _stats(ric_arr),
        "ic_series": ic_series,
        "rank_ic_series": ric_series,
        "turnover": float(sign_change),
        "coverage": float(len(f.dropna()) / len(close) if len(close) > 0 else 0),
    }


@router.post("/correlation")
async def factor_correlation(req: CorrelationRequest):
    """计算多因子两两相关系数矩阵（在单个标的时序上）。"""
    reg = get_registry()
    ctx, _, symbol = _load_ctx_from_dataset(req.dataset_id, req.symbol)

    series_map: Dict[str, pd.Series] = {}
    for fname in req.factor_names:
        info = reg.get(fname)
        if info is None:
            raise HTTPException(404, f"Factor {fname} not found")
        try:
            out = info.compute(ctx)
        except Exception as e:
            raise HTTPException(500, f"Factor {fname} compute failed: {e}")
        s = _extract_symbol_series(out, symbol)
        series_map[fname] = s

    df = pd.DataFrame(series_map).dropna(how="any")
    if len(df) < 10:
        raise HTTPException(400, "Not enough overlapping data points for correlation")
    corr = df.corr(method="pearson")

    labels = list(corr.columns)
    matrix = [[None if pd.isna(corr.loc[a, b]) else float(corr.loc[a, b]) for b in labels] for a in labels]
    return {"labels": labels, "matrix": matrix}


# ---------- 辅助 ----------

def _series_to_list(s: pd.Series) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for v in s.values:
        if pd.isna(v):
            out.append(None)
        else:
            try:
                out.append(float(v))
            except Exception:
                out.append(None)
    return out
