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
    return df.to_dict(orient="records")


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
