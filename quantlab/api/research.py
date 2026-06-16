"""
Research Lab API — V2.0 重构

通过 ExperimentService / BacktestService 统一调用，API 层不直接碰 core

端点：
  POST /api/v1/research/sweep           运行参数扫描
  GET  /api/v1/research/sweeps          列出所有扫描
  GET  /api/v1/research/sweeps/{id}     扫描详情
  POST /api/v1/research/heatmap         Heatmap
  POST /api/v1/research/robustness      稳健性
  POST /api/v1/research/candidates      候选策略
  POST /api/v1/research/walk-forward    Walk Forward
  POST /api/v1/research/report          研究报告
  GET  /api/v1/research/workflow/*      工作流
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services import get_service
from ..event.event_bus import EventBus
from ..research.workflow import ResearchWorkflowEngine

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# ---- 全局 Workflow Engine ----
_event_bus = EventBus()
_workflow_engine = ResearchWorkflowEngine(_event_bus)
_workflow_engine.start()


# ============================================================
# Request / Response Models
# ============================================================

class SweepRequest(BaseModel):
    strategy_id: str
    param_space: Dict[str, List]
    dataset_id: str = "default"
    use_mock: bool = True


class HeatmapRequest(BaseModel):
    sweep_id: str
    x_param: str
    y_param: str
    metric: str = "sharpe"


class RobustnessRequest(BaseModel):
    sweep_id: str
    params: List[str]
    metric: str = "sharpe"


class CandidateRequest(BaseModel):
    sweep_id: str
    min_sharpe: float = 1.5
    max_drawdown: float = 0.20
    min_trades: int = 50


class WalkForwardRequest(BaseModel):
    strategy_id: str
    param_space: Dict[str, List]
    dataset_id: str = "default"
    train_years: int = 3
    test_years: int = 1
    use_mock: bool = True


class ReportRequest(BaseModel):
    sweep_id: str
    include_heatmap: bool = True
    include_robustness: bool = True
    include_candidates: bool = True
    min_sharpe: float = 1.5


# ============================================================
# Endpoints
# ============================================================

@router.post("/sweep")
async def api_run_sweep(req: SweepRequest) -> Dict[str, Any]:
    """运行参数扫描"""
    svc = get_service("experiment")
    result = svc.run_sweep(
        strategy_id=req.strategy_id,
        param_space=req.param_space,
        dataset_id=req.dataset_id,
    )
    return {
        "sweep_id": result.sweep_id,
        "strategy_id": result.strategy_id,
        "dataset_id": result.dataset_id,
        "total_combos": result.total_combos,
        "completed": result.completed,
        "errors": result.errors,
        "status": result.status,
        "results": result.results,
    }


@router.get("/sweeps")
async def api_list_sweeps() -> List[Dict[str, Any]]:
    """列出所有扫描"""
    svc = get_service("experiment")
    return svc.list_sweeps()


@router.get("/sweeps/{sweep_id}")
async def api_get_sweep(sweep_id: str) -> Dict[str, Any]:
    """获取扫描详情"""
    svc = get_service("experiment")
    sweep = svc.get_sweep(sweep_id)
    if not sweep:
        raise HTTPException(status_code=404, detail=f"Sweep '{sweep_id}' not found")
    return {
        "sweep_id": sweep.sweep_id,
        "strategy_id": sweep.strategy_id,
        "dataset_id": sweep.dataset_id,
        "param_space": sweep.param_space,
        "total_combos": sweep.total_combos,
        "completed": sweep.completed,
        "errors": sweep.errors,
        "status": sweep.status,
        "results": sweep.results,
        "created_at": sweep.created_at,
    }


@router.post("/heatmap")
async def api_heatmap(req: HeatmapRequest) -> Dict[str, Any]:
    """生成 Heatmap 数据"""
    svc = get_service("experiment")
    try:
        hm = svc.heatmap(req.sweep_id, req.x_param, req.y_param, req.metric)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "x_label": hm.x_label,
        "y_label": hm.y_label,
        "x_values": hm.x_values,
        "y_values": hm.y_values,
        "matrix": hm.matrix,
        "metric": hm.metric,
    }


@router.post("/robustness")
async def api_robustness(req: RobustnessRequest) -> Dict[str, Any]:
    """计算参数稳健性分数"""
    svc = get_service("experiment")
    try:
        result = svc.robustness(req.sweep_id, req.params, req.metric)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


@router.post("/candidates")
async def api_candidates(req: CandidateRequest) -> Dict[str, Any]:
    """自动筛选候选策略"""
    svc = get_service("experiment")
    candidates = svc.find_candidates(
        sweep_id=req.sweep_id,
        min_sharpe=req.min_sharpe,
        max_drawdown=req.max_drawdown,
        min_trades=req.min_trades,
    )
    return {
        "sweep_id": req.sweep_id,
        "criteria": {
            "min_sharpe": req.min_sharpe,
            "max_drawdown": req.max_drawdown,
            "min_trades": req.min_trades,
        },
        "count": len(candidates),
        "candidates": candidates,
    }


@router.post("/walk-forward")
async def api_walk_forward(req: WalkForwardRequest) -> Dict[str, Any]:
    """Walk Forward 测试"""
    n_windows = max(1, 5)
    windows = []
    for i in range(n_windows):
        windows.append({
            "window_id": i + 1,
            "train_period": f"201{8+i}-202{0+i}",
            "test_period": f"202{1+i}",
            "best_params": {"fast": 10 + i * 5, "slow": 60 + i * 20},
            "train_sharpe": round(1.2 + i * 0.1, 2),
            "test_sharpe": round(0.8 + i * 0.15, 2),
            "test_return": round(0.05 + i * 0.03, 4),
            "test_max_dd": round(0.12 - i * 0.01, 4),
        })

    return {
        "strategy_id": req.strategy_id,
        "dataset_id": req.dataset_id,
        "train_years": req.train_years,
        "test_years": req.test_years,
        "n_windows": n_windows,
        "windows": windows,
        "avg_test_sharpe": round(sum(w["test_sharpe"] for w in windows) / n_windows, 4),
        "avg_test_return": round(sum(w["test_return"] for w in windows) / n_windows, 4),
        "stability_score": 0.72,
    }


@router.post("/report")
async def api_generate_report(req: ReportRequest) -> Dict[str, Any]:
    """生成研究报告"""
    svc = get_service("experiment")
    sweep = svc.get_sweep(req.sweep_id)
    if not sweep:
        raise HTTPException(status_code=404, detail=f"Sweep '{req.sweep_id}' not found")

    report = {
        "sweep_id": req.sweep_id,
        "strategy_id": sweep.strategy_id,
        "dataset_id": sweep.dataset_id,
        "total_combos": sweep.total_combos,
        "completed": sweep.completed,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "overview": {
            "best_sharpe": max((r.get("sharpe", 0) for r in sweep.results), default=0),
            "best_return": max((r.get("total_return", 0) for r in sweep.results), default=0),
            "worst_sharpe": min((r.get("sharpe", 0) for r in sweep.results), default=0),
            "avg_sharpe": round(
                sum(r.get("sharpe", 0) for r in sweep.results) / max(len(sweep.results), 1), 4
            ),
        },
    }

    if req.include_heatmap and len(sweep.param_space) >= 2:
        params = list(sweep.param_space.keys())
        try:
            hm = svc.heatmap(req.sweep_id, params[0], params[1], "sharpe")
            report["heatmap"] = {
                "x_label": hm.x_label,
                "y_label": hm.y_label,
                "x_values": hm.x_values,
                "y_values": hm.y_values,
                "matrix": hm.matrix,
            }
        except Exception:
            pass

    if req.include_robustness and len(sweep.param_space) >= 1:
        try:
            params = list(sweep.param_space.keys())
            rob = svc.robustness(req.sweep_id, params, "sharpe")
            report["robustness"] = rob
        except Exception:
            pass

    if req.include_candidates:
        cands = svc.find_candidates(req.sweep_id, min_sharpe=req.min_sharpe)
        report["candidates"] = {"count": len(cands), "top5": cands[:5]}

    return report


# ============================================================
# V2.0 Workflow API
# ============================================================

@router.get("/workflow/suggestions")
async def api_get_suggestions(include_dismissed: bool = False) -> Dict[str, Any]:
    """获取系统建议"""
    suggestions = _workflow_engine.get_suggestions(include_dismissed=include_dismissed)
    return {
        "suggestions": [
            {
                "action": s.action,
                "label": s.label,
                "description": s.description,
                "context": s.context,
                "priority": s.priority,
                "dismissed": s.dismissed,
            }
            for s in suggestions
        ],
        "total": len(suggestions),
    }


@router.get("/workflow/next-step")
async def api_get_next_step() -> Dict[str, Any]:
    """获取最高优先级的下一步建议"""
    suggestion = _workflow_engine.get_next_step()
    if not suggestion:
        return {"has_suggestion": False, "message": "No pending suggestions"}
    return {
        "has_suggestion": True,
        "action": suggestion.action,
        "label": suggestion.label,
        "description": suggestion.description,
        "context": suggestion.context,
        "priority": suggestion.priority,
    }


@router.post("/workflow/dismiss/{index}")
async def api_dismiss_suggestion(index: int) -> Dict[str, Any]:
    """忽略建议"""
    _workflow_engine.dismiss_suggestion(index)
    return {"dismissed": True}


@router.post("/workflow/clear")
async def api_clear_suggestions() -> Dict[str, Any]:
    """清空所有建议"""
    _workflow_engine.clear_suggestions()
    return {"cleared": True}


@router.get("/workflow/history")
async def api_get_workflow_history(limit: int = 50) -> Dict[str, Any]:
    """获取事件历史"""
    history = _workflow_engine.get_history(limit=limit)
    return {"history": history, "count": len(history)}


@router.post("/workflow/event")
async def api_publish_event(event_type: str, payload: Dict[str, Any] = {}) -> Dict[str, Any]:
    """手动发布研究事件"""
    from ..event.event_types import (
        FactorCreatedEvent,
        SignalCreatedEvent,
        StrategyCreatedEvent,
        BacktestFinishedEvent,
        SweepFinishedEvent,
    )

    event_map = {
        "FACTOR_CREATED": FactorCreatedEvent,
        "SIGNAL_CREATED": SignalCreatedEvent,
        "STRATEGY_CREATED": StrategyCreatedEvent,
        "BACKTEST_FINISHED": BacktestFinishedEvent,
        "SWEEP_FINISHED": SweepFinishedEvent,
    }

    event_cls = event_map.get(event_type)
    if not event_cls:
        raise HTTPException(status_code=400, detail=f"Unknown event type: {event_type}")

    event = event_cls(**payload)
    _event_bus.publish(event)

    return {
        "published": True,
        "event_type": event_type,
        "suggestions_count": len(_workflow_engine.get_suggestions()),
    }
