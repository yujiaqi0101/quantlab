"""
Trading Session — 交易会话

Replay 的核心概念：一次策略运行形成一个 Session，关联所有事件。

例如：
    2026-06-18 BTC Momentum Strategy → session_id="20260618_btc_momentum"

用法：
    mgr = SessionManager(store)
    sid = mgr.start_session(strategy="momentum", symbol="BTCUSDT")
    store.append("SIGNAL", {...}, session_id=sid)
    mgr.end_session(sid)
    info = mgr.get_session(sid)
    events = mgr.get_session_events(sid)
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .event_store import EventStore, SessionInfo, StoredEvent, get_event_store

logger = logging.getLogger("quantlab.execution.observe.session")


@dataclass
class TradingSession:
    """交易会话"""
    session_id: str
    strategy: str = ""
    symbol: str = ""
    start_time: int = 0
    end_time: int = 0
    n_events: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)
    # 运行时字段
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "n_events": self.n_events,
            "meta": self.meta,
            "is_active": self.is_active,
        }


class SessionManager:
    """
    会话管理器

    用法：
        mgr = SessionManager()
        sid = mgr.start_session(strategy="momentum", symbol="BTCUSDT")
        # ... 运行策略，事件写入 EventStore ...
        mgr.end_session(sid)
    """

    def __init__(self, store: Optional[EventStore] = None) -> None:
        self.store = store or get_event_store()
        self._active: Dict[str, TradingSession] = {}

    def start_session(
        self,
        strategy: str = "",
        symbol: str = "",
        session_id: Optional[str] = None,
        meta: Optional[Dict] = None,
    ) -> str:
        """启动新会话"""
        sid = session_id or self._generate_id(strategy, symbol)
        ts = int(time.time() * 1000)

        info = self.store.create_session(
            session_id=sid,
            strategy=strategy,
            symbol=symbol,
            start_time=ts,
            meta=meta,
        )

        session = TradingSession(
            session_id=sid,
            strategy=strategy,
            symbol=symbol,
            start_time=ts,
            end_time=ts,
            n_events=0,
            meta=meta or {},
            is_active=True,
        )
        self._active[sid] = session
        logger.info(f"Session started: {sid} (strategy={strategy}, symbol={symbol})")
        return sid

    def end_session(self, session_id: str) -> None:
        """结束会话"""
        ts = int(time.time() * 1000)
        self.store.update_session(session_id, end_time=ts)
        if session_id in self._active:
            self._active[session_id].is_active = False
            self._active[session_id].end_time = ts
            del self._active[session_id]
        logger.info(f"Session ended: {session_id}")

    def get_session(self, session_id: str) -> Optional[TradingSession]:
        """获取会话"""
        active = self._active.get(session_id)
        if active:
            return active
        info = self.store.get_session(session_id)
        if not info:
            return None
        return TradingSession(
            session_id=info.session_id,
            strategy=info.strategy,
            symbol=info.symbol,
            start_time=info.start_time,
            end_time=info.end_time,
            n_events=info.n_events,
            meta=info.meta,
            is_active=False,
        )

    def get_session_events(self, session_id: str) -> List[StoredEvent]:
        """获取会话所有事件"""
        return self.store.query(session_id=session_id, limit=100000)

    def list_sessions(
        self,
        strategy: Optional[str] = None,
        limit: int = 100,
    ) -> List[TradingSession]:
        """列出会话"""
        infos = self.store.list_sessions(strategy=strategy, limit=limit)
        sessions = []
        for info in infos:
            is_active = info.session_id in self._active
            sessions.append(TradingSession(
                session_id=info.session_id,
                strategy=info.strategy,
                symbol=info.symbol,
                start_time=info.start_time,
                end_time=info.end_time,
                n_events=info.n_events,
                meta=info.meta,
                is_active=is_active,
            ))
        return sessions

    def list_active(self) -> List[TradingSession]:
        """列出活跃会话"""
        return list(self._active.values())

    def append_event(
        self,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[int] = None,
        source: str = "",
        trace_id: str = "",
    ) -> str:
        """向会话追加事件"""
        return self.store.append(
            event_type=event_type,
            payload=payload,
            timestamp=timestamp,
            source=source,
            trace_id=trace_id,
            session_id=session_id,
        )

    def _generate_id(self, strategy: str, symbol: str) -> str:
        date_str = time.strftime("%Y%m%d", time.localtime())
        rand = uuid.uuid4().hex[:6]
        parts = [date_str]
        if strategy:
            parts.append(strategy[:20])
        if symbol:
            parts.append(symbol)
        parts.append(rand)
        return "_".join(parts)


# 全局单例
_global_mgr: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _global_mgr
    if _global_mgr is None:
        _global_mgr = SessionManager()
    return _global_mgr
