"""
Trading Studio API
==================

前缀：/api/v1/trading

统一交易工作室的 REST API，对接 TradingCore + Persistence + ReplayEngine。
支持 Paper / Live / Replay 三种模式。

端点分组：
    - 会话管理：/sessions
    - 数据查询：/sessions/{sid}/<workspace>
    - 操作：/sessions/{sid}/order | cancel | kill-switch
    - Replay：/sessions/{sid}/replay/*
    - 策略库：/strategies
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .trading_service import get_trading_service

logger = logging.getLogger("quantlab.api.trading")

router = APIRouter(prefix="/api/v1/trading", tags=["Trading Studio"])


# ----------------------------------------------------------------------
# 请求模型
# ----------------------------------------------------------------------
class CreateSessionRequest(BaseModel):
    mode: str = Field("paper", description="paper / live / replay")
    strategy_id: str = Field("", description="关联策略ID（可选）")
    strategy_name: str = Field("", description="策略显示名")
    initial_capital: float = Field(1_000_000, description="初始资金")
    symbols: List[str] = Field(default_factory=list, description="交易标的列表")


class ManualOrderRequest(BaseModel):
    symbol: str
    side: str = Field(..., description="buy / sell")
    quantity: float
    order_type: str = Field("market", description="market / limit")
    price: Optional[float] = Field(None, description="限价单价格或市价参考价")
    reason: str = ""


class RestoreReplayRequest(BaseModel):
    time: str = Field(..., description="ISO 时间字符串")


# ----------------------------------------------------------------------
# 会话管理
# ----------------------------------------------------------------------
@router.get("/sessions")
async def list_sessions(
    mode: Optional[str] = Query(None, description="按 mode 过滤"),
    include_stopped: bool = Query(True, description="是否包含已停止会话"),
):
    """列出所有交易会话。"""
    svc = get_trading_service()
    return {"sessions": svc.list_sessions(mode=mode, include_stopped=include_stopped)}


@router.post("/sessions")
async def create_session(req: CreateSessionRequest):
    """创建新交易会话。"""
    svc = get_trading_service()
    try:
        return svc.create_session(
            mode=req.mode,
            strategy_id=req.strategy_id,
            strategy_name=req.strategy_name,
            initial_capital=req.initial_capital,
            symbols=req.symbols,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions/{sid}")
async def get_session(sid: str):
    """获取会话详情。"""
    svc = get_trading_service()
    status = svc.get_session_status(sid)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"session not found: {sid}")
    return status


@router.delete("/sessions/{sid}")
async def delete_session(sid: str):
    """删除会话（停止 + 清理）。"""
    svc = get_trading_service()
    svc.delete_session(sid)
    return {"sid": sid, "deleted": True}


@router.post("/sessions/{sid}/start")
async def start_session(sid: str):
    svc = get_trading_service()
    try:
        return svc.start_session(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{sid}/pause")
async def pause_session(sid: str):
    svc = get_trading_service()
    try:
        return svc.pause_session(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{sid}/resume")
async def resume_session(sid: str):
    svc = get_trading_service()
    try:
        return svc.resume_session(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/sessions/{sid}/stop")
async def stop_session(sid: str):
    svc = get_trading_service()
    try:
        return svc.stop_session(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{sid}/status")
async def get_session_status(sid: str):
    svc = get_trading_service()
    status = svc.get_session_status(sid)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail=f"session not found: {sid}")
    return status


# ----------------------------------------------------------------------
# 数据查询（9 个 Workspace）
# ----------------------------------------------------------------------
@router.get("/sessions/{sid}/overview")
async def get_overview(sid: str):
    """Overview Workspace。"""
    svc = get_trading_service()
    try:
        return svc.get_overview(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{sid}/market")
async def get_market(
    sid: str,
    symbols: Optional[str] = Query(None, description="逗号分隔的标的列表"),
):
    """Market Workspace。"""
    svc = get_trading_service()
    sym_list = symbols.split(",") if symbols else None
    return svc.get_market(sid, symbols=sym_list)


@router.get("/sessions/{sid}/signals")
async def get_signals(sid: str, limit: int = Query(100, le=1000)):
    """Signals Workspace。"""
    svc = get_trading_service()
    return {"signals": svc.get_signals(sid, limit=limit)}


@router.get("/sessions/{sid}/orders")
async def get_orders(
    sid: str,
    status: Optional[str] = Query(None, description="按状态过滤"),
    limit: int = Query(200, le=1000),
):
    """Orders Workspace。"""
    svc = get_trading_service()
    return {"orders": svc.get_orders(sid, status=status, limit=limit)}


@router.get("/sessions/{sid}/positions")
async def get_positions(sid: str):
    """Positions Workspace。"""
    svc = get_trading_service()
    return {"positions": svc.get_positions(sid)}


@router.get("/sessions/{sid}/portfolio")
async def get_portfolio(sid: str):
    """Portfolio Workspace。"""
    svc = get_trading_service()
    return svc.get_portfolio(sid)


@router.get("/sessions/{sid}/risk")
async def get_risk(sid: str):
    """Risk Workspace。"""
    svc = get_trading_service()
    return svc.get_risk(sid)


@router.get("/sessions/{sid}/journal")
async def get_journal(sid: str, limit: int = Query(100, le=1000)):
    """Journal Workspace。"""
    svc = get_trading_service()
    return {"journal": svc.get_journal(sid, limit=limit)}


@router.get("/sessions/{sid}/equity-curve")
async def get_equity_curve(sid: str, points: int = Query(500, le=10000)):
    """Equity Curve 数据。"""
    svc = get_trading_service()
    return {"curve": svc.get_equity_curve(sid, points=points)}


# ----------------------------------------------------------------------
# 操作
# ----------------------------------------------------------------------
@router.post("/sessions/{sid}/order")
async def manual_order(sid: str, req: ManualOrderRequest):
    """手动下单。"""
    svc = get_trading_service()
    try:
        return svc.manual_order(
            sid=sid,
            symbol=req.symbol,
            side=req.side,
            quantity=req.quantity,
            order_type=req.order_type,
            price=req.price,
            reason=req.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/sessions/{sid}/cancel/{order_id}")
async def cancel_order(sid: str, order_id: str):
    """撤单。"""
    svc = get_trading_service()
    try:
        return svc.cancel_order(sid, order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{sid}/kill-switch")
async def kill_switch(sid: str):
    """触发 Kill Switch。"""
    svc = get_trading_service()
    try:
        return svc.kill_switch(sid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------------------------
# Replay
# ----------------------------------------------------------------------
@router.get("/sessions/{sid}/replay/timeline")
async def get_replay_timeline(sid: str, limit: int = Query(500, le=5000)):
    """获取 Replay 时间线。"""
    svc = get_trading_service()
    return {"timeline": svc.get_replay_timeline(sid, limit=limit)}


@router.get("/sessions/{sid}/replay/snapshot")
async def get_replay_snapshot(sid: str, time: str = Query(..., description="ISO 时间")):
    """获取指定时间的快照。"""
    svc = get_trading_service()
    return svc.get_replay_snapshot(sid, time)


@router.post("/sessions/{sid}/replay/restore")
async def restore_replay(sid: str, req: RestoreReplayRequest):
    """恢复到指定时间点。"""
    svc = get_trading_service()
    return svc.restore_replay(sid, req.time)


# ----------------------------------------------------------------------
# 策略库
# ----------------------------------------------------------------------
@router.get("/strategies")
async def list_strategies():
    """可用策略列表。"""
    svc = get_trading_service()
    return {"strategies": svc.list_strategies()}


@router.get("/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """策略详情。"""
    svc = get_trading_service()
    s = svc.get_strategy(strategy_id)
    if s is None:
        raise HTTPException(status_code=404, detail=f"strategy not found: {strategy_id}")
    return s
