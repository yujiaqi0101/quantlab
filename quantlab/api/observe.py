"""
Observe API — 可观测性 API

Observe Studio 的后端支撑，覆盖：
  - Trade Analytics      交易分析
  - Execution Analytics  执行分析（latency）
  - Timeline             事件时间线
  - Health               策略健康
  - Drift                数据漂移
  - Journal              交易日志（复用 execution/journal）
  - Replay               重放（复用 runtime/replay）

端点：
  GET  /api/v1/observe/trade-analytics           交易分析
  GET  /api/v1/observe/execution-analytics       执行分析
  GET  /api/v1/observe/timeline                  事件时间线
  GET  /api/v1/observe/timeline/traces           trace 列表
  GET  /api/v1/observe/timeline/traces/{id}      单个 trace 详情
  GET  /api/v1/observe/health                    所有策略健康
  GET  /api/v1/observe/health/{strategy_id}      单个策略健康
  POST /api/v1/observe/health/{strategy_id}/signal   记录信号
  POST /api/v1/observe/health/{strategy_id}/fill     记录成交
  GET  /api/v1/observe/drift/baselines            漂移基线列表
  POST /api/v1/observe/drift/baselines/{name}     设置基线
  POST /api/v1/observe/drift/detect/{name}        检测漂移
  GET  /api/v1/observe/journal                    日志列表
  GET  /api/v1/observe/stats                      全局统计
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("quantlab.api.observe")

router = APIRouter(prefix="/api/v1/observe", tags=["observe"])


# ------------------------------------------------------------------
# 全局实例（懒加载）
# ------------------------------------------------------------------

_trade_analytics = None
_execution_analytics = None
_timeline_view = None
_health_monitor = None
_drift_detector = None
_journal = None


def _get_trade_analytics():
    global _trade_analytics
    if _trade_analytics is None:
        from quantlab.observe import TradeAnalytics
        _trade_analytics = TradeAnalytics()
    return _trade_analytics


def _get_execution_analytics():
    global _execution_analytics
    if _execution_analytics is None:
        from quantlab.observe import ExecutionAnalytics
        _execution_analytics = ExecutionAnalytics()
    return _execution_analytics


def _get_timeline_view():
    global _timeline_view
    if _timeline_view is None:
        from quantlab.observe import TimelineView
        _timeline_view = TimelineView()
    return _timeline_view


def _get_health_monitor():
    global _health_monitor
    if _health_monitor is None:
        from quantlab.observe import get_health_monitor
        _health_monitor = get_health_monitor()
    return _health_monitor


def _get_drift_detector():
    global _drift_detector
    if _drift_detector is None:
        from quantlab.observe import DriftDetector
        _drift_detector = DriftDetector()
    return _drift_detector


def _get_journal():
    global _journal
    if _journal is None:
        try:
            from quantlab.execution.journal import TradingJournal
            _journal = TradingJournal()
        except Exception as e:
            logger.warning(f"Journal not available: {e}")
            _journal = None
    return _journal


# ------------------------------------------------------------------
# Pydantic 模型
# ------------------------------------------------------------------

class TradeRecord(BaseModel):
    pnl: float
    side: str = ""
    symbol: str = ""


class LatencyRecordIn(BaseModel):
    trace_id: str
    signal_time: Optional[str] = None
    order_time: Optional[str] = None
    fill_time: Optional[str] = None


class SignalIn(BaseModel):
    timestamp: Optional[str] = None


class FillIn(BaseModel):
    pnl: float = 0.0
    timestamp: Optional[str] = None


class BaselineIn(BaseModel):
    values: List[float]


class DriftDetectIn(BaseModel):
    values: List[float]
    method: Optional[str] = None


# ------------------------------------------------------------------
# Trade Analytics
# ------------------------------------------------------------------

@router.get("/trade-analytics")
async def get_trade_analytics() -> Dict[str, Any]:
    """获取交易分析报告（需要先通过 POST 上传 trades）"""
    # 这里返回空报告，实际数据通过 POST 接口上传
    analytics = _get_trade_analytics()
    return {
        "message": "use POST /trade-analytics to upload trades, then GET /trade-analytics/report",
        "n_cached_trades": getattr(analytics, "_cached_n", 0),
    }


@router.post("/trade-analytics")
async def post_trade_analytics(trades: List[TradeRecord]) -> Dict[str, Any]:
    """上传 trades 并生成分析报告"""
    analytics = _get_trade_analytics()
    trades_dict = [t.dict() for t in trades]
    report = analytics.analyze(trades_dict)
    return report.to_dict()


# ------------------------------------------------------------------
# Execution Analytics
# ------------------------------------------------------------------

@router.get("/execution-analytics")
async def get_execution_analytics() -> Dict[str, Any]:
    """获取执行分析报告"""
    return _get_execution_analytics().report().to_dict()


@router.post("/execution-analytics")
async def post_latency_record(rec: LatencyRecordIn) -> Dict[str, Any]:
    """记录一笔延迟"""
    r = _get_execution_analytics().record(
        trace_id=rec.trace_id,
        signal_time=rec.signal_time,
        order_time=rec.order_time,
        fill_time=rec.fill_time,
    )
    return r.to_dict()


# ------------------------------------------------------------------
# Timeline
# ------------------------------------------------------------------

@router.get("/timeline")
async def get_timeline(
    limit: int = Query(100, ge=1, le=10000),
    category: Optional[str] = None,
    trace_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """获取事件时间线"""
    view = _get_timeline_view()
    entries = view.get_timeline(limit=limit, category=category, trace_id=trace_id)
    return [e.to_dict() for e in entries]


@router.get("/timeline/traces")
async def list_traces(limit: int = Query(50, ge=1, le=500)) -> List[Dict[str, Any]]:
    """列出所有 trace 摘要"""
    view = _get_timeline_view()
    return [s.to_dict() for s in view.list_traces(limit=limit)]


@router.get("/timeline/traces/{trace_id}")
async def get_trace(trace_id: str) -> Dict[str, Any]:
    """获取单个 trace 详情"""
    view = _get_timeline_view()
    summary = view.get_by_trace(trace_id)
    if summary is None:
        raise HTTPException(404, f"trace {trace_id} not found")
    entries = view.get_timeline(trace_id=trace_id, limit=10000)
    return {
        "summary": summary.to_dict(),
        "spans": [e.to_dict() for e in entries],
    }


@router.get("/timeline/stats")
async def timeline_stats() -> Dict[str, Any]:
    """时间线统计"""
    return _get_timeline_view().stats()


# ------------------------------------------------------------------
# Health
# ------------------------------------------------------------------

@router.get("/health")
async def list_health() -> List[Dict[str, Any]]:
    """所有策略健康状态"""
    monitor = _get_health_monitor()
    return [h.to_dict() for h in monitor.list_health()]


@router.get("/health/{strategy_id}")
async def get_health(strategy_id: str) -> Dict[str, Any]:
    """单个策略健康状态"""
    monitor = _get_health_monitor()
    return monitor.get_health(strategy_id).to_dict()


@router.post("/health/{strategy_id}/signal")
async def record_signal(strategy_id: str, signal: SignalIn) -> Dict[str, Any]:
    """记录策略信号"""
    monitor = _get_health_monitor()
    from datetime import datetime
    ts = datetime.fromisoformat(signal.timestamp) if signal.timestamp else None
    monitor.record_signal(strategy_id, timestamp=ts)
    return {"status": "ok", "strategy_id": strategy_id}


@router.post("/health/{strategy_id}/fill")
async def record_fill(strategy_id: str, fill: FillIn) -> Dict[str, Any]:
    """记录策略成交"""
    monitor = _get_health_monitor()
    from datetime import datetime
    ts = datetime.fromisoformat(fill.timestamp) if fill.timestamp else None
    monitor.record_fill(strategy_id, pnl=fill.pnl, timestamp=ts)
    return {"status": "ok", "strategy_id": strategy_id, "pnl": fill.pnl}


@router.get("/health/stats")
async def health_stats() -> Dict[str, Any]:
    """健康统计"""
    return _get_health_monitor().stats()


# ------------------------------------------------------------------
# Drift
# ------------------------------------------------------------------

@router.get("/drift/baselines")
async def list_baselines() -> Dict[str, Any]:
    """列出所有漂移基线"""
    return _get_drift_detector().stats()


@router.post("/drift/baselines/{name}")
async def set_baseline(name: str, body: BaselineIn) -> Dict[str, Any]:
    """设置漂移基线"""
    detector = _get_drift_detector()
    detector.set_baseline(name, body.values)
    return {"status": "ok", "feature": name, "n": len(body.values)}


@router.post("/drift/detect/{name}")
async def detect_drift(name: str, body: DriftDetectIn) -> Dict[str, Any]:
    """检测漂移"""
    detector = _get_drift_detector()
    result = detector.detect(name, body.values, method=body.method)
    return result.to_dict()


@router.delete("/drift/baselines/{name}")
async def remove_baseline(name: str) -> Dict[str, Any]:
    """删除漂移基线"""
    ok = _get_drift_detector().remove_baseline(name)
    return {"status": "ok" if ok else "not_found", "feature": name}


# ------------------------------------------------------------------
# Journal（复用 execution/journal）
# ------------------------------------------------------------------

@router.get("/journal")
async def list_journal(
    category: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
) -> Dict[str, Any]:
    """日志列表"""
    journal = _get_journal()
    if journal is None:
        return {"entries": [], "error": "journal not available"}
    entries = journal.list_entries(category=category, strategy=strategy)
    entries = entries[-limit:]
    return {
        "entries": [e.to_dict() if hasattr(e, "to_dict") else e for e in entries],
        "n": len(entries),
    }


@router.get("/journal/stats")
async def journal_stats() -> Dict[str, Any]:
    """日志统计"""
    journal = _get_journal()
    if journal is None:
        return {"error": "journal not available"}
    return journal.stats()


# ------------------------------------------------------------------
# 全局统计
# ------------------------------------------------------------------

@router.get("/stats")
async def global_stats() -> Dict[str, Any]:
    """全局可观测性统计"""
    return {
        "trade_analytics": {
            "available": True,
        },
        "execution_analytics": _get_execution_analytics().report().to_dict(),
        "timeline": _get_timeline_view().stats(),
        "health": _get_health_monitor().stats(),
        "drift": _get_drift_detector().stats(),
    }
