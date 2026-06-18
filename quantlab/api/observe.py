"""
Observe Studio API — 可观测性后端

Observe Studio 不是看收益，而是理解系统正在发生什么。

端点：
  GET  /api/v1/observe/overview           系统总览（首页）
  GET  /api/v1/observe/positions           持仓列表
  GET  /api/v1/observe/orders              订单列表
  GET  /api/v1/observe/trades              成交列表 + 分析
  GET  /api/v1/observe/risk                风险状态
  GET  /api/v1/observe/health              策略健康
  GET  /api/v1/observe/timeline            事件时间线
  GET  /api/v1/observe/replay/sessions     重放会话列表
  GET  /api/v1/observe/replay/{session_id} 重放单个会话
  GET  /api/v1/observe/journal             交易日志
  GET  /api/v1/observe/journal/stats       日志统计
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("quantlab.api.observe")

router = APIRouter(prefix="/api/v1/observe", tags=["observe"])


# ------------------------------------------------------------------
# Observe Registry — 单例，桥接 Production / Runtime / OMS
# ------------------------------------------------------------------

class ObserveRegistry:
    """
    Observe Studio 组件注册表

    桥接 ProductionRegistry / Runtime / OMS / EventTracer，
    为前端提供统一的只读视图。
    """

    def __init__(self) -> None:
        self.production_registry = None
        self.event_tracer = None
        self.health_monitor = None
        self.trade_analytics = None
        self.execution_analytics = None
        self.drift_detector = None
        self.journal = None
        self.replay_engine = None

    def attach_production(self, prod_registry) -> None:
        self.production_registry = prod_registry

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def overview(self) -> Dict[str, Any]:
        """首页总览"""
        # 尝试从 production registry 获取真实数据
        prod = self._prod_summary()

        # 计算今日/总收益
        today_pnl = 0.0
        total_pnl = 0.0
        equity = 0.0
        cash = 0.0
        max_drawdown = 0.0
        active_strategies = 0
        n_positions = 0

        if prod and prod.get("runtime"):
            rt = prod["runtime"]
            equity = rt.get("equity", 0.0)
            cash = rt.get("cash", 0.0)
            today_pnl = rt.get("today_pnl", 0.0)
            total_pnl = rt.get("total_pnl", 0.0)
            max_drawdown = rt.get("max_drawdown", 0.0)
            active_strategies = rt.get("active_strategies", 0)
            n_positions = rt.get("n_positions", 0)

        return {
            "equity": equity,
            "cash": cash,
            "today_pnl": today_pnl,
            "today_pnl_pct": (today_pnl / equity * 100) if equity > 0 else 0.0,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / (equity - total_pnl) * 100) if (equity - total_pnl) > 0 else 0.0,
            "max_drawdown": max_drawdown,
            "active_strategies": active_strategies,
            "n_positions": n_positions,
            "timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def positions(self) -> List[Dict[str, Any]]:
        """持仓列表"""
        prod = self._prod_summary()
        if prod and prod.get("runtime"):
            return prod["runtime"].get("positions", [])
        return []

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def orders(
        self,
        status: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """订单列表"""
        prod = self._prod_summary()
        if prod and prod.get("runtime"):
            orders = prod["runtime"].get("orders", [])
            # 按时间过滤
            cutoff = datetime.now() - timedelta(hours=hours)
            filtered = []
            for o in orders:
                # 简单过滤：如果有 created_at 字段
                created = o.get("created_at", "")
                if created:
                    try:
                        ct = datetime.fromisoformat(created)
                        if ct < cutoff:
                            continue
                    except Exception:
                        pass
                if status and o.get("status") != status:
                    continue
                filtered.append(o)
            return filtered
        return []

    # ------------------------------------------------------------------
    # Trades + Analytics
    # ------------------------------------------------------------------

    def trades(self, hours: int = 24) -> Dict[str, Any]:
        """成交列表 + 分析"""
        prod = self._prod_summary()
        trades_list = []
        if prod and prod.get("runtime"):
            trades_list = prod["runtime"].get("trades", [])

        # 按时间过滤
        cutoff = datetime.now() - timedelta(hours=hours)
        filtered = []
        for t in trades_list:
            ts = t.get("timestamp", "")
            if ts:
                try:
                    tt = datetime.fromisoformat(ts)
                    if tt < cutoff:
                        continue
                except Exception:
                    pass
            filtered.append(t)

        # 计算分析
        analytics = self._compute_trade_analytics(filtered)

        return {
            "trades": filtered,
            "analytics": analytics,
            "n": len(filtered),
        }

    def _compute_trade_analytics(self, trades: List[Dict]) -> Dict[str, Any]:
        """计算交易分析"""
        if not trades:
            return {
                "n_trades": 0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_pnl": 0.0,
            }

        n = len(trades)
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) < 0]

        total_profit = sum(t["pnl"] for t in wins)
        total_loss = abs(sum(t["pnl"] for t in losses))
        total_pnl = total_profit - total_loss

        return {
            "n_trades": n,
            "n_wins": len(wins),
            "n_losses": len(losses),
            "win_rate": len(wins) / n if n > 0 else 0.0,
            "profit_factor": (total_profit / total_loss) if total_loss > 0 else 0.0,
            "expectancy": total_pnl / n if n > 0 else 0.0,
            "avg_win": (total_profit / len(wins)) if wins else 0.0,
            "avg_loss": (total_loss / len(losses)) if losses else 0.0,
            "total_pnl": total_pnl,
            "largest_win": max((t["pnl"] for t in wins), default=0.0),
            "largest_loss": min((t["pnl"] for t in losses), default=0.0),
        }

    # ------------------------------------------------------------------
    # Risk
    # ------------------------------------------------------------------

    def risk(self) -> Dict[str, Any]:
        """风险状态"""
        prod = self._prod_summary()
        if prod and prod.get("risk"):
            return prod["risk"]

        # 默认风险状态
        return {
            "status": "NORMAL",   # NORMAL / WARNING / CRITICAL
            "max_position_pct": 0.0,
            "daily_loss": 0.0,
            "max_daily_loss": 0.0,
            "max_drawdown": 0.0,
            "kill_switch_active": False,
        }

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> List[Dict[str, Any]]:
        """策略健康状态"""
        if self.health_monitor:
            return [h.to_dict() for h in self.health_monitor.list_health()]
        return []

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def timeline(
        self,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """事件时间线"""
        if self.event_tracer:
            from quantlab.execution.observe.timeline import TimelineView
            view = TimelineView(self.event_tracer)
            entries = view.get_timeline(limit=limit, category=category)
            return [e.to_dict() for e in entries]
        return []

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    def replay_sessions(self) -> List[Dict[str, Any]]:
        """重放会话列表"""
        if self.replay_engine:
            return self.replay_engine.list_sessions()
        return []

    def replay_session(self, session_id: str) -> Dict[str, Any]:
        """单个重放会话"""
        if self.replay_engine:
            session = self.replay_engine.get_session(session_id)
            if session is None:
                raise HTTPException(404, f"session {session_id} not found")
            return session
        return {"session_id": session_id, "events": []}

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------

    def journal_entries(
        self,
        category: Optional[str] = None,
        strategy: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """日志条目"""
        if self.journal:
            entries = self.journal.list_entries(category=category, strategy=strategy)
            return [e.to_dict() if hasattr(e, "to_dict") else e for e in entries[-limit:]]
        return []

    def journal_stats(self) -> Dict[str, Any]:
        """日志统计"""
        if self.journal and hasattr(self.journal, "stats"):
            return self.journal.stats()
        return {"n_entries": 0}

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _prod_summary(self) -> Optional[Dict]:
        """获取 production registry summary"""
        if self.production_registry:
            try:
                return self.production_registry.summary()
            except Exception as e:
                logger.warning(f"production summary failed: {e}")
        return None


_registry = ObserveRegistry()


def get_registry() -> ObserveRegistry:
    return _registry


# ------------------------------------------------------------------
# Pydantic 模型
# ------------------------------------------------------------------

class JournalEntryIn(BaseModel):
    category: str = "observation"
    title: str
    content: str
    strategy: str = ""
    symbol: str = ""
    metadata: Dict[str, Any] = {}


# ------------------------------------------------------------------
# 端点
# ------------------------------------------------------------------

@router.get("/overview")
async def overview() -> Dict[str, Any]:
    """系统总览（首页）"""
    return _registry.overview()


@router.get("/positions")
async def positions() -> List[Dict[str, Any]]:
    """持仓列表"""
    return _registry.positions()


@router.get("/orders")
async def orders(
    status: Optional[str] = None,
    hours: int = Query(24, ge=1, le=720),
) -> List[Dict[str, Any]]:
    """订单列表"""
    return _registry.orders(status=status, hours=hours)


@router.get("/trades")
async def trades(
    hours: int = Query(24, ge=1, le=720),
) -> Dict[str, Any]:
    """成交列表 + 分析"""
    return _registry.trades(hours=hours)


@router.get("/risk")
async def risk() -> Dict[str, Any]:
    """风险状态"""
    return _registry.risk()


@router.get("/health")
async def health() -> List[Dict[str, Any]]:
    """策略健康状态"""
    return _registry.health()


@router.get("/timeline")
async def timeline(
    limit: int = Query(100, ge=1, le=10000),
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """事件时间线"""
    return _registry.timeline(limit=limit, category=category)


@router.get("/replay/sessions")
async def replay_sessions() -> List[Dict[str, Any]]:
    """重放会话列表"""
    return _registry.replay_sessions()


@router.get("/replay/{session_id}")
async def replay_session(session_id: str) -> Dict[str, Any]:
    """单个重放会话"""
    return _registry.replay_session(session_id)


@router.get("/journal")
async def journal(
    category: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """日志条目"""
    entries = _registry.journal_entries(
        category=category, strategy=strategy, limit=limit
    )
    return {"entries": entries, "n": len(entries)}


@router.get("/journal/stats")
async def journal_stats() -> Dict[str, Any]:
    """日志统计"""
    return _registry.journal_stats()


@router.post("/journal")
async def add_journal_entry(entry: JournalEntryIn) -> Dict[str, Any]:
    """新增日志条目"""
    if not _registry.journal:
        raise HTTPException(503, "Journal not available")
    # 根据 category 调用对应方法
    j = _registry.journal
    if entry.category == "reflection":
        result = j.log_reflection(entry.title, entry.content)
    elif entry.category == "open":
        result = j.log_open(entry.symbol, 0, 0, entry.content, entry.strategy)
    elif entry.category == "close":
        result = j.log_close(entry.symbol, 0, 0, 0, entry.content, entry.strategy)
    else:
        result = j.log_observation(entry.title, entry.content, entry.metadata)
    return result.to_dict() if hasattr(result, "to_dict") else result


@router.get("/stats")
async def global_stats() -> Dict[str, Any]:
    """全局统计"""
    return {
        "overview": _registry.overview(),
        "risk": _registry.risk(),
        "health": _registry.health(),
        "timeline_stats": {"available": _registry.event_tracer is not None},
        "journal_stats": _registry.journal_stats(),
    }


# ==================================================================
# Replay V2 — EventStore / Session / Timeline / Controller / RCA
# ==================================================================

from quantlab.execution.observe import (
    EventStore,
    SessionManager,
    TimelineService,
    ReplayController,
    ReplayStatus,
    RootCauseAnalysis,
    get_event_store,
    get_session_manager,
    get_replay_controller,
)
from quantlab.execution.observe.analysis import (
    AnalysisReporter,
    TraceBuilder,
    RootCauseAnalyzer,
    ExplainEngine,
)


# ------------------------------------------------------------------
# EventStore
# ------------------------------------------------------------------

@router.get("/events")
async def query_events(
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    trace_id: Optional[str] = None,
    source: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    limit: int = Query(500, ge=1, le=100000),
    offset: int = Query(0, ge=0),
    order: str = Query("asc", pattern="^(asc|desc)$"),
) -> Dict[str, Any]:
    """查询事件（EventStore）"""
    store = get_event_store()
    events = store.query(
        session_id=session_id,
        event_type=event_type,
        trace_id=trace_id,
        source=source,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        offset=offset,
        order=order,
    )
    return {
        "events": [e.to_dict() for e in events],
        "n": len(events),
        "total": store.count(session_id=session_id, event_type=event_type),
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str) -> Dict[str, Any]:
    """获取单个事件"""
    store = get_event_store()
    event = store.get_event(event_id)
    if not event:
        raise HTTPException(404, f"event {event_id} not found")
    return event.to_dict()


@router.get("/events/stats/summary")
async def event_store_stats() -> Dict[str, Any]:
    """EventStore 统计"""
    store = get_event_store()
    return store.stats()


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(
    strategy: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """会话列表"""
    mgr = get_session_manager()
    sessions = mgr.list_sessions(strategy=strategy, limit=limit)
    return {
        "sessions": [s.to_dict() for s in sessions],
        "n": len(sessions),
    }


@router.get("/sessions/active")
async def list_active_sessions() -> Dict[str, Any]:
    """活跃会话"""
    mgr = get_session_manager()
    sessions = mgr.list_active()
    return {
        "sessions": [s.to_dict() for s in sessions],
        "n": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """获取会话详情"""
    mgr = get_session_manager()
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(404, f"session {session_id} not found")
    return session.to_dict()


@router.post("/sessions")
async def create_session(
    strategy: str = "",
    symbol: str = "",
    meta: Dict[str, Any] = {},
) -> Dict[str, Any]:
    """创建会话"""
    mgr = get_session_manager()
    sid = mgr.start_session(strategy=strategy, symbol=symbol, meta=meta)
    session = mgr.get_session(sid)
    return session.to_dict() if session else {"session_id": sid}


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> Dict[str, Any]:
    """结束会话"""
    mgr = get_session_manager()
    mgr.end_session(session_id)
    return {"session_id": session_id, "ended": True}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """删除会话"""
    store = get_event_store()
    n = store.delete_session(session_id)
    return {"session_id": session_id, "deleted_events": n}


# ------------------------------------------------------------------
# Timeline Service
# ------------------------------------------------------------------

@router.get("/timeline/v2")
async def timeline_v2(
    session_id: Optional[str] = None,
    event_type: Optional[str] = None,
    trace_id: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=100000),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """时间线（V2，基于 EventStore）"""
    svc = TimelineService()
    items = svc.get_timeline(
        session_id=session_id,
        event_type=event_type,
        trace_id=trace_id,
        start_ts=start_ts,
        end_ts=end_ts,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [it.to_dict() for it in items],
        "n": len(items),
    }


@router.get("/timeline/v2/categories")
async def timeline_categories(
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """时间线各类别事件数"""
    svc = TimelineService()
    return svc.get_categories(session_id=session_id)


# ------------------------------------------------------------------
# Replay Controller
# ------------------------------------------------------------------

@router.post("/replay/v2/load/{session_id}")
async def replay_load(session_id: str) -> Dict[str, Any]:
    """加载会话到重放控制器"""
    ctrl = get_replay_controller()
    n = ctrl.load_session(session_id)
    return {"session_id": session_id, "n_events": n}


@router.get("/replay/v2/snapshot")
async def replay_snapshot() -> Dict[str, Any]:
    """获取重放快照"""
    ctrl = get_replay_controller()
    return ctrl.get_snapshot().to_dict()


@router.post("/replay/v2/play")
async def replay_play(speed: float = Query(1.0, ge=0.1, le=1000.0)) -> Dict[str, Any]:
    """开始/继续播放"""
    ctrl = get_replay_controller()
    ctrl.play(speed=speed)
    return ctrl.get_snapshot().to_dict()


@router.post("/replay/v2/pause")
async def replay_pause() -> Dict[str, Any]:
    """暂停"""
    ctrl = get_replay_controller()
    ctrl.pause()
    return ctrl.get_snapshot().to_dict()


@router.post("/replay/v2/resume")
async def replay_resume() -> Dict[str, Any]:
    """恢复"""
    ctrl = get_replay_controller()
    ctrl.resume()
    return ctrl.get_snapshot().to_dict()


@router.post("/replay/v2/stop")
async def replay_stop() -> Dict[str, Any]:
    """停止"""
    ctrl = get_replay_controller()
    ctrl.stop()
    return ctrl.get_snapshot().to_dict()


@router.post("/replay/v2/next")
async def replay_next() -> Dict[str, Any]:
    """下一事件"""
    ctrl = get_replay_controller()
    event = ctrl.next_event()
    snap = ctrl.get_snapshot()
    return {
        **snap.to_dict(),
        "advanced": event is not None,
    }


@router.post("/replay/v2/prev")
async def replay_prev() -> Dict[str, Any]:
    """上一事件"""
    ctrl = get_replay_controller()
    event = ctrl.previous_event()
    snap = ctrl.get_snapshot()
    return {
        **snap.to_dict(),
        "advanced": event is not None,
    }


@router.post("/replay/v2/seek")
async def replay_seek(position: int = Query(0, ge=0)) -> Dict[str, Any]:
    """跳转到指定位置"""
    ctrl = get_replay_controller()
    ctrl.seek(position)
    return ctrl.get_snapshot().to_dict()


@router.get("/replay/v2/events")
async def replay_events(
    start: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """获取当前会话的事件范围"""
    ctrl = get_replay_controller()
    events = ctrl.get_events_range(start=start, limit=limit)
    return {
        "events": [e.to_dict() for e in events],
        "n": len(events),
        "position": ctrl.position,
        "total": ctrl.total_events,
    }


# ------------------------------------------------------------------
# Root Cause Analysis
# ------------------------------------------------------------------

@router.get("/rca/trace/{trace_id}")
async def rca_trace(trace_id: str) -> Dict[str, Any]:
    """按 trace_id 分析交易链路"""
    rca = RootCauseAnalysis()
    chain = rca.analyze_trace(trace_id)
    return chain.to_dict()


@router.get("/rca/event/{event_id}")
async def rca_event(event_id: str) -> Dict[str, Any]:
    """从事件出发分析链路"""
    rca = RootCauseAnalysis()
    chain = rca.analyze_event(event_id)
    return chain.to_dict()


@router.get("/rca/session/{session_id}")
async def rca_session(
    session_id: str,
    symbol: Optional[str] = None,
) -> Dict[str, Any]:
    """会话所有交易链路"""
    rca = RootCauseAnalysis()
    chains = rca.find_traces_for_session(session_id, symbol=symbol)
    return {
        "chains": [c.to_dict() for c in chains],
        "n": len(chains),
    }


@router.get("/rca/session/{session_id}/losses")
async def rca_losses(
    session_id: str,
    top_n: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """会话亏损交易链路"""
    rca = RootCauseAnalysis()
    chains = rca.find_loss_trades(session_id, top_n=top_n)
    return {
        "chains": [c.to_dict() for c in chains],
        "n": len(chains),
    }


@router.get("/rca/session/{session_id}/anomalies")
async def rca_anomalies(session_id: str) -> Dict[str, Any]:
    """会话异常检测"""
    rca = RootCauseAnalysis()
    return rca.find_anomalies(session_id)


# ==================================================================
# Analysis V3 — Root Cause Analysis（根因分析）
#
#   TradeTrace        — 交易链路（入场/出场/滑点/PnL）
#   RootCauseAnalyzer — 根因分析（5 种原因类型）
#   ExplainEngine     — 解释引擎（自然语言）
#   AnalysisReporter  — 报告 + 异常检测
# ==================================================================

def get_reporter() -> AnalysisReporter:
    """获取分析报告生成器"""
    return AnalysisReporter(get_event_store())


@router.get("/analysis/trace/{trace_id}")
async def analysis_trace(trace_id: str) -> Dict[str, Any]:
    """分析单笔交易（按 trace_id）— 返回 TradeTrace + 根因 + 解释"""
    reporter = get_reporter()
    report = reporter.analyze_trace(trace_id)
    return report.to_dict()


@router.get("/analysis/event/{event_id}")
async def analysis_event(event_id: str) -> Dict[str, Any]:
    """分析单笔交易（按事件 ID）"""
    reporter = get_reporter()
    report = reporter.analyze_event(event_id)
    return report.to_dict()


@router.get("/analysis/session/{session_id}")
async def analysis_session(
    session_id: str,
    only_closed: bool = Query(False, description="只返回已平仓的交易"),
    only_losses: bool = Query(False, description="只返回亏损交易"),
    top_n: int = Query(50, ge=1, le=500),
) -> Dict[str, Any]:
    """分析会话所有交易"""
    reporter = get_reporter()

    if only_losses:
        reports = reporter.analyze_losses(session_id, top_n=top_n)
    else:
        reports = reporter.analyze_session(session_id)

    if only_closed:
        reports = [r for r in reports if r.trace.is_closed]

    return {
        "session_id": session_id,
        "n": len(reports),
        "reports": [r.to_dict() for r in reports],
    }


@router.get("/analysis/session/{session_id}/losses")
async def analysis_losses(
    session_id: str,
    top_n: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """分析会话亏损交易（按亏损金额排序）"""
    reporter = get_reporter()
    reports = reporter.analyze_losses(session_id, top_n=top_n)
    return {
        "session_id": session_id,
        "n": len(reports),
        "reports": [r.to_dict() for r in reports],
    }


@router.get("/analysis/session/{session_id}/anomalies")
async def analysis_anomalies(
    session_id: str,
    consecutive_losses: int = Query(3, ge=2, le=20),
    slippage_bps: float = Query(50.0, ge=1.0, le=1000.0),
    no_signal_hours: float = Query(24.0, ge=1.0, le=720.0),
) -> Dict[str, Any]:
    """会话异常检测（连续亏损 / 滑点异常 / 无信号 / 成交无信号 / 订单未成交）"""
    reporter = get_reporter()
    report = reporter.detect_anomalies(
        session_id=session_id,
        consecutive_losses_threshold=consecutive_losses,
        slippage_threshold_bps=slippage_bps,
        no_signal_hours=no_signal_hours,
    )
    return report.to_dict()


@router.get("/analysis/explain/{trace_id}")
async def analysis_explain(trace_id: str) -> Dict[str, Any]:
    """仅获取解释（自然语言）"""
    reporter = get_reporter()
    report = reporter.analyze_trace(trace_id)
    if not report.explanation:
        return {
            "trace_id": trace_id,
            "summary": "无可用解释",
            "paragraphs": [],
            "text": "",
        }
    exp = report.explanation
    return {
        "trace_id": trace_id,
        "summary": exp.summary,
        "paragraphs": exp.paragraphs,
        "key_metrics": exp.key_metrics,
        "root_cause_labels": exp.root_cause_labels,
        "suggestions": exp.suggestions,
        "text": exp.to_text(),
    }


@router.get("/analysis/causes/{trace_id}")
async def analysis_causes(trace_id: str) -> Dict[str, Any]:
    """仅获取根因列表"""
    reporter = get_reporter()
    report = reporter.analyze_trace(trace_id)
    return {
        "trace_id": trace_id,
        "n": len(report.causes),
        "causes": [c.to_dict() for c in report.causes],
    }


# ==================================================================
# Attribution V4 — Performance Attribution（绩效归因）
#
#   回答：这 12% 是谁赚出来的？
#
#   GET /attribution/strategy/{session_id}   策略归因
#   GET /attribution/symbol/{session_id}     品种归因 + Long/Short
#   GET /attribution/time/{session_id}       时段归因 + Regime
#   GET /attribution/risk/{session_id}       风险归因 + Drawdown
#   GET /attribution/factor/{session_id}     因子归因（预留）
#   GET /attribution/overview/{session_id}   综合归因总览
#   GET /attribution/monthly                 月度报告
#   GET /attribution/monthly/md              月度报告（Markdown）
#   GET /attribution/monthly/html            月度报告（HTML）
# ==================================================================

from quantlab.execution.observe.attribution import (
    StrategyAttribution,
    SymbolAttribution,
    TimeAttribution,
    RiskAttribution,
    FactorAttribution,
    MonthlyReview,
)


def _get_attribution_store() -> EventStore:
    """获取归因分析用的 EventStore"""
    return get_event_store()


@router.get("/attribution/strategy/{session_id}")
async def attribution_strategy(session_id: str) -> Dict[str, Any]:
    """策略归因 — 收益/PnL/成交/风险贡献"""
    store = _get_attribution_store()
    report = StrategyAttribution(store).analyze(session_id=session_id)
    return report.to_dict()


@router.get("/attribution/symbol/{session_id}")
async def attribution_symbol(session_id: str) -> Dict[str, Any]:
    """品种归因 + Long/Short 归因"""
    store = _get_attribution_store()
    report = SymbolAttribution(store).analyze(session_id=session_id)
    return report.to_dict()


@router.get("/attribution/time/{session_id}")
async def attribution_time(session_id: str) -> Dict[str, Any]:
    """时段归因 + Regime 归因"""
    store = _get_attribution_store()
    report = TimeAttribution(store).analyze(session_id=session_id)
    return report.to_dict()


@router.get("/attribution/risk/{session_id}")
async def attribution_risk(session_id: str) -> Dict[str, Any]:
    """风险归因 + Drawdown 归因"""
    store = _get_attribution_store()
    report = RiskAttribution(store).analyze(session_id=session_id)
    return report.to_dict()


@router.get("/attribution/factor/{session_id}")
async def attribution_factor(session_id: str) -> Dict[str, Any]:
    """因子归因（接口预留，待 Alpha Factory 成熟后实现）"""
    store = _get_attribution_store()
    report = FactorAttribution(store).analyze(session_id=session_id)
    return report.to_dict()


@router.get("/attribution/overview/{session_id}")
async def attribution_overview(session_id: str) -> Dict[str, Any]:
    """综合归因总览 — 一次返回所有归因结果"""
    store = _get_attribution_store()
    return {
        "session_id": session_id,
        "strategy": StrategyAttribution(store).analyze(session_id=session_id).to_dict(),
        "symbol": SymbolAttribution(store).analyze(session_id=session_id).to_dict(),
        "time": TimeAttribution(store).analyze(session_id=session_id).to_dict(),
        "risk": RiskAttribution(store).analyze(session_id=session_id).to_dict(),
        "factor": FactorAttribution(store).analyze(session_id=session_id).to_dict(),
    }


@router.get("/attribution/range")
async def attribution_range(
    start_ts: int,
    end_ts: int,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """按时间范围查询归因"""
    store = _get_attribution_store()
    return {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "session_id": session_id,
        "strategy": StrategyAttribution(store).analyze_range(
            start_ts, end_ts, session_id
        ).to_dict(),
        "symbol": SymbolAttribution(store).analyze_range(
            start_ts, end_ts, session_id
        ).to_dict(),
        "time": TimeAttribution(store).analyze_range(
            start_ts, end_ts, session_id
        ).to_dict(),
        "risk": RiskAttribution(store).analyze_range(
            start_ts, end_ts, session_id
        ).to_dict(),
    }


# ------------------------------------------------------------------
# Monthly Review
# ------------------------------------------------------------------

@router.get("/attribution/monthly")
async def attribution_monthly(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """月度报告（JSON）"""
    store = _get_attribution_store()
    report = MonthlyReview(store).generate(year=year, month=month, session_id=session_id)
    return report.to_dict()


@router.get("/attribution/monthly/md")
async def attribution_monthly_md(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """月度报告（Markdown）"""
    store = _get_attribution_store()
    report = MonthlyReview(store).generate(year=year, month=month, session_id=session_id)
    return {
        "year": year,
        "month": month,
        "period_label": report.period_label,
        "markdown": report.to_markdown(),
    }


@router.get("/attribution/monthly/html")
async def attribution_monthly_html(
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """月度报告（HTML）"""
    store = _get_attribution_store()
    report = MonthlyReview(store).generate(year=year, month=month, session_id=session_id)
    return {
        "year": year,
        "month": month,
        "period_label": report.period_label,
        "html": report.to_html(),
    }
