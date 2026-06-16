"""
Experiment API — V4.4 重写

实验管理是研究平台真正的核心。

端点：
  GET  /api/v1/experiments                实验列表（搜索/过滤）
  POST /api/v1/experiments/search         多维度搜索
  GET  /api/v1/experiments/rank           排名
  POST /api/v1/experiments/compare        实验对比
  GET  /api/v1/experiments/tags/list      可用标签列表
  GET  /api/v1/experiments/{id}           实验详情（含指标+artifact）
  DELETE /api/v1/experiments/{id}         删除实验
  GET  /api/v1/experiments/{id}/trades    交易明细
  GET  /api/v1/experiments/{id}/equity    权益曲线
  GET  /api/v1/experiments/{id}/report    HTML 报告
  GET  /api/v1/experiments/{id}/tags      获取标签
  POST /api/v1/experiments/{id}/tags      添加标签
  DELETE /api/v1/experiments/{id}/tags    移除标签
  PUT  /api/v1/experiments/{id}/tags      设置标签（覆盖）
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ..research.repository import ExperimentRepository
from ..research.database import Database
from ..experiment.registry import ExperimentRegistry
from ..experiment.search import ExperimentSearch
from ..experiment.compare import ExperimentComparer
from ..experiment.report import ReportGenerator
from ..experiment.tags import TagManager
from ..experiment.artifact import ExperimentArtifact


router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


# ---- Pydantic 模型 ----
class SearchRequest(BaseModel):
    """多维度搜索请求"""
    q: str = Field("", description="模糊搜索（name/strategy/note）")
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
    """实验对比请求"""
    experiment_ids: List[str] = Field(..., description="要对比的实验 ID 列表")
    include_equity: bool = Field(True, description="是否包含权益曲线")
    include_trades: bool = Field(False, description="是否包含交易明细")


class TagRequest(BaseModel):
    """标签操作请求"""
    tag: str = Field(..., description="标签名")


class TagsRequest(BaseModel):
    """批量标签设置请求"""
    tags: List[str] = Field(..., description="标签列表（覆盖）")


class StatusRequest(BaseModel):
    """状态更新请求"""
    status: str = Field(..., description="状态：normal / candidate / production")


class FavoriteRequest(BaseModel):
    """收藏请求"""
    favorite: bool = Field(..., description="是否收藏")


class FolderRequest(BaseModel):
    """文件夹请求"""
    folder: str = Field(..., description="文件夹名称")


# ---- 全局组件 ----
_db: Optional[Database] = None
_repo: Optional[ExperimentRepository] = None
_registry: Optional[ExperimentRegistry] = None
_search: Optional[ExperimentSearch] = None
_comparer: Optional[ExperimentComparer] = None
_report_gen: Optional[ReportGenerator] = None
_tag_mgr: Optional[TagManager] = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def _get_repo() -> ExperimentRepository:
    global _repo
    if _repo is None:
        _repo = ExperimentRepository(db=_get_db())
    return _repo


def _get_registry() -> ExperimentRegistry:
    global _registry
    if _registry is None:
        _registry = ExperimentRegistry(db=_get_db())
        _registry.rebuild_index()
    return _registry


def _get_search() -> ExperimentSearch:
    global _search
    if _search is None:
        _search = ExperimentSearch(db=_get_db())
    return _search


def _get_comparer() -> ExperimentComparer:
    global _comparer
    if _comparer is None:
        _comparer = ExperimentComparer(db=_get_db())
    return _comparer


def _get_report_gen() -> ReportGenerator:
    global _report_gen
    if _report_gen is None:
        _report_gen = ReportGenerator(db=_get_db())
    return _report_gen


def _get_tag_mgr() -> TagManager:
    global _tag_mgr
    if _tag_mgr is None:
        _tag_mgr = TagManager(db=_get_db())
    return _tag_mgr


# ---- 内存缓存：task 完成后暂存 BacktestResult ----
_result_cache: Dict[str, Any] = {}


def cache_backtest_result(experiment_id: str, result: Any) -> None:
    """缓存 BacktestResult（BacktestService 完成后调用）"""
    _result_cache[experiment_id] = result


def get_cached_result(experiment_id: str) -> Optional[Any]:
    """获取缓存的 BacktestResult"""
    return _result_cache.get(experiment_id)


# ================================================================
# 固定路径端点（必须在 /{experiment_id} 之前注册，否则被拦截）
# ================================================================

@router.get("")
async def api_list_experiments(
    strategy: Optional[str] = Query(None, description="按策略名过滤"),
    dataset_id: Optional[str] = Query(None, description="按数据集过滤"),
    tag: Optional[str] = Query(None, description="按标签过滤"),
    sharpe_min: Optional[float] = Query(None, description="Sharpe 下限"),
    max_dd_max: Optional[float] = Query(None, description="最大回撤上限（正数）"),
    return_min: Optional[float] = Query(None, description="总收益下限"),
    status: Optional[str] = Query(None, description="按状态过滤（normal/candidate/production）"),
    favorite: Optional[bool] = Query(None, description="只看收藏"),
    folder: Optional[str] = Query(None, description="按文件夹过滤"),
    limit: int = Query(100, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """实验列表（搜索/过滤）"""
    repo = _get_repo()
    df = repo.search(
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
    # 前端过滤 status/favorite/folder（后续可移到 SQL）
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
    search = _get_search()
    return search.search(
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
    metric: str = Query("sharpe", description="排名指标（sharpe/total_return/max_drawdown/win_rate/trade_count）"),
    strategy: Optional[str] = Query(None, description="限定策略"),
    top: int = Query(20, description="返回数量"),
    ascending: bool = Query(False, description="是否升序"),
) -> List[Dict[str, Any]]:
    """按指标排名（Top N）"""
    search = _get_search()
    return search.rank_by(
        metric=metric,
        strategy=strategy,
        top=top,
        ascending=ascending,
    )


@router.post("/compare")
async def api_compare_experiments(req: CompareRequest) -> Dict[str, Any]:
    """实验对比（指标+权益曲线叠加+参数差异）"""
    comparer = _get_comparer()
    return comparer.compare(
        req.experiment_ids,
        include_equity=req.include_equity,
        include_trades=req.include_trades,
    )


@router.get("/tags/list")
async def api_list_available_tags() -> Dict[str, str]:
    """列出所有可用标签"""
    tag_mgr = _get_tag_mgr()
    return tag_mgr.list_available_tags()


@router.get("/folders/list")
async def api_list_folders() -> List[str]:
    """列出所有文件夹"""
    db = _get_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT folder FROM experiments WHERE folder != '' ORDER BY folder"
        ).fetchall()
    return [row["folder"] for row in rows]


@router.get("/timeline/global")
async def api_get_timeline(
    limit: int = Query(50, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """
    全局研究时间线

    返回最近的活动日志，包含实验信息
    """
    db = _get_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.experiment_id, a.action, a.detail, a.created_at,
                   e.name, e.strategy, e.status
            FROM activity_log a
            LEFT JOIN experiments e ON a.experiment_id = e.id
            ORDER BY a.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


# ================================================================
# 动态路径端点（/{experiment_id}）
# ================================================================

@router.get("/{experiment_id}")
async def api_get_experiment(experiment_id: str) -> Dict[str, Any]:
    """实验详情（含指标+artifact）"""
    registry = _get_registry()
    result = registry.get(experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return result


@router.delete("/{experiment_id}")
async def api_delete_experiment(experiment_id: str) -> Dict[str, str]:
    """删除实验"""
    registry = _get_registry()
    ok = registry.delete(experiment_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")
    return {"status": "deleted", "id": experiment_id}


@router.get("/{experiment_id}/trades")
async def api_get_trades(experiment_id: str) -> List[Dict[str, Any]]:
    """交易明细"""
    # 优先从 artifact 加载
    artifact = ExperimentArtifact(experiment_id)
    trades_df = artifact.load_trades()
    if trades_df is not None and not trades_df.empty:
        return trades_df.to_dict(orient="records")

    # 回退到内存缓存
    cached = get_cached_result(experiment_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail=f"No trades data for experiment '{experiment_id}'"
        )

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
    # 优先从 artifact 加载
    artifact = ExperimentArtifact(experiment_id)
    eq_df = artifact.load_equity()
    if eq_df is not None and not eq_df.empty:
        timestamps = [str(i) for i in eq_df.index]
        if "equity" in eq_df.columns:
            equity = eq_df["equity"].tolist()
        else:
            equity = eq_df.iloc[:, 0].tolist()
        return {
            "experiment_id": experiment_id,
            "timestamps": timestamps,
            "equity": equity,
        }

    # 回退到内存缓存
    cached = get_cached_result(experiment_id)
    if cached is None:
        raise HTTPException(
            status_code=404,
            detail=f"No equity data for experiment '{experiment_id}'"
        )

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

    return {
        "experiment_id": experiment_id,
        "timestamps": ts_list,
        "equity": eq_list,
    }


@router.get("/{experiment_id}/analytics")
async def api_get_analytics(experiment_id: str) -> Dict[str, Any]:
    """
    实验分析数据

    返回：
      drawdown_curve  回撤曲线
      monthly_returns 月度收益热力图数据
      annual_returns  年度收益柱状图数据
      rolling_sharpe  滚动 Sharpe
      rolling_drawdown 滚动最大回撤
      rolling_volatility 滚动波动率
      trade_stats     交易统计（分布/持仓时间/Top Winners/Losers）
      extended_metrics 扩展指标（Sortino/Calmar/Volatility/PF）
    """
    import numpy as np
    from datetime import datetime

    artifact = ExperimentArtifact(experiment_id)

    # 加载权益曲线
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

    # ---- Drawdown Curve ----
    if n >= 2:
        peak = np.maximum.accumulate(equity_arr)
        dd = ((equity_arr - peak) / peak * 100).tolist()
        result["drawdown_curve"] = dd
    else:
        result["drawdown_curve"] = []

    # ---- Monthly Returns ----
    monthly: Dict[str, Dict[str, float]] = {}
    annual: Dict[str, float] = {}

    if n >= 2 and timestamps_raw:
        try:
            # 解析时间戳
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

            # 计算每日收益率
            daily_returns = np.diff(equity_arr) / equity_arr[:-1]

            # 按月聚合
            from collections import defaultdict
            month_data: Dict[tuple, list] = defaultdict(list)
            year_data: Dict[int, list] = defaultdict(list)

            for i, dt in enumerate(dates[1:]):
                if dt is not None and i < len(daily_returns):
                    key = (dt.year, dt.month)
                    month_data[key].append(daily_returns[i])
                    year_data[dt.year].append(daily_returns[i])

            # 月度收益 = 月内日收益连乘 - 1
            month_map = {}
            for (yr, mo), rets in sorted(month_data.items()):
                month_ret = (np.array(rets) + 1).prod() - 1
                if yr not in month_map:
                    month_map[yr] = {}
                month_map[yr][f"{mo:02d}"] = round(float(month_ret * 100), 2)
            result["monthly_returns"] = month_map

            # 年度收益
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

    # ---- Rolling Metrics ----
    window = 60  # 60 天滚动窗口
    if n >= window + 1:
        daily_rets = np.diff(equity_arr) / equity_arr[:-1]
        rolling_sharpe = []
        rolling_dd = []
        rolling_vol = []

        for i in range(len(daily_rets) - window + 1):
            w = daily_rets[i:i + window]
            # Sharpe
            if w.std() > 0:
                rolling_sharpe.append(round(float(w.mean() / w.std() * np.sqrt(252)), 3))
            else:
                rolling_sharpe.append(0.0)
            # Volatility
            rolling_vol.append(round(float(w.std() * np.sqrt(252) * 100), 2))
            # Rolling MaxDD
            cum = (1 + w).cumprod()
            pk = np.maximum.accumulate(cum)
            rdd = ((cum - pk) / pk * 100).min()
            rolling_dd.append(round(float(rdd), 2))

        # 对齐时间戳（从 window 开始）
        dd_offset = window  # daily_rets 比 equity 少 1
        result["rolling_sharpe"] = rolling_sharpe
        result["rolling_drawdown"] = rolling_dd
        result["rolling_volatility"] = rolling_vol
        result["rolling_start_index"] = dd_offset
    else:
        result["rolling_sharpe"] = []
        result["rolling_drawdown"] = []
        result["rolling_volatility"] = []
        result["rolling_start_index"] = 0

    # ---- Extended Metrics ----
    if n >= 2:
        daily_rets = np.diff(equity_arr) / equity_arr[:-1]
        # Sortino
        downside = daily_rets[daily_rets < 0]
        if len(downside) > 0 and downside.std() > 0:
            sortino = float(daily_rets.mean() / downside.std() * np.sqrt(252))
        else:
            sortino = 0.0
        # Calmar
        ann_ret = float((equity_arr[-1] / equity_arr[0]) ** (252 / max(n - 1, 1)) - 1)
        mdd = float(((equity_arr - np.maximum.accumulate(equity_arr)) / np.maximum.accumulate(equity_arr)).min())
        calmar = ann_ret / abs(mdd) if mdd != 0 else 0.0
        # Volatility
        vol = float(daily_rets.std() * np.sqrt(252) * 100)

        result["extended_metrics"] = {
            "sortino": round(sortino, 3),
            "calmar": round(calmar, 3),
            "volatility": round(vol, 2),
        }
    else:
        result["extended_metrics"] = {}

    # ---- Trade Stats ----
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
        # PnL 分布
        bins = 20
        if pnls:
            hist, edges = np.histogram(pnls, bins=bins)
            result["pnl_distribution"] = {
                "counts": hist.tolist(),
                "edges": [round(float(e), 2) for e in edges],
            }
        else:
            result["pnl_distribution"] = {"counts": [], "edges": []}

        # 持仓时间
        holding_times = []
        for t in trades_list:
            try:
                if t.get("entry_time") and t.get("exit_time"):
                    entry = datetime.fromisoformat(str(t["entry_time"]).replace("Z", "+00:00").replace(" ", "T"))
                    exit_ = datetime.fromisoformat(str(t["exit_time"]).replace("Z", "+00:00").replace(" ", "T"))
                    holding_times.append((exit_ - entry).total_seconds() / 86400)  # 天
            except Exception:
                pass

        if holding_times:
            result["holding_stats"] = {
                "avg_days": round(float(np.mean(holding_times)), 1),
                "max_days": round(float(np.max(holding_times)), 1),
                "min_days": round(float(np.min(holding_times)), 1),
                "median_days": round(float(np.median(holding_times)), 1),
            }
        else:
            result["holding_stats"] = {}

        # Top Winners / Losers
        sorted_by_pnl = sorted(trades_list, key=lambda t: t.get("pnl", 0), reverse=True)
        result["top_winners"] = sorted_by_pnl[:5]
        result["top_losers"] = sorted_by_pnl[-5:][::-1]

        # Profit Factor
        gross_profit = sum(t.get("pnl", 0) for t in trades_list if t.get("pnl", 0) > 0)
        gross_loss = abs(sum(t.get("pnl", 0) for t in trades_list if t.get("pnl", 0) < 0))
        pf = gross_profit / gross_loss if gross_loss > 0 else 0.0
        result["extended_metrics"]["profit_factor"] = round(pf, 2)
    else:
        result["pnl_distribution"] = {"counts": [], "edges": []}
        result["holding_stats"] = {}
        result["top_winners"] = []
        result["top_losers"] = []

    return result


@router.get("/{experiment_id}/report")
async def api_get_report(
    experiment_id: str,
    format: str = Query("html", description="报告格式（html/markdown）"),
) -> Dict[str, str]:
    """生成实验报告"""
    report_gen = _get_report_gen()
    if format == "markdown":
        content = report_gen.generate_markdown(experiment_id)
    else:
        content = report_gen.generate_html(experiment_id)
    return {
        "experiment_id": experiment_id,
        "format": format,
        "content": content,
    }


# ---- Tags 端点 ----

@router.get("/{experiment_id}/tags")
async def api_get_experiment_tags(experiment_id: str) -> List[str]:
    """获取实验标签"""
    tag_mgr = _get_tag_mgr()
    return tag_mgr.get_tags(experiment_id)


@router.post("/{experiment_id}/tags")
async def api_add_tag(experiment_id: str, req: TagRequest) -> Dict[str, Any]:
    """添加标签"""
    tag_mgr = _get_tag_mgr()
    tag_mgr.add_tag(experiment_id, req.tag)
    tags = tag_mgr.get_tags(experiment_id)
    return {"experiment_id": experiment_id, "tags": tags}


@router.delete("/{experiment_id}/tags")
async def api_remove_tag(experiment_id: str, req: TagRequest) -> Dict[str, Any]:
    """移除标签"""
    tag_mgr = _get_tag_mgr()
    tag_mgr.remove_tag(experiment_id, req.tag)
    tags = tag_mgr.get_tags(experiment_id)
    return {"experiment_id": experiment_id, "tags": tags}


@router.put("/{experiment_id}/tags")
async def api_set_tags(experiment_id: str, req: TagsRequest) -> Dict[str, Any]:
    """设置标签（覆盖）"""
    tag_mgr = _get_tag_mgr()
    tag_mgr.set_tags(experiment_id, req.tags)
    tags = tag_mgr.get_tags(experiment_id)
    return {"experiment_id": experiment_id, "tags": tags}


# ---- Status / Favorite / Folder 端点 ----

# status 端点已移至文件末尾（带活动日志）


@router.put("/{experiment_id}/favorite")
async def api_set_favorite(experiment_id: str, req: FavoriteRequest) -> Dict[str, Any]:
    """设置收藏"""
    db = _get_db()
    fav = 1 if req.favorite else 0
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE experiments SET favorite = ? WHERE id = ?",
            (fav, experiment_id),
        )
    return {"experiment_id": experiment_id, "favorite": req.favorite}


@router.put("/{experiment_id}/folder")
async def api_set_folder(experiment_id: str, req: FolderRequest) -> Dict[str, Any]:
    """设置文件夹"""
    db = _get_db()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE experiments SET folder = ? WHERE id = ?",
            (req.folder, experiment_id),
        )
    return {"experiment_id": experiment_id, "folder": req.folder}


# ---- Note / Lineage / Activity 端点 ----

class NoteRequest(BaseModel):
    """备注更新请求"""
    note: str = Field(..., description="研究备注")


class ParentRequest(BaseModel):
    """父实验设置请求"""
    parent_id: str = Field(..., description="父实验 ID")


@router.put("/{experiment_id}/note")
async def api_set_note(experiment_id: str, req: NoteRequest) -> Dict[str, Any]:
    """更新实验研究备注"""
    db = _get_db()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE experiments SET note = ? WHERE id = ?",
            (req.note, experiment_id),
        )
    _log_activity(experiment_id, "note_updated", req.note[:100])
    return {"experiment_id": experiment_id, "note": req.note}


@router.put("/{experiment_id}/parent")
async def api_set_parent(experiment_id: str, req: ParentRequest) -> Dict[str, Any]:
    """设置父实验（血缘关系）"""
    db = _get_db()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE experiments SET parent_id = ? WHERE id = ?",
            (req.parent_id, experiment_id),
        )
    _log_activity(experiment_id, "parent_set", f"parent={req.parent_id}")
    return {"experiment_id": experiment_id, "parent_id": req.parent_id}


@router.get("/{experiment_id}/lineage")
async def api_get_lineage(experiment_id: str) -> Dict[str, Any]:
    """
    获取实验血缘关系

    返回：
      ancestors  祖先链（从根到父）
      children   直接子实验
      siblings   同父兄弟实验
      family     完整家族树
    """
    db = _get_db()

    def _get_exp(conn: Any, eid: str) -> Optional[Dict]:
        row = conn.execute(
            "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE id = ?",
            (eid,),
        ).fetchone()
        if row is None:
            return None
        d = dict(row)
        try:
            d["params"] = json.loads(d.pop("params_json", "{}"))
        except Exception:
            d["params"] = {}
        return d

    with db.get_connection() as conn:
        # 当前实验
        current = _get_exp(conn, experiment_id)
        if current is None:
            raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")

        # 祖先链
        ancestors = []
        pid = current.get("parent_id", "")
        visited = {experiment_id}
        while pid and pid not in visited:
            visited.add(pid)
            parent = _get_exp(conn, pid)
            if parent is None:
                break
            ancestors.append(parent)
            pid = parent.get("parent_id", "")

        # 子实验
        children_rows = conn.execute(
            "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE parent_id = ?",
            (experiment_id,),
        ).fetchall()
        children = []
        for row in children_rows:
            d = dict(row)
            try:
                d["params"] = json.loads(d.pop("params_json", "{}"))
            except Exception:
                d["params"] = {}
            children.append(d)

        # 兄弟实验
        siblings = []
        parent_id = current.get("parent_id", "")
        if parent_id:
            sib_rows = conn.execute(
                "SELECT id, name, strategy, params_json, created_at, parent_id, status FROM experiments WHERE parent_id = ? AND id != ?",
                (parent_id, experiment_id),
            ).fetchall()
            for row in sib_rows:
                d = dict(row)
                try:
                    d["params"] = json.loads(d.pop("params_json", "{}"))
                except Exception:
                    d["params"] = {}
                siblings.append(d)

        # 完整家族树（从根节点开始递归）
        root_id = ancestors[-1]["id"] if ancestors else experiment_id

        def _build_tree(conn: Any, eid: str, visited_set: set) -> Dict:
            node = _get_exp(conn, eid)
            if node is None:
                return {}
            node["children"] = []
            child_rows = conn.execute(
                "SELECT id FROM experiments WHERE parent_id = ?",
                (eid,),
            ).fetchall()
            for cr in child_rows:
                cid = cr["id"]
                if cid not in visited_set:
                    visited_set.add(cid)
                    child_tree = _build_tree(conn, cid, visited_set)
                    if child_tree:
                        node["children"].append(child_tree)
            return node

        family = _build_tree(conn, root_id, {root_id})

    return {
        "experiment_id": experiment_id,
        "ancestors": list(reversed(ancestors)),
        "children": children,
        "siblings": siblings,
        "family": family,
    }


@router.get("/{experiment_id}/activity")
async def api_get_activity(
    experiment_id: str,
    limit: int = Query(50, description="返回数量上限"),
) -> List[Dict[str, Any]]:
    """获取实验活动日志"""
    db = _get_db()
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT id, experiment_id, action, detail, created_at FROM activity_log WHERE experiment_id = ? ORDER BY created_at DESC LIMIT ?",
            (experiment_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---- 活动日志辅助函数 ----

def _log_activity(experiment_id: str, action: str, detail: str = "") -> None:
    """记录实验活动日志"""
    from datetime import datetime, timezone
    db = _get_db()
    now = datetime.now(timezone.utc).isoformat()
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO activity_log (experiment_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (experiment_id, action, detail, now),
        )


# 扩展 status 端点，增加活动日志
@router.put("/{experiment_id}/status")
async def api_set_status(experiment_id: str, req: StatusRequest) -> Dict[str, Any]:
    """设置实验状态（research / candidate / paper_trading / production）"""
    db = _get_db()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE experiments SET status = ? WHERE id = ?",
            (req.status, experiment_id),
        )
    _log_activity(experiment_id, "status_changed", f"status={req.status}")
    return {"experiment_id": experiment_id, "status": req.status}
