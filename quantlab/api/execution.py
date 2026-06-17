"""
Execution API — Live Studio 执行系统 API

Live Studio 的后端支撑，覆盖：
  - Accounts       账户
  - Portfolio      组合
  - Orders         订单
  - Positions      持仓
  - Risk           风险
  - Monitoring     监控
  - Candidates     候选提升工作流

端点：
  GET  /api/v1/execution/accounts                 账户列表
  GET  /api/v1/execution/accounts/{id}            账户详情
  GET  /api/v1/execution/portfolio                当前组合
  GET  /api/v1/execution/positions                持仓列表
  GET  /api/v1/execution/orders                   订单列表
  POST /api/v1/execution/orders                   手动下单
  DELETE /api/v1/execution/orders/{id}            撤单
  GET  /api/v1/execution/risk/status              风险状态
  GET  /api/v1/execution/risk/rejects             拒单记录
  GET  /api/v1/execution/monitoring/dashboard     监控面板
  GET  /api/v1/execution/candidates               候选列表
  POST /api/v1/execution/candidates/{id}/paper    启动 Paper Trading
  POST /api/v1/execution/candidates/{id}/live     部署到实盘
  GET  /api/v1/execution/pipeline                 提升流水线状态
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("quantlab.api.execution")

router = APIRouter(prefix="/api/v1/execution", tags=["execution"])


# ------------------------------------------------------------------
# 全局 Execution Registry（单例）
# ------------------------------------------------------------------

class ExecutionRegistry:
    """
    执行系统注册表

    管理多个账户 / 引擎 / 候选工作流
    """

    def __init__(self) -> None:
        self.accounts: Dict[str, Any] = {}  # account_id → broker
        self.engines: Dict[str, Any] = {}   # account_id → LiveEngine
        self.workflow: Optional[Any] = None  # PromotionWorkflow

    def register_account(
        self,
        account_id: str,
        broker: Any,
        engine: Optional[Any] = None,
    ) -> None:
        self.accounts[account_id] = broker
        if engine:
            self.engines[account_id] = engine

    def set_workflow(self, workflow: Any) -> None:
        self.workflow = workflow

    def get_broker(self, account_id: str) -> Any:
        if account_id not in self.accounts:
            raise KeyError(f"account not found: {account_id}")
        return self.accounts[account_id]

    def get_engine(self, account_id: str) -> Any:
        return self.engines.get(account_id)


_registry = ExecutionRegistry()


def get_execution_registry() -> ExecutionRegistry:
    return _registry


# ------------------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------------------

class OrderRequest(BaseModel):
    """下单请求"""
    account_id: str
    symbol: str
    quantity: int
    price: Optional[float] = None
    order_type: str = "MARKET"
    client_order_id: Optional[str] = None


class CancelOrderRequest(BaseModel):
    account_id: str
    order_id: str


class StartPaperRequest(BaseModel):
    """启动 Paper Trading"""
    duration_days: int = 7
    strategy_config: Optional[Dict[str, Any]] = None


class DeployLiveRequest(BaseModel):
    """部署到实盘"""
    account_id: str
    portfolio_id: Optional[str] = None


# ------------------------------------------------------------------
# Accounts
# ------------------------------------------------------------------

@router.get("/accounts")
async def list_accounts():
    """账户列表"""
    registry = get_execution_registry()
    accounts = []
    for acc_id, broker in registry.accounts.items():
        try:
            state = broker.get_account()
            accounts.append({
                "account_id": acc_id,
                "broker": getattr(broker, "name", "UNKNOWN"),
                "cash": state.cash,
                "equity": state.equity,
                "margin_used": state.margin_used,
                "buying_power": state.buying_power,
                "connected": getattr(broker, "_connected", False),
            })
        except Exception as e:
            accounts.append({
                "account_id": acc_id,
                "error": str(e),
            })
    return {"accounts": accounts, "total": len(accounts)}


@router.get("/accounts/{account_id}")
async def get_account(account_id: str):
    """账户详情"""
    registry = get_execution_registry()
    try:
        broker = registry.get_broker(account_id)
    except KeyError:
        raise HTTPException(404, f"account not found: {account_id}")

    state = broker.get_account()
    return {
        "account_id": account_id,
        "broker": getattr(broker, "name", "UNKNOWN"),
        "cash": state.cash,
        "equity": state.equity,
        "margin_used": state.margin_used,
        "buying_power": state.buying_power,
        "connected": getattr(broker, "_connected", False),
    }


# ------------------------------------------------------------------
# Portfolio & Positions
# ------------------------------------------------------------------

@router.get("/portfolio")
async def get_portfolio(account_id: str = Query(..., description="账户 ID")):
    """当前组合"""
    registry = get_execution_registry()
    try:
        broker = registry.get_broker(account_id)
    except KeyError:
        raise HTTPException(404, f"account not found: {account_id}")

    state = broker.get_account()
    positions = broker.get_positions()

    return {
        "account_id": account_id,
        "cash": state.cash,
        "equity": state.equity,
        "margin_used": state.margin_used,
        "buying_power": state.buying_power,
        "n_positions": len(positions),
        "gross_exposure": sum(abs(q) for q in positions.values()),
    }


@router.get("/positions")
async def get_positions(account_id: str = Query(..., description="账户 ID")):
    """持仓列表"""
    registry = get_execution_registry()
    try:
        broker = registry.get_broker(account_id)
    except KeyError:
        raise HTTPException(404, f"account not found: {account_id}")

    positions = broker.get_positions()
    last_prices = getattr(broker, "_last_prices", {})

    rows = []
    for sym, qty in positions.items():
        price = last_prices.get(sym, 0.0)
        market_value = qty * price
        rows.append({
            "symbol": sym,
            "quantity": qty,
            "last_price": price,
            "market_value": market_value,
            "side": "LONG" if qty > 0 else "SHORT" if qty < 0 else "FLAT",
        })

    return {
        "positions": rows,
        "total": len(rows),
        "account_id": account_id,
    }


# ------------------------------------------------------------------
# Orders
# ------------------------------------------------------------------

@router.get("/orders")
async def list_orders(
    account_id: str = Query(..., description="账户 ID"),
    status: Optional[str] = Query(None, description="按状态过滤"),
):
    """订单列表"""
    registry = get_execution_registry()
    engine = registry.get_engine(account_id)

    if engine is None or not hasattr(engine, "order_manager"):
        return {"orders": [], "total": 0, "account_id": account_id}

    om = engine.order_manager
    orders = om.all()

    if status:
        orders = [o for o in orders if o.state.value == status]

    rows = []
    for mo in orders:
        rows.append({
            "local_id": mo.order.id,
            "broker_id": mo.broker_id,
            "symbol": mo.order.symbol,
            "quantity": mo.order.quantity,
            "side": mo.order.side,
            "price": mo.order.price,
            "order_type": mo.order.order_type,
            "status": mo.state.value,
            "filled_qty": mo.filled_qty,
            "reject_reason": mo.reject_reason,
            "created_at": mo.created_at.isoformat() if mo.created_at else None,
            "updated_at": mo.updated_at.isoformat() if mo.updated_at else None,
        })

    return {"orders": rows, "total": len(rows), "account_id": account_id}


@router.post("/orders")
async def submit_order(req: OrderRequest):
    """手动下单"""
    registry = get_execution_registry()
    try:
        broker = registry.get_broker(req.account_id)
    except KeyError:
        raise HTTPException(404, f"account not found: {req.account_id}")

    from ..core.order import Order

    order = Order(
        symbol=req.symbol,
        quantity=req.quantity,
        price=req.price,
        order_type=req.order_type,
        client_order_id=req.client_order_id or "",
    )

    # 风险检查
    engine = registry.get_engine(req.account_id)
    if engine is not None and hasattr(engine, "risk_manager"):
        ctx = {
            "positions": broker.get_positions(),
            "equity": broker.get_account().equity,
            "gross_position_value": sum(
                abs(q) * getattr(broker, "_last_prices", {}).get(s, 0.0)
                for s, q in broker.get_positions().items()
            ),
        }
        if not engine.risk_manager.check(order, ctx):
            raise HTTPException(
                400,
                f"order rejected by risk manager: {engine.risk_manager.rejects[-1]}",
            )

    # 下单
    try:
        broker_id = broker.submit_order(order)
    except Exception as e:
        raise HTTPException(500, f"submit_order failed: {e}")

    return {
        "status": "submitted",
        "broker_id": broker_id,
        "client_order_id": order.client_order_id,
        "order": {
            "symbol": order.symbol,
            "quantity": order.quantity,
            "side": order.side,
            "price": order.price,
            "order_type": order.order_type,
        },
    }


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    account_id: str = Query(..., description="账户 ID"),
):
    """撤单"""
    registry = get_execution_registry()
    engine = registry.get_engine(account_id)

    if engine is None or not hasattr(engine, "order_manager"):
        raise HTTPException(404, "order manager not available")

    ok = engine.order_manager.cancel(order_id)
    if not ok:
        raise HTTPException(400, f"cancel failed for order {order_id}")

    return {"status": "cancelled", "order_id": order_id}


# ------------------------------------------------------------------
# Risk
# ------------------------------------------------------------------

@router.get("/risk/status")
async def risk_status(account_id: str = Query(..., description="账户 ID")):
    """风险状态"""
    registry = get_execution_registry()
    engine = registry.get_engine(account_id)

    if engine is None or not hasattr(engine, "risk_manager"):
        return {"account_id": account_id, "checks": [], "n_rejects": 0}

    rm = engine.risk_manager
    checks = [{"name": c.name} for c in rm.checks]

    # kill switch 状态
    kill_switch_active = False
    if hasattr(engine, "emergency_stop"):
        kill_switch_active = engine.emergency_stop.stop

    return {
        "account_id": account_id,
        "checks": checks,
        "n_rejects": len(rm.rejects),
        "kill_switch_active": kill_switch_active,
    }


@router.get("/risk/rejects")
async def risk_rejects(
    account_id: str = Query(..., description="账户 ID"),
    limit: int = Query(50, description="返回条数"),
):
    """拒单记录"""
    registry = get_execution_registry()
    engine = registry.get_engine(account_id)

    if engine is None or not hasattr(engine, "risk_manager"):
        return {"rejects": [], "total": 0}

    rm = engine.risk_manager
    rejects = rm.rejects[-limit:]

    rows = []
    for r in rejects:
        order = r.get("order")
        rows.append({
            "check": r.get("check", ""),
            "symbol": getattr(order, "symbol", "") if order else "",
            "quantity": getattr(order, "quantity", 0) if order else 0,
            "context": str(r.get("context", {}))[:200],
        })

    return {"rejects": rows, "total": len(rm.rejects)}


# ------------------------------------------------------------------
# Monitoring
# ------------------------------------------------------------------

@router.get("/monitoring/dashboard")
async def monitoring_dashboard(
    account_id: str = Query(..., description="账户 ID"),
):
    """监控面板"""
    registry = get_execution_registry()
    engine = registry.get_engine(account_id)

    if engine is None:
        return {"account_id": account_id, "error": "engine not found"}

    # 收集指标
    equity_curve = getattr(engine, "equity_curve", [])
    equity_ts = getattr(engine, "equity_ts", [])

    # 计算基本指标
    initial_cash = getattr(engine, "initial_cash", 100000.0)
    current_equity = equity_curve[-1] if equity_curve else initial_cash
    total_return = (current_equity - initial_cash) / initial_cash if initial_cash > 0 else 0

    # max drawdown
    max_dd = 0.0
    if equity_curve:
        peak = equity_curve[0]
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

    # 订单统计
    n_orders = 0
    n_rejects = 0
    if hasattr(engine, "order_manager"):
        n_orders = len(engine.order_manager)
    if hasattr(engine, "risk_manager"):
        n_rejects = len(engine.risk_manager.rejects)

    return {
        "account_id": account_id,
        "current_equity": current_equity,
        "initial_cash": initial_cash,
        "total_return": total_return,
        "max_drawdown": max_dd,
        "n_data_points": len(equity_curve),
        "n_orders": n_orders,
        "n_rejects": n_rejects,
        "kill_switch_active": (
            engine.emergency_stop.stop
            if hasattr(engine, "emergency_stop") else False
        ),
        "equity_curve_sample": equity_curve[-100:] if equity_curve else [],
        "timestamps_sample": [
            str(t) for t in equity_ts[-100:]
        ] if equity_ts else [],
    }


# ------------------------------------------------------------------
# Candidates / Promotion Workflow
# ------------------------------------------------------------------

@router.get("/candidates")
async def list_candidates(
    status: Optional[str] = Query(None, description="按状态过滤"),
    project_id: Optional[str] = Query(None, description="按项目过滤"),
):
    """候选列表"""
    registry = get_execution_registry()
    if registry.workflow is None:
        return {"candidates": [], "total": 0}

    cm = registry.workflow.cm
    from ..research.projects.candidate import CandidateStatus

    status_enum = CandidateStatus(status) if status else None
    cands = cm.list(status=status_enum, project_id=project_id)

    rows = [c.to_dict() for c in cands]
    return {"candidates": rows, "total": len(rows)}


@router.post("/candidates/{candidate_id}/paper")
async def start_paper_trading(
    candidate_id: str,
    req: StartPaperRequest,
):
    """启动 Paper Trading"""
    registry = get_execution_registry()
    if registry.workflow is None:
        raise HTTPException(503, "promotion workflow not configured")

    try:
        result = registry.workflow.start_paper_trading(
            candidate_id=candidate_id,
            duration_days=req.duration_days,
        )
        return {
            "status": "started",
            "candidate_id": candidate_id,
            "started_at": result.started_at,
            "duration_days": result.duration_days,
        }
    except KeyError:
        raise HTTPException(404, f"candidate not found: {candidate_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/candidates/{candidate_id}/live")
async def deploy_to_live(
    candidate_id: str,
    req: DeployLiveRequest,
):
    """部署到实盘"""
    registry = get_execution_registry()
    if registry.workflow is None:
        raise HTTPException(503, "promotion workflow not configured")

    try:
        cand = registry.workflow.deploy_to_live(
            candidate_id=candidate_id,
            account_id=req.account_id,
            portfolio_id=req.portfolio_id or "",
        )
        return {
            "status": "deployed",
            "candidate_id": candidate_id,
            "portfolio_id": cand.portfolio_id,
            "account_id": req.account_id,
        }
    except KeyError:
        raise HTTPException(404, f"candidate not found: {candidate_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/pipeline")
async def pipeline_status():
    """提升流水线状态"""
    registry = get_execution_registry()
    if registry.workflow is None:
        return {"workflow": "not_configured"}

    return registry.workflow.get_pipeline_status()


@router.get("/pipeline/paper-results")
async def paper_results():
    """Paper Trading 结果列表"""
    registry = get_execution_registry()
    if registry.workflow is None:
        return {"results": [], "total": 0}

    results = registry.workflow.list_paper_results()
    return {"results": results, "total": len(results)}
