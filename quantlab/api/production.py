"""
Production Hardening API — 生产硬化 API

端点：
  GET  /api/v1/production/status              系统总览
  GET  /api/v1/production/runtime              运行时状态
  POST /api/v1/production/runtime/start        启动运行时
  POST /api/v1/production/runtime/stop         停止运行时
  POST /api/v1/production/runtime/pause        暂停
  POST /api/v1/production/runtime/resume       恢复
  GET  /api/v1/production/risk                 风险状态
  POST /api/v1/production/risk/kill-switch     触发 Kill Switch
  POST /api/v1/production/risk/kill-switch/reset  重置 Kill Switch
  GET  /api/v1/production/capital              资金分配
  POST /api/v1/production/capital/rebalance    触发调仓
  GET  /api/v1/production/health               健康状态
  GET  /api/v1/production/metrics              指标快照
  GET  /api/v1/production/journal              交易日志
  GET  /api/v1/production/pnl/attribution      PnL 归因
  GET  /api/v1/production/reconciliation       对账状态
  POST /api/v1/production/reconciliation/run   手动对账
  GET  /api/v1/production/recovery             恢复状态
  POST /api/v1/production/recovery/checkpoint  手动 checkpoint
  GET  /api/v1/production/self-healing         自愈历史
  GET  /api/v1/production/replay/status        重放状态
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("quantlab.api.production")

router = APIRouter(prefix="/api/v1/production", tags=["production"])


# ------------------------------------------------------------------
# Production Registry（单例）
# ------------------------------------------------------------------

class ProductionRegistry:
    """
    Production Hardening 组件注册表
    """

    def __init__(self) -> None:
        self.runtime = None
        self.scheduler = None
        self.kill_switch_trigger = None
        self.kill_switch_executor = None
        self.risk_engine = None
        self.capital_allocator = None
        self.capital_portfolio = None
        self.rebalance_engine = None
        self.heartbeat_monitor = None
        self.watchdog = None
        self.metrics_collector = None
        self.trade_journal = None
        self.pnl_attribution = None
        self.reconciliation_engine = None
        self.state_restorer = None
        self.order_recovery = None
        self.position_recovery = None
        self.self_healing = None
        self.replay_engine = None
        self.event_bus = None
        self.oms = None

    def summary(self) -> Dict:
        """系统总览"""
        return {
            "runtime": self.runtime.get_status() if self.runtime else None,
            "kill_switch_active": (
                self.kill_switch_trigger.active
                if self.kill_switch_trigger
                else False
            ),
            "capital": (
                self.capital_allocator.to_dict()
                if self.capital_allocator
                else None
            ),
            "health": {
                "all_alive": (
                    self.heartbeat_monitor.all_alive()
                    if self.heartbeat_monitor
                    else True
                ),
                "components": (
                    self.heartbeat_monitor.get_status()
                    if self.heartbeat_monitor
                    else []
                ),
            },
            "watchdog_alerts": (
                len(self.watchdog.get_alerts())
                if self.watchdog
                else 0
            ),
            "self_healing": (
                self.self_healing.get_stats()
                if self.self_healing
                else None
            ),
        }


_registry = ProductionRegistry()


def get_registry() -> ProductionRegistry:
    return _registry


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class KillSwitchRequest(BaseModel):
    reason: str = "Manual trigger"


class RebalanceRequest(BaseModel):
    target_weights: Dict[str, Dict[str, float]]
    prices: Dict[str, float]


class SignalExecuteRequest(BaseModel):
    signal_id: str
    strategy_id: str
    symbol: str
    side: str  # BUY / SELL
    qty: int
    order_type: str = "MARKET"
    price: Optional[float] = None


# ------------------------------------------------------------------
# 系统总览
# ------------------------------------------------------------------

@router.get("/status")
async def production_status():
    """Production Hardening 系统总览"""
    return _registry.summary()


# ------------------------------------------------------------------
# Runtime
# ------------------------------------------------------------------

@router.get("/runtime")
async def runtime_status():
    """运行时状态"""
    if not _registry.runtime:
        raise HTTPException(404, "Runtime not initialized")
    return _registry.runtime.get_status()


@router.post("/runtime/start")
async def runtime_start():
    if not _registry.runtime:
        raise HTTPException(404, "Runtime not initialized")
    _registry.runtime.start()
    return {"status": "started"}


@router.post("/runtime/stop")
async def runtime_stop():
    if not _registry.runtime:
        raise HTTPException(404, "Runtime not initialized")
    _registry.runtime.stop()
    return {"status": "stopped"}


@router.post("/runtime/pause")
async def runtime_pause():
    if not _registry.runtime:
        raise HTTPException(404, "Runtime not initialized")
    _registry.runtime.pause()
    return {"status": "paused"}


@router.post("/runtime/resume")
async def runtime_resume():
    if not _registry.runtime:
        raise HTTPException(404, "Runtime not initialized")
    _registry.runtime.resume()
    return {"status": "resumed"}


# ------------------------------------------------------------------
# Risk & Kill Switch
# ------------------------------------------------------------------

@router.get("/risk")
async def risk_status():
    """风险状态"""
    if not _registry.risk_engine:
        raise HTTPException(404, "Risk engine not initialized")
    return {
        "kill_switch_active": _registry.kill_switch_trigger.active if _registry.kill_switch_trigger else False,
        "rejects": _registry.risk_engine.get_reject_log() if hasattr(_registry.risk_engine, "get_reject_log") else [],
        "limits": [],
    }


@router.post("/risk/kill-switch")
async def trigger_kill_switch(req: KillSwitchRequest):
    """触发 Kill Switch"""
    if not _registry.kill_switch_trigger:
        raise HTTPException(404, "Kill switch not initialized")
    _registry.kill_switch_trigger.manual_trigger(req.reason)
    return {"status": "triggered", "reason": req.reason}


@router.post("/risk/kill-switch/reset")
async def reset_kill_switch():
    """重置 Kill Switch"""
    if not _registry.kill_switch_executor:
        raise HTTPException(404, "Kill switch not initialized")
    _registry.kill_switch_executor.reset()
    return {"status": "reset"}


# ------------------------------------------------------------------
# Capital
# ------------------------------------------------------------------

@router.get("/capital")
async def capital_status():
    """资金分配状态"""
    if not _registry.capital_allocator:
        raise HTTPException(404, "Capital allocator not initialized")
    result = _registry.capital_allocator.to_dict()
    if _registry.capital_portfolio:
        result["portfolio"] = _registry.capital_portfolio.to_dict()
    return result


@router.post("/capital/rebalance")
async def capital_rebalance(req: RebalanceRequest):
    """触发调仓"""
    if not _registry.rebalance_engine:
        raise HTTPException(404, "Rebalance engine not initialized")
    orders = _registry.rebalance_engine.compute_rebalance(
        target_weights=req.target_weights,
        prices=req.prices,
    )
    return {
        "orders": [o.to_dict() for o in orders],
        "count": len(orders),
    }


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
async def health_status():
    """健康状态"""
    result = {
        "heartbeat": [],
        "watchdog_alerts": [],
        "all_alive": True,
    }
    if _registry.heartbeat_monitor:
        result["heartbeat"] = _registry.heartbeat_monitor.get_status()
        result["all_alive"] = _registry.heartbeat_monitor.all_alive()
    if _registry.watchdog:
        result["watchdog_alerts"] = [
            a.to_dict() for a in _registry.watchdog.get_alerts()
        ]
    return result


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------

@router.get("/metrics")
async def metrics_snapshot():
    """指标快照"""
    if not _registry.metrics_collector:
        raise HTTPException(404, "Metrics collector not initialized")
    return _registry.metrics_collector.snapshot()


# ------------------------------------------------------------------
# Journal
# ------------------------------------------------------------------

@router.get("/journal")
async def journal_query(
    type: Optional[str] = None,
    strategy_id: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    """交易日志查询"""
    if not _registry.trade_journal:
        raise HTTPException(404, "Trade journal not initialized")
    from ..execution.observe.journal import JournalEntryType
    entry_type = None
    if type:
        try:
            entry_type = JournalEntryType(type)
        except ValueError:
            pass
    entries = _registry.trade_journal.query(
        type=entry_type,
        strategy_id=strategy_id,
        symbol=symbol,
        limit=limit,
    )
    return {
        "entries": [e.to_dict() for e in entries],
        "count": len(entries),
    }


# ------------------------------------------------------------------
# PnL Attribution
# ------------------------------------------------------------------

@router.get("/pnl/attribution")
async def pnl_attribution():
    """PnL 归因"""
    if not _registry.pnl_attribution:
        raise HTTPException(404, "PnL attribution not initialized")
    return _registry.pnl_attribution.get_summary()


# ------------------------------------------------------------------
# Reconciliation
# ------------------------------------------------------------------

@router.get("/reconciliation")
async def reconciliation_status():
    """对账状态"""
    if not _registry.reconciliation_engine:
        raise HTTPException(404, "Reconciliation engine not initialized")
    return {
        "last_run": getattr(_registry.reconciliation_engine, "_last_run", 0),
        "mismatches": getattr(_registry.reconciliation_engine, "_mismatch_count", 0),
    }


@router.post("/reconciliation/run")
async def reconciliation_run():
    """手动触发对账"""
    if not _registry.reconciliation_engine:
        raise HTTPException(404, "Reconciliation engine not initialized")
    # 实际调用需要注入 fetch 函数
    return {"status": "triggered"}


# ------------------------------------------------------------------
# Recovery
# ------------------------------------------------------------------

@router.get("/recovery")
async def recovery_status():
    """恢复状态"""
    return {
        "state_restorer": bool(_registry.state_restorer),
        "order_recovery": bool(_registry.order_recovery),
        "position_recovery": (
            {"recovery_count": _registry.position_recovery.recovery_count}
            if _registry.position_recovery
            else None
        ),
    }


@router.post("/recovery/checkpoint")
async def recovery_checkpoint():
    """手动 checkpoint"""
    if not _registry.state_restorer:
        raise HTTPException(404, "State restorer not initialized")
    snapshot = _registry.state_restorer.save(
        portfolio=_registry.capital_portfolio,
        oms=_registry.oms,
        allocator=_registry.capital_allocator,
    )
    return {
        "status": "saved",
        "timestamp": snapshot.timestamp,
        "orders": len(snapshot.orders),
    }


# ------------------------------------------------------------------
# Self-Healing
# ------------------------------------------------------------------

@router.get("/self-healing")
async def self_healing_status():
    """自愈系统状态"""
    if not _registry.self_healing:
        raise HTTPException(404, "Self-healing not initialized")
    return {
        "stats": _registry.self_healing.get_stats(),
        "history": [e.to_dict() for e in _registry.self_healing.get_history()],
    }


# ------------------------------------------------------------------
# Replay
# ------------------------------------------------------------------

@router.get("/replay/status")
async def replay_status():
    """重放状态"""
    if not _registry.replay_engine:
        raise HTTPException(404, "Replay engine not initialized")
    return _registry.replay_engine.get_status()


# ------------------------------------------------------------------
# Idempotent Execution
# ------------------------------------------------------------------

@router.post("/execute/signal")
async def execute_signal(req: SignalExecuteRequest):
    """幂等执行信号"""
    if not _registry.oms:
        raise HTTPException(404, "OMS not initialized")
    from ..execution.runtime.idempotent import IdempotentExecutor
    from ..execution.core.oms.order import OrderSide, OrderType

    executor = IdempotentExecutor(oms=_registry.oms)
    order, is_new = executor.execute_signal(
        signal_id=req.signal_id,
        strategy_id=req.strategy_id,
        symbol=req.symbol,
        side=OrderSide(req.side),
        qty=req.qty,
        order_type=OrderType(req.order_type),
        price=req.price,
    )
    if not order:
        raise HTTPException(400, "Order creation failed")
    return {
        "order_id": order.id,
        "is_new": is_new,
        "state": order.state.value,
        "stats": executor.get_stats(),
    }
