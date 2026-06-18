"""
Live Studio V1 API — 实时交易工作室

T1 第十模块：Observe Studio 看结果，Live Studio 看运行过程

端点：
  GET  /api/v1/live/status                Live Studio 总览
  GET  /api/v1/live/strategies             策略库
  GET  /api/v1/live/strategies/{id}        策略详情
  POST /api/v1/live/deploy                 部署策略
  POST /api/v1/live/undeploy/{deploy_id}   卸载策略
  GET  /api/v1/live/deployments            部署列表
  GET  /api/v1/live/deployments/{id}/status  部署状态
  GET  /api/v1/live/deployments/{id}/orders    订单
  GET  /api/v1/live/deployments/{id}/positions 持仓
  GET  /api/v1/live/deployments/{id}/portfolio 组合
  GET  /api/v1/live/deployments/{id}/risk       风险
  POST /api/v1/live/deployments/{id}/pause      暂停
  POST /api/v1/live/deployments/{id}/resume     恢复
  POST /api/v1/live/deployments/{id}/order      手动下单
  POST /api/v1/live/deployments/{id}/cancel/{order_id}  撤单
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..execution.deployment import DeploymentManager, DeployRequest, DeployStatus
from ..execution.strategy_registry import get_registry

logger = logging.getLogger("quantlab.api.live")

router = APIRouter(prefix="/api/v1/live", tags=["live"])


# ------------------------------------------------------------------
# 单例
# ------------------------------------------------------------------

_deployment_manager: Optional[DeploymentManager] = None


def get_deployment_manager() -> DeploymentManager:
    global _deployment_manager
    if _deployment_manager is None:
        _deployment_manager = DeploymentManager()
    return _deployment_manager


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class DeployRequestModel(BaseModel):
    strategy_id: str
    symbols: List[str]
    params: Dict = {}
    initial_capital: float = 100000.0
    broker_type: str = "PAPER"
    strategy_name: str = ""


class ManualOrderModel(BaseModel):
    symbol: str
    side: str           # BUY / SELL
    qty: float
    order_type: str = "MARKET"
    price: Optional[float] = None
    strategy_id: str = "manual"


# ------------------------------------------------------------------
# Live Studio 总览
# ------------------------------------------------------------------

@router.get("/status")
async def live_status() -> Dict[str, Any]:
    """Live Studio 总览"""
    mgr = get_deployment_manager()
    reg = get_registry()
    return {
        "deployment_manager": mgr.get_status(),
        "strategy_registry": reg.to_dict(),
    }


# ------------------------------------------------------------------
# 策略库
# ------------------------------------------------------------------

@router.get("/strategies")
async def list_strategies(
    category: str = "",
    tag: str = "",
    enabled_only: bool = False,
) -> Dict[str, Any]:
    """列出所有可用策略"""
    reg = get_registry()
    strategies = reg.list_strategies(
        category=category,
        tag=tag,
        enabled_only=enabled_only,
    )
    return {
        "total": len(strategies),
        "strategies": [s.to_dict() for s in strategies],
        "categories": reg.list_categories(),
        "tags": reg.list_tags(),
    }


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str) -> Dict[str, Any]:
    """获取策略详情"""
    reg = get_registry()
    info = reg.get_strategy(strategy_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")
    return info.to_dict()


# ------------------------------------------------------------------
# 部署
# ------------------------------------------------------------------

@router.post("/deploy")
async def deploy_strategy(req: DeployRequestModel) -> Dict[str, Any]:
    """部署策略"""
    mgr = get_deployment_manager()
    reg = get_registry()

    # 校验策略存在
    if not reg.has(req.strategy_id):
        raise HTTPException(
            status_code=404,
            detail=f"Strategy not found: {req.strategy_id}",
        )

    deploy_req = DeployRequest(
        strategy_id=req.strategy_id,
        symbols=req.symbols,
        params=req.params,
        initial_capital=req.initial_capital,
        broker_type=req.broker_type,
        strategy_name=req.strategy_name,
    )
    result = mgr.deploy(deploy_req)
    return result.to_dict()


@router.post("/undeploy/{deploy_id}")
async def undeploy_strategy(deploy_id: str) -> Dict[str, Any]:
    """卸载策略"""
    mgr = get_deployment_manager()
    success = mgr.undeploy(deploy_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    return {"deploy_id": deploy_id, "undeployed": True}


@router.get("/deployments")
async def list_deployments(status: str = "") -> Dict[str, Any]:
    """列出所有部署"""
    mgr = get_deployment_manager()
    status_filter = DeployStatus(status) if status else None
    records = mgr.list_deployments(status=status_filter)
    return {
        "total": len(records),
        "deployments": [r.to_dict() for r in records],
    }


@router.get("/deployments/{deploy_id}/status")
async def deployment_status(deploy_id: str) -> Dict[str, Any]:
    """部署状态"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    return runtime.get_status()


@router.get("/deployments/{deploy_id}/orders")
async def deployment_orders(
    deploy_id: str,
    active_only: bool = False,
) -> Dict[str, Any]:
    """获取部署的订单"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    orders = runtime.get_orders(active_only=active_only)
    return {"total": len(orders), "orders": orders}


@router.get("/deployments/{deploy_id}/positions")
async def deployment_positions(deploy_id: str) -> Dict[str, Any]:
    """获取部署的持仓"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    positions = runtime.get_positions()
    return {"total": len(positions), "positions": positions}


@router.get("/deployments/{deploy_id}/portfolio")
async def deployment_portfolio(deploy_id: str) -> Dict[str, Any]:
    """获取部署的组合状态"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    return runtime.portfolio_book.to_dict()


@router.get("/deployments/{deploy_id}/risk")
async def deployment_risk(deploy_id: str) -> Dict[str, Any]:
    """获取部署的风险状态"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")

    portfolio = runtime.portfolio_book
    return {
        "equity": portfolio.equity(),
        "exposure": portfolio.exposure(),
        "long_exposure": portfolio.long_exposure(),
        "short_exposure": portfolio.short_exposure(),
        "margin": portfolio.margin(),
        "max_drawdown": portfolio.max_drawdown(),
        "current_drawdown": portfolio.current_drawdown(),
        "n_open_positions": portfolio.n_open_positions(),
        "initial_capital": portfolio.initial_capital,
        "total_pnl": portfolio.total_pnl(),
        "total_return": portfolio.total_return(),
    }


# ------------------------------------------------------------------
# 运行时控制
# ------------------------------------------------------------------

@router.post("/deployments/{deploy_id}/pause")
async def pause_deployment(deploy_id: str) -> Dict[str, Any]:
    """暂停部署"""
    mgr = get_deployment_manager()
    success = mgr.pause(deploy_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    return {"deploy_id": deploy_id, "paused": True}


@router.post("/deployments/{deploy_id}/resume")
async def resume_deployment(deploy_id: str) -> Dict[str, Any]:
    """恢复部署"""
    mgr = get_deployment_manager()
    success = mgr.resume(deploy_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")
    return {"deploy_id": deploy_id, "resumed": True}


# ------------------------------------------------------------------
# 手动交易
# ------------------------------------------------------------------

@router.post("/deployments/{deploy_id}/order")
async def manual_order(
    deploy_id: str,
    req: ManualOrderModel,
) -> Dict[str, Any]:
    """手动下单"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")

    order = runtime.submit_order(
        symbol=req.symbol,
        side=req.side,
        qty=req.qty,
        order_type=req.order_type,
        price=req.price,
        strategy_id=req.strategy_id,
    )
    if not order:
        raise HTTPException(status_code=400, detail="Order submission failed")
    return order.to_dict()


@router.post("/deployments/{deploy_id}/cancel/{order_id}")
async def cancel_order(
    deploy_id: str,
    order_id: str,
) -> Dict[str, Any]:
    """撤单"""
    mgr = get_deployment_manager()
    runtime = mgr.get_runtime(deploy_id)
    if not runtime:
        raise HTTPException(status_code=404, detail=f"Deployment not found: {deploy_id}")

    success = runtime.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cancel failed")
    return {"order_id": order_id, "cancelled": True}
