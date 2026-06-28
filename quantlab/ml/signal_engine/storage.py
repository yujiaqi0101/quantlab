"""
Signal Engine SQLite 存储

在 storage/ml_lab.db 新增 signals + signal_versions 两张表。
遵循项目规则：不写模拟数据，复用现有 MLStore 模式。
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.signal_engine.storage")

DEFAULT_DB_PATH = "storage/ml_lab.db"


class SignalStore:
    """Signal Engine SQLite 存储层"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_tables(self) -> None:
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS signals (
                    signal_id        TEXT PRIMARY KEY,
                    symbol           TEXT NOT NULL,
                    datetime         TEXT NOT NULL,
                    direction        TEXT NOT NULL,
                    score            REAL NOT NULL,
                    confidence       REAL NOT NULL,
                    expected_return  REAL,
                    suggested_weight REAL,
                    holding_period   INTEGER,
                    source_model     TEXT,
                    generator        TEXT,
                    metadata         TEXT,
                    version_id       TEXT,
                    created_at       TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
                CREATE INDEX IF NOT EXISTS idx_signals_datetime ON signals(datetime);
                CREATE INDEX IF NOT EXISTS idx_signals_direction ON signals(direction);

                CREATE TABLE IF NOT EXISTS signal_versions (
                    version_id          TEXT PRIMARY KEY,
                    signal_id           TEXT NOT NULL,
                    version             INTEGER NOT NULL,
                    generator_config    TEXT,
                    model_version       TEXT,
                    dataset_id          TEXT,
                    validation_summary  TEXT,
                    pipeline_config     TEXT,
                    created_at          TEXT NOT NULL,
                    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
                );
                CREATE INDEX IF NOT EXISTS idx_versions_signal ON signal_versions(signal_id);
            """)
        logger.info(f"SignalStore initialized: {self.db_path}")

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ---- Signal CRUD ----

    def save_signal(self, signal_dict: Dict[str, Any], version_id: str = "") -> None:
        """保存单个信号"""
        now = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO signals
                   (signal_id, symbol, datetime, direction, score, confidence,
                    expected_return, suggested_weight, holding_period, source_model,
                    generator, metadata, version_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    signal_dict.get("signal_id", ""),
                    signal_dict.get("symbol", ""),
                    signal_dict.get("datetime", ""),
                    signal_dict.get("direction", "NEUTRAL"),
                    float(signal_dict.get("score", 0.0)),
                    float(signal_dict.get("confidence", 0.0)),
                    float(signal_dict.get("expected_return", 0.0)),
                    float(signal_dict.get("suggested_weight", 0.0)),
                    int(signal_dict.get("holding_period", 0)),
                    signal_dict.get("source_model", ""),
                    signal_dict.get("generator", ""),
                    json.dumps(signal_dict.get("metadata", {}), ensure_ascii=False),
                    version_id,
                    now,
                ],
            )

    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM signals WHERE signal_id = ?", [signal_id])
            row = cur.fetchone()
        return self._row_to_signal_dict(row) if row else None

    def list_signals(
        self,
        symbol: str = "",
        direction: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM signals WHERE 1=1"
        params: List[Any] = []
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if direction:
            sql += " AND direction = ?"
            params.append(direction)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [self._row_to_signal_dict(r) for r in rows]

    def count_signals(self, symbol: str = "", direction: str = "") -> int:
        sql = "SELECT COUNT(*) FROM signals WHERE 1=1"
        params: List[Any] = []
        if symbol:
            sql += " AND symbol = ?"
            params.append(symbol)
        if direction:
            sql += " AND direction = ?"
            params.append(direction)
        with self._cursor() as cur:
            cur.execute(sql, params)
            return int(cur.fetchone()[0])

    def update_signal_version_id(self, signal_id: str, version_id: str) -> None:
        """回填 signal 的 version_id"""
        with self._cursor() as cur:
            cur.execute(
                "UPDATE signals SET version_id = ? WHERE signal_id = ?",
                [version_id, signal_id],
            )

    # ---- Version CRUD ----

    def save_version(self, version_dict: Dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO signal_versions
                   (version_id, signal_id, version, generator_config, model_version,
                    dataset_id, validation_summary, pipeline_config, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [
                    version_dict.get("version_id", ""),
                    version_dict.get("signal_id", ""),
                    int(version_dict.get("version", 1)),
                    json.dumps(version_dict.get("generator_config", {}), ensure_ascii=False),
                    version_dict.get("model_version", ""),
                    version_dict.get("dataset_id", ""),
                    json.dumps(version_dict.get("validation_summary", {}), ensure_ascii=False),
                    json.dumps(version_dict.get("pipeline_config", {}), ensure_ascii=False),
                    version_dict.get("created_at", now),
                ],
            )

    def list_versions(self, signal_id: str = "") -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            if signal_id:
                cur.execute(
                    "SELECT * FROM signal_versions WHERE signal_id = ? ORDER BY version DESC",
                    [signal_id],
                )
            else:
                cur.execute(
                    "SELECT * FROM signal_versions ORDER BY version DESC LIMIT 200",
                )
            rows = cur.fetchall()
        return [self._row_to_version_dict(r) for r in rows]

    def get_version(self, version_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM signal_versions WHERE version_id = ?", [version_id])
            row = cur.fetchone()
        return self._row_to_version_dict(row) if row else None

    def latest_version_number(self, signal_id: str) -> int:
        with self._cursor() as cur:
            cur.execute(
                "SELECT MAX(version) FROM signal_versions WHERE signal_id = ?",
                [signal_id],
            )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 0

    # ---- 行转换 ----

    @staticmethod
    def _row_to_signal_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.get("metadata") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
        return d

    @staticmethod
    def _row_to_version_dict(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for k in ("generator_config", "validation_summary", "pipeline_config"):
            try:
                d[k] = json.loads(d.get(k) or "{}")
            except (json.JSONDecodeError, TypeError):
                d[k] = {}
        return d


# ---- 模块级单例 ----

_store: Optional[SignalStore] = None
_store_lock = threading.Lock()


def get_signal_store() -> SignalStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = SignalStore()
    return _store
