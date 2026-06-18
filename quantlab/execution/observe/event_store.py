"""
Event Store — 事件持久化存储

Replay 的基础。事件处理完后写入 EventStore，后续可查询/重放。

存储：SQLite（第一版不要 Kafka）
结构：
    events(
        event_id TEXT PRIMARY KEY,
        timestamp INTEGER,
        event_type TEXT,
        source TEXT,
        trace_id TEXT,
        session_id TEXT,
        payload TEXT  -- JSON
    )
    sessions(
        session_id TEXT PRIMARY KEY,
        strategy TEXT,
        symbol TEXT,
        start_time INTEGER,
        end_time INTEGER,
        meta TEXT  -- JSON
    )

索引：timestamp、event_type、session_id、trace_id
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger("quantlab.execution.observe.event_store")


@dataclass
class StoredEvent:
    """存储的事件"""
    event_id: str
    timestamp: int
    event_type: str
    source: str = ""
    trace_id: str = ""
    session_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "payload": self.payload,
        }


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    strategy: str = ""
    symbol: str = ""
    start_time: int = 0
    end_time: int = 0
    n_events: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "strategy": self.strategy,
            "symbol": self.symbol,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "n_events": self.n_events,
            "meta": self.meta,
        }


class EventStore:
    """
    事件存储 — SQLite 持久化

    用法：
        store = EventStore("replay.db")
        store.open()
        store.append(event_type="SIGNAL", payload={...}, session_id="s1")
        events = store.query(session_id="s1", event_type="SIGNAL")
        store.close()
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS events (
        event_id    TEXT PRIMARY KEY,
        timestamp   INTEGER NOT NULL,
        event_type  TEXT NOT NULL,
        source      TEXT DEFAULT '',
        trace_id    TEXT DEFAULT '',
        session_id  TEXT DEFAULT '',
        payload     TEXT DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_events_timestamp   ON events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_events_type        ON events(event_type);
    CREATE INDEX IF NOT EXISTS idx_events_session     ON events(session_id);
    CREATE INDEX IF NOT EXISTS idx_events_trace       ON events(trace_id);

    CREATE TABLE IF NOT EXISTS sessions (
        session_id  TEXT PRIMARY KEY,
        strategy    TEXT DEFAULT '',
        symbol      TEXT DEFAULT '',
        start_time  INTEGER DEFAULT 0,
        end_time    INTEGER DEFAULT 0,
        n_events    INTEGER DEFAULT 0,
        meta        TEXT DEFAULT '{}'
    );
    CREATE INDEX IF NOT EXISTS idx_sessions_strategy ON sessions(strategy);
    CREATE INDEX IF NOT EXISTS idx_sessions_start    ON sessions(start_time);
    """

    def __init__(self, db_path: str = "storage/replay.db") -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

    def open(self) -> None:
        import os
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()
        logger.info(f"EventStore opened: {self.db_path}")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        with self._lock:
            if not self._conn:
                self.open()
            cur = self._conn.cursor()
            try:
                yield cur
                self._conn.commit()
            finally:
                cur.close()

    # ------------------------------------------------------------------
    # Event 写入
    # ------------------------------------------------------------------

    def append(
        self,
        event_type: str,
        payload: Dict[str, Any],
        timestamp: Optional[int] = None,
        source: str = "",
        trace_id: str = "",
        session_id: str = "",
        event_id: Optional[str] = None,
    ) -> str:
        """追加事件"""
        eid = event_id or uuid.uuid4().hex[:16]
        ts = timestamp or int(time.time() * 1000)
        tid = trace_id or uuid.uuid4().hex[:12]
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)

        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO events
                   (event_id, timestamp, event_type, source, trace_id, session_id, payload)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (eid, ts, event_type, source, tid, session_id, payload_json),
            )

            # 更新 session 的 end_time 和 n_events
            if session_id:
                cur.execute(
                    "UPDATE sessions SET end_time = ?, n_events = n_events + 1 WHERE session_id = ?",
                    (ts, session_id),
                )
                if cur.rowcount == 0:
                    # session 不存在，自动创建
                    cur.execute(
                        """INSERT OR IGNORE INTO sessions
                           (session_id, strategy, symbol, start_time, end_time, n_events, meta)
                           VALUES (?, '', '', ?, ?, 1, '{}')""",
                        (session_id, ts, ts),
                    )

        return eid

    def append_event(self, event: StoredEvent) -> str:
        """追加 StoredEvent 对象"""
        return self.append(
            event_type=event.event_type,
            payload=event.payload,
            timestamp=event.timestamp,
            source=event.source,
            trace_id=event.trace_id,
            session_id=event.session_id,
            event_id=event.event_id,
        )

    # ------------------------------------------------------------------
    # Event 查询
    # ------------------------------------------------------------------

    def query(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        source: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0,
        order: str = "asc",
    ) -> List[StoredEvent]:
        """查询事件"""
        sql = "SELECT * FROM events WHERE 1=1"
        params: List[Any] = []

        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        if trace_id:
            sql += " AND trace_id = ?"
            params.append(trace_id)
        if source:
            sql += " AND source = ?"
            params.append(source)
        if start_ts is not None:
            sql += " AND timestamp >= ?"
            params.append(start_ts)
        if end_ts is not None:
            sql += " AND timestamp <= ?"
            params.append(end_ts)

        sql += f" ORDER BY timestamp {'DESC' if order == 'desc' else 'ASC'}"
        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

        return [self._row_to_event(r) for r in rows]

    def get_event(self, event_id: str) -> Optional[StoredEvent]:
        """获取单个事件"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cur.fetchone()
        return self._row_to_event(row) if row else None

    def get_trace(self, trace_id: str) -> List[StoredEvent]:
        """获取同一 trace 的所有事件"""
        return self.query(trace_id=trace_id, limit=10000)

    def count(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """计数"""
        sql = "SELECT COUNT(*) FROM events WHERE 1=1"
        params: List[Any] = []
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)

        with self._cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # Session 管理
    # ------------------------------------------------------------------

    def create_session(
        self,
        session_id: str,
        strategy: str = "",
        symbol: str = "",
        start_time: Optional[int] = None,
        meta: Optional[Dict] = None,
    ) -> SessionInfo:
        """创建会话"""
        ts = start_time or int(time.time() * 1000)
        meta_json = json.dumps(meta or {}, ensure_ascii=False)

        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO sessions
                   (session_id, strategy, symbol, start_time, end_time, n_events, meta)
                   VALUES (?, ?, ?, ?, ?, 0, ?)""",
                (session_id, strategy, symbol, ts, ts, meta_json),
            )

        return SessionInfo(
            session_id=session_id,
            strategy=strategy,
            symbol=symbol,
            start_time=ts,
            end_time=ts,
            n_events=0,
            meta=meta or {},
        )

    def update_session(
        self,
        session_id: str,
        end_time: Optional[int] = None,
        meta: Optional[Dict] = None,
    ) -> None:
        """更新会话"""
        sets: List[str] = []
        params: List[Any] = []
        if end_time is not None:
            sets.append("end_time = ?")
            params.append(end_time)
        if meta is not None:
            sets.append("meta = ?")
            params.append(json.dumps(meta, ensure_ascii=False))
        if not sets:
            return
        params.append(session_id)
        with self._cursor() as cur:
            cur.execute(
                f"UPDATE sessions SET {', '.join(sets)} WHERE session_id = ?",
                params,
            )

    def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(
        self,
        strategy: Optional[str] = None,
        limit: int = 100,
    ) -> List[SessionInfo]:
        """列出会话"""
        sql = "SELECT * FROM sessions"
        params: List[Any] = []
        if strategy:
            sql += " WHERE strategy = ?"
            params.append(strategy)
        sql += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        with self._cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._row_to_session(r) for r in rows]

    def delete_session(self, session_id: str) -> int:
        """删除会话及其事件"""
        with self._cursor() as cur:
            cur.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            n = cur.rowcount
            cur.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        return n

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _row_to_event(self, row: sqlite3.Row) -> StoredEvent:
        try:
            payload = json.loads(row["payload"])
        except Exception:
            payload = {}
        return StoredEvent(
            event_id=row["event_id"],
            timestamp=row["timestamp"],
            event_type=row["event_type"],
            source=row["source"],
            trace_id=row["trace_id"],
            session_id=row["session_id"],
            payload=payload,
        )

    def _row_to_session(self, row: sqlite3.Row) -> SessionInfo:
        try:
            meta = json.loads(row["meta"])
        except Exception:
            meta = {}
        return SessionInfo(
            session_id=row["session_id"],
            strategy=row["strategy"],
            symbol=row["symbol"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            n_events=row["n_events"],
            meta=meta,
        )

    def stats(self) -> Dict[str, Any]:
        """统计"""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            n_events = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM sessions")
            n_sessions = cur.fetchone()[0]
            cur.execute(
                "SELECT event_type, COUNT(*) FROM events GROUP BY event_type ORDER BY COUNT(*) DESC"
            )
            by_type = {r[0]: r[1] for r in cur.fetchall()}
        return {
            "n_events": n_events,
            "n_sessions": n_sessions,
            "by_type": by_type,
        }


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_store: Optional[EventStore] = None
_global_lock = threading.Lock()


def get_event_store() -> EventStore:
    global _global_store
    if _global_store is None:
        with _global_lock:
            if _global_store is None:
                _global_store = EventStore()
                _global_store.open()
    return _global_store


def set_event_store(store: EventStore) -> None:
    global _global_store
    with _global_lock:
        _global_store = store
