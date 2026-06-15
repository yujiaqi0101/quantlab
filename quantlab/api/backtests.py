"""
Backtest API — 提交回测

对应前端 Run Backtest 按钮

端点：
  POST /api/v1/backtests   提交回测任务
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..dto.backtest import BacktestRequest
from ..application.backtest_service import BacktestService


router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])


# ---- Pydantic 请求模型 ----
class BacktestSubmitRequest(BaseModel):
    """前端提交回测的请求体"""
    strategy: str = Field(..., description="策略 ID，如 ma_cross")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    dataset: str = Field("default", description="数据集标识")
    symbols: List[str] = Field(default_factory=list, description="标的列表，空则取全部")
    start: Optional[str] = Field(None, description="开始时间")
    end: Optional[str] = Field(None, description="结束时间")
    initial_cash: float = Field(100000.0, description="初始资金")
    commission_bps: float = Field(1.0, description="佣金 bps")
    slippage_bps: float = Field(1.0, description="滑点 bps")
    engine: str = Field("bar", description="引擎类型: bar / vectorbt / auto")
    top_n: int = Field(1, description="组合构造选 N")
    save_experiment: bool = Field(True, description="是否落库 Experiment")
    experiment_name: Optional[str] = Field(None, description="自定义实验名")
    dataset_version: Optional[str] = Field(None, description="数据集版本（V4.3，保证可复现）")


# ---- 全局 BacktestService ----
_service: Optional[BacktestService] = None


def _get_service() -> BacktestService:
    global _service
    if _service is None:
        _service = BacktestService()
    return _service


@router.post("")
async def api_run_backtest(req: BacktestSubmitRequest) -> Dict[str, Any]:
    """
    提交回测任务

    返回 task_id，前端可轮询 /tasks/{id} 或通过 WebSocket 监听进度
    """
    service = _get_service()

    backtest_req = BacktestRequest(
        strategy_id=req.strategy,
        parameters=req.parameters,
        dataset=req.dataset,
        symbols=req.symbols,
        start=req.start,
        end=req.end,
        initial_cash=req.initial_cash,
        commission_bps=req.commission_bps,
        slippage_bps=req.slippage_bps,
        engine=req.engine,
        top_n=req.top_n,
        save_experiment=req.save_experiment,
        experiment_name=req.experiment_name,
        dataset_version=req.dataset_version,
    )

    resp = service.run_backtest(backtest_req)
    return resp.to_dict()
