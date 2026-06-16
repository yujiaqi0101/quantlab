"""
Experiment API — V2.0 重构

通过 ExperimentService 统一调用，API 层不直接碰 core

端点：
  GET  /api/v1/experiments                实验列表（搜索/过滤）
  POST /api/v1/experiments/search         多维度搜索
  GET  /api/v1/experiments/rank           排名
  POST /api/v1/experiments/compare        实验对比
  GET  /api/v1/experiments/tags/list      可用标签列表
  GET  /api/v1/experiments/{id}           实验详情
  DELETE /api/v1/experiments/{id}         删除实验
  GET  /api/v1/experiments/{id}/trades    交易明细
  GET  /api/v1/experiments/{id}/equity    权益曲线
  GET  /api/v1/experiments/{id}/analytics 分析数据
  GET  /api/v1/experiments/{id}/tags      获取标签
  POST /api/v1/experiments/{id}/tags      添加标签
  PUT  /api/v1/experiments/{id}/status    设置状态
  PUT  /api/v1/experiments/{id}/favorite  设置收藏
  PUT  /api/v1/experiments/{id}/folder    设置文件夹
  PUT  /api/v1/experiments/{id}/note      更新备注
  PUT  /api/v1/experiments/{id}/parent    设置父实验
  GET  /api/v1/experiments/{id}/lineage   血缘关系
  GET  /api/v1/experiments/{id}/activity  活动日志
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ..services import get_service
from ..experiment.artifact import ExperimentArtifact


router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


def _svc():
    return get_service("experiment")


# ---- 内存缓存：task 完成后暂存 BacktestResult ----
_result_cache: Dict[str, Any] = {}


def cache_backtest_result(experiment_id: str, result: Any) -> None:
    """缓存 BacktestResult（BacktestService 完成后调用）"""
    _result_cache[experiment_id] = result


def get_cached_result(experiment_id: str) -> Optional[Any]:
    """获取缓存的 BacktestResult"""
    return _result_cache.get(experiment_id)


# ---- Pydantic 模型 ----

class SearchRequest(BaseModel):
    q: str = Field("", description="模糊搜索")
    strategy: Optional[str] = Field(None, description="策略 ID")
    dataset_id: Optional[str] = Field(None, description="数据集 ID")
    sharpe_gt: Optional[float] = Field(None, description="Sharpe 下限")
    sharpe_lt: Optional[float] = Field(None, description="Sharpe 上限")
    return_gt: Optional[float] = Field(None, description="总收益下限(%)")
    return_lt: Optional[float] = Field(None, description="总收益上限(%)")
    max_dd_lt: Optional[float] = Field(None, description="最大回撤上限(正数%)")
    trade_count_gt: Optional[int] = Field(None, description="最小交易次数")
    tags: Optional[List[str]] = Field(None, description="包含任意标签")
    date_from: Optional[str] = Field(None, description="起始日期")
    date_to: Optional[str] = Field(None, description="结束日期")
    limit: int = Field(100, description="返回数量上限")


class CompareRequest(BaseModel):
    experiment_ids: List[str] = Field(..., description="要对比的实验 ID 列表")
    include_equity: bool = Field(True, description="是否包含权益曲线")
    include_trades: bool = Field(False, description="是否包含交易明细")


class TagRequest(BaseModel):
    tag: str = Field(..., description="标签名")


class TagsRequest(BaseModel):
    tags: List[str] = Field(..., description="标签列表（覆盖）")


class StatusRequest(BaseModel):
    status: str = Field(..., description="状态：normal / candidate / production")


class FavoriteRequest(BaseModel):
    favorite: bool = Field(..., description="是否收藏")


class FolderRequest(BaseModel):
    folder: str = Field(..., description="文件夹名称")


class NoteRequest(BaseModel):
    note: str = Field(..., description="研究备注")


class ParentRequest(BaseModel):
    parent_id: str = Field(..., description="父实验 ID")


# ================================================================
# 固定路径端点
# ================================================================

@router.get("")
async def api_list_experiments(
    strategy: Optional[str] = Query(None, description="按策略名过滤"),
    dataset_id: Optional[str] = Query(None, description="按数据集过滤"),
    tag: Optional[str] = Query(None, description="按标签过滤"),
    sharpe_min: Optional[float] = Query(None, description="Sharpe 下限"),
    max_dd_max: Optional[float] = Query(None, description="最大回撤上限（正数）"),
    return_min: Optional[float] = Query(None, description="总收益下限"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    favorite: Optional[bool] = Query(None, description="只看收藏"),
    folder: Optional[str] = Query(None, description="按文件夹过滤"),
    limit: int = Query(100, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """实验列表（搜索/过滤）"""
    svc = _svc()
    df = svc.search_experiments(
        strategy=strategy,
        tag=tag,
        sharpe_min=sharpe_min,
        max_dd_max=max_dd_max,
        return_min=return_min,
        dataset_id=dataset_id,
        limit=limit,
    )
    if df.empty:
        return []
    records = df.to_dict(orient="records")
    if status:
        records = [r for r in records if r.get("status", "normal") == status]
    if favorite:
        records = [r for r in records if r.get("favorite", 0) == 1]
    if folder:
        records = [r for r in records if r.get("folder", "") == folder]
    return records


@router.post("/search")
async def api_search_experiments(req: SearchRequest) -> List[Dict[str, Any]]:
    """多维度搜索"""
    svc = _svc()
    return svc.multi_search(
        q=req.q,
        strategy=req.strategy,
        dataset_id=req.dataset_id,
        sharpe_gt=req.sharpe_gt,
        sharpe_lt=req.sharpe_lt,
        return_gt=req.return_gt,
        return_lt=req.return_lt,
        max_dd_lt=req.max_dd_lt,
        trade_count_gt=req.trade_count_gt,
        tags=req.tags,
        date_from=req.date_from,
        date_to=req.date_to,
        limit=req.limit,
    )


@router.get("/rank")
async def api_rank_experiments(
    metric: str = Query("sharpe", description="排名指标"),
    strategy: Optional[str] = Query(None, description="限定策略"),
    top: int = Query(20, description="返回数量"),
    ascending: bool = Query(False, description="是否升序"),
) -> List[Dict[str, Any]]:
    """按指标排名"""
    svc = _svc()
    return svc.rank_by(metric=metric, strategy=strategy, top=top, ascending=ascending)


@router.post("/compare")
async def api_compare_experiments(req: CompareRequest) -> Dict[str, Any]:
    """实验对比"""
    svc = _svc()
    return svc.compare(
        req.experiment_ids,
        include_equity=req.include_equity,
        include_trades=req.include_trades,
    )


@router.get("/tags/list")
async def api_list_available_tags() -> Dict[str, str]:
    """列出所有可用标签"""
    return _svc().list_available_tags()


@router.get("/folders/list")
async def api_list_folders() -> List[str]:
    """列出所有文件夹"""
    return _svc().list_folders()


@router.get("/timeline/global")
async def api_get_timeline(
    limit: int = Query(50, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """全局研究时间线"""
    return _svc().get_timeline(limit=limit)


# ================================================================
# 动态路径端点（/{experiment_id}）
# ================================================================

@router.get("/{experiment_id}")
async def api_get_experiment(experiment_id: str) -> Dict[str, Any]:
    """实验详情"""
    svc = _svc()
    result = svc.get_experiment_full(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return result


@router.delete("/{experiment_id}")
async def api_delete_experiment(experiment_id: str) -> Dict[str, str]:
    """删除实验"""
    svc = _svc()
    ok = svc.delete_experiment(experiment_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return {"status": "deleted", "id": experiment_id}


@router.get("/{experiment_id}/trades")
async def api_get_trades(experiment_id: str) -> List[Dict[str, Any]]:
    """交易明细"""
    svc = _svc()
    artifact = svc.get_artifact(experiment_id)
    trades_df = artifact.load_trades()
    if trades_df is not None and not trades_df.empty:
        return trades_df.to_dict(orient="records")

    cached = get_cached_result(experiment_id)
    if cached is None:
        raise HTTPException(status_code=404, detail=f"No trades data for experiment '{experiment_id}'")

    trades: List[Dict[str, Any]] = []
    tb = getattr(cached, "tradebook", None)
    if tb is not None and hasattr(tb, "closed_trades"):
        for t in tb.closed_trades:
            trades.append({
                "entry_time": str(t.entry_time) if t.entry_time else "",
                "exit_time": str(t.exit_time) if t.exit_time else "",
                "symbol": t.symbol,
                "side": "long",
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "qty": t.qty,
                "pnl": t.pnl,
                "return_pct": t.return_pct,
            })
    return trades


@router.get("/{experiment_id}/equity")
async def api_get_equity_curve(experiment_id: str) -> Dict[str, Any]:
    """权益曲线"""
    svc = _svc()
    artifact = svc.get_artifact(experiment_id)
    eq_df = artifact.load_equity()
    if eq_df is not None and not eq_df.empty:
        timestamps = [str(i) for i in eq_df.index]
        if "equity" in eq_df.columns:
            equity = eq_df["equity"].tolist()
        else:
            equity = eq_df.iloc[:, 0].tolist()
        return {"experiment_id": experiment_id, "timestamps": timestamps, "equity": equity}

    cached = get_cached_result(experiment_id)
    if cached is None:
        raise HTTPException(status_code=404, detail=f"No equity data for experiment '{experiment_id}'")

    equity_curve = getattr(cached, "equity_curve", [])
    timestamps = getattr(cached, "timestamps", None)
    if timestamps is None:
        portfolio = getattr(cached, "portfolio", None)
        if portfolio is not None:
            timestamps = getattr(portfolio, "timestamps", None)

    ts_list = [str(t) for t in timestamps] if timestamps else []
    eq_list = []
    if equity_curve is not None:
        try:
            eq_list = [float(v) for v in equity_curve]
        except (TypeError, ValueError):
            eq_list = []

    return {"experiment_id": experiment_id, "timestamps": ts_list, "equity": eq_list}


@router.get("/{experiment_id}/analytics")
async def api_get_analytics(experiment_id: str) -> Dict[str, Any]:
    """
    实验分析数据

    返回：drawdown_curve, monthly_returns, annual_returns,
         rolling_sharpe, rolling_drawdown, rolling_volatility,
         trade_stats, extended_metrics
    """
    from datetime import datetime
    from collections import defaultdict

    svc = _svc()
    artifact = svc.get_artifact(experiment_id)

    eq_df = artifact.load_equity()
    if eq_df is None or eq_df.empty:
        cached = get_cached_result(experiment_id)
        if cached is None:
            raise HTTPException(status_code=404, detail=f"No equity data for experiment '{experiment_id}'")
        equity = list(cached.equity_curve or [])
        timestamps_raw = list(cached.timestamps or [])
        if not timestamps_raw and cached.portfolio:
            timestamps_raw = list(cached.portfolio.timestamps or [])
    else:
        equity = eq_df["equity"].tolist() if "equity" in eq_df.columns else eq_df.iloc[:, 0].tolist()
        timestamps_raw = [str(i) for i in eq_df.index]

    equity_arr = np.array(equity, dtype=float)
    n = len(equity_arr)
    result: Dict[str, Any] = {}

    # Drawdown Curve
    if n >= 2:
        peak = np.maximum.accumulate(equity_arr)
        dd = ((equity_arr - peak) / peak * 100).tolist()
        result["drawdown_curve"] = dd
    else:
        result["drawdown_curve"] = []

    # Monthly / Annual Returns
    monthly: Dict[str, Dict[str, float]] = {}
    annual: Dict[str, float] = {}

    if n >= 2 and timestamps_raw:
        try:
            dates = []
            for t in timestamps_raw:
                try:
                    if isinstance(t, str):
                        dt = datetime.fromisoformat(t.replace("Z", "+00:00").replace(" ", "T"))
                    else:
                        dt = pd.Timestamp(t).to_pydatetime()
                    dates.append(dt)
                except Exception:
                    dates.append(None)

            daily_returns = np.diff(equity_arr) / equity_arr[:-1]
            month_data: Dict[tuple, list] = defaultdict(list)
            year_data: Dict[int, list] = defaultdict(list)

            for i, dt in enumerate(dates[1:]):
                if dt is not None and i < len(daily_returns):
                    key = (dt.year, dt.month)
                    month_data[key].append(daily_returns[i])
                    year_data[dt.year].append(daily_returns[i])

            month_map = {}
            for (yr, mo), rets in sorted(month_data.items()):
                month_ret = (np.array(rets) + 1).prod() - 1
                if yr not in month_map:
                    month_map[yr] = {}
                month_map[yr][f"{mo:02d}"] = round(float(month_ret * 100), 2)
            result["monthly_returns"] = month_map

            for yr, rets in sorted(year_data.items()):
                year_ret = (np.array(rets) + 1).prod() - 1
                annual[str(yr)] = round(float(year_ret * 100), 2)
            result["annual_returns"] = annual
        except Exception:
            result["monthly_returns"] = {}
            result["annual_returns"] = {}
    else:
        result["monthly_returns"] = {}
        result["annual_returns"] = {}

    # Rolling Metrics
    window = 60
    if n >= window + 1:
        daily_rets = np.diff(equity_arr) / equity_arr[:-1]
        rolling_sharpe = []
        rolling_dd = []
        rolling_vol = []

        for i in range(len(daily_rets) - window + 1):
            w = daily_rets[i:i + window]
            if w.std() > 0:
                rolling_sharpe.append(round(float(w.mean() / w.std() * np.sqrt(252)), 3))
            else:
                rolling_sharpe.append(0.0)
            rolling_vol.append(round(float(w.std() * np.sqrt(252) * 100), 2))
            cum = (1 + w).cumprod()
            pk = np.maximum.accumulate(cum)
            rdd = ((cum - pk) / pk * 100).min()
            rolling_dd.append(round(float(rdd), 2))

        result["rolling_sharpe"] = rolling_sharpe
        result["rolling_drawdown"] = rolling_dd
        result["rolling_volatility"] = rolling_vol
        result["rolling_start_index"] = window
    else:
        result["rolling_sharpe"] = []
        result["rolling_drawdown"] = []
        result["rolling_volatility"] = []
        result["rolling_start_index"] = 0

    # Extended Metrics
    if n >= 2:
        daily_rets = np.diff(equity_arr) / equity_arr[:-1]
        downside = daily_rets[daily_rets < 0]
        if len(downside) > 0 and downside.std() > 0:
            sortino = float(daily_rets.mean() / downside.std() * np.sqrt(252))
        else:
            sortino = 0.0
        ann_ret = float((equity_arr[-1] / equity_arr[0]) ** (252 / max(n - 1, 1)) - 1)
        mdd = float(((equity_arr - np.maximum.accumulate(equity_arr)) / np.maximum.accumulate(equity_arr)).min())
        calmar = ann_ret / abs(mdd) if mdd != 0 else 0.0
        vol = float(daily_rets.std() * np.sqrt(252) * 100)

        result["extended_metrics"] = {
            "sortino": round(sortino, 3),
            "calmar": round(calmar, 3),
            "volatility": round(vol, 2),
        }
    else:
        result["extended_metrics"] = {}

    # Trade Stats
    trades_df = artifact.load_trades()
    trades_list = []
    if trades_df is not None and not trades_df.empty:
        trades_list = trades_df.to_dict(orient="records")
    else:
        cached = get_cached_result(experiment_id)
        if cached and cached.tradebook:
            for t in cached.tradebook.closed_trades:
                trades_list.append({
                    "entry_time": str(t.entry_time) if t.entry_time else "",
                    "exit_time": str(t.exit_time) if t.exit_time else "",
                    "symbol": t.symbol,
                    "side": "long",
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "qty": t.qty,
                    "pnl": t.pnl,
                    "return_pct": t.return_pct,
                })

    if trades_list:
        pnls = [t.get("pnl", 0) for t in trades_list if t.get("pnl") is not None]
        rets = [t.get("return_pct", 0) for t in trades_list if t.get("return_pct") is not None]
        win_trades = [p for p in pnls if p > 0]
        loss_trades = [p for p in pnls if p < 0]

        # Sort by PnL for top winners/losers
        sorted_trades = sorted(trades_list, key=lambda x: x.get("pnl", 0) or 0, reverse=True)

        result["trade_stats"] = {
            "total": len(trades_list),
            "wins": len(win_trades),
            "losses": len(loss_trades),
            "win_rate": round(len(win_trades) / len(pnls), 4) if pnls else 0,
            "avg_pnl": round(float(np.mean(pnls)), 4) if pnls else 0,
            "avg_return": round(float(np.mean(rets)), 4) if rets else 0,
            "profit_factor": round(sum(win_trades) / abs(sum(loss_trades)), 3) if loss_trades and sum(loss_trades) != 0 else 0,
            "top_winners": sorted_trades[:5],
            "top_losers": sorted_trades[-5:],
        }
    else:
        result["trade_stats"] = {"total": 0, "wins": 0, "losses": 0, "win_rate": 0}

    return result


# ---- 标签操作 ----

@router.get("/{experiment_id}/tags")
async def api_get_tags(experiment_id: str) -> Dict[str, Any]:
    """获取实验标签"""
    svc = _svc()
    tag_mgr = svc._get_tag_mgr()
    return tag_mgr.get_tags(experiment_id)


@router.post("/{experiment_id}/tags")
async def api_add_tag(experiment_id: str, req: TagRequest) -> Dict[str, Any]:
    """添加标签"""
    svc = _svc()
    tag_mgr = svc._get_tag_mgr()
    tag_mgr.add_tag(experiment_id, req.tag)
    return {"experiment_id": experiment_id, "tag": req.tag, "action": "added"}


@router.delete("/{experiment_id}/tags")
async def api_remove_tag(experiment_id: str, req: TagRequest) -> Dict[str, Any]:
    """移除标签"""
    svc = _svc()
    tag_mgr = svc._get_tag_mgr()
    tag_mgr.remove_tag(experiment_id, req.tag)
    return {"experiment_id": experiment_id, "tag": req.tag, "action": "removed"}


@router.put("/{experiment_id}/tags")
async def api_set_tags(experiment_id: str, req: TagsRequest) -> Dict[str, Any]:
    """设置标签（覆盖）"""
    svc = _svc()
    tag_mgr = svc._get_tag_mgr()
    tag_mgr.set_tags(experiment_id, req.tags)
    return {"experiment_id": experiment_id, "tags": req.tags, "action": "set"}


# ---- 状态 / 收藏 / 文件夹 ----

@router.put("/{experiment_id}/status")
async def api_set_status(experiment_id: str, req: StatusRequest) -> Dict[str, Any]:
    """设置实验状态"""
    svc = _svc()
    svc.set_status(experiment_id, req.status)
    return {"experiment_id": experiment_id, "status": req.status}


@router.put("/{experiment_id}/favorite")
async def api_set_favorite(experiment_id: str, req: FavoriteRequest) -> Dict[str, Any]:
    """设置收藏"""
    svc = _svc()
    svc.set_favorite(experiment_id, req.favorite)
    return {"experiment_id": experiment_id, "favorite": req.favorite}


@router.put("/{experiment_id}/folder")
async def api_set_folder(experiment_id: str, req: FolderRequest) -> Dict[str, Any]:
    """设置文件夹"""
    svc = _svc()
    svc.set_folder(experiment_id, req.folder)
    return {"experiment_id": experiment_id, "folder": req.folder}


# ---- 备注 / 血缘 / 活动 ----

@router.put("/{experiment_id}/note")
async def api_set_note(experiment_id: str, req: NoteRequest) -> Dict[str, Any]:
    """更新实验研究备注"""
    svc = _svc()
    svc.set_note(experiment_id, req.note)
    return {"experiment_id": experiment_id, "note": req.note}


@router.put("/{experiment_id}/parent")
async def api_set_parent(experiment_id: str, req: ParentRequest) -> Dict[str, Any]:
    """设置父实验"""
    svc = _svc()
    svc.set_parent(experiment_id, req.parent_id)
    return {"experiment_id": experiment_id, "parent_id": req.parent_id}


@router.get("/{experiment_id}/lineage")
async def api_get_lineage(experiment_id: str) -> Dict[str, Any]:
    """获取实验血缘关系"""
    svc = _svc()
    result = svc.get_lineage(experiment_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{experiment_id}/activity")
async def api_get_activity(
    experiment_id: str,
    limit: int = Query(50, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """获取实验活动日志"""
    svc = _svc()
    return svc.get_activity(experiment_id, limit=limit)
