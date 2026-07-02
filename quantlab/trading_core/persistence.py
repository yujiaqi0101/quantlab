"""
Trading Core 持久化层
=====================

将 TradingCore 的运行时状态（账户/持仓/订单/成交/快照）持久化到 SQLite。

5 张表：
    - paper_accounts    账户
    - paper_positions   持仓快照
    - paper_orders      订单
    - paper_trades      成交
    - paper_snapshots   净值快照（用于 Replay + Equity Curve）

设计原则：
    - 纯 DB CRUD，不依赖 TradingCore（解耦）
    - 线程安全（threading.local + RLock）
    - 时间统一用 ISO 字符串存储
    - 不写模拟市场数据（仅交易状态）
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.trading_core.persistence")

DEFAULT_DB_PATH = "storage/trading.db"


class TradingPersistence:
    """TradingCore 状态持久化到 paper_* 表。"""

    _instance: Optional["TradingPersistence"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._rlock = threading.RLock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()
        logger.info(f"TradingPersistence initialized: {db_path}")

    # ------------------------------------------------------------------
    # 连接管理
    # ------------------------------------------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path, check_same_thread=False
            )
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

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    # ------------------------------------------------------------------
    # 建表
    # ------------------------------------------------------------------
    def _init_tables(self) -> None:
        with self._cursor() as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS paper_accounts (
                    strategy_id      TEXT PRIMARY KEY,
                    strategy_name    TEXT NOT NULL,
                    version          TEXT DEFAULT '1.0',
                    mode             TEXT NOT NULL DEFAULT 'paper',
                    initial_capital  REAL NOT NULL,
                    cash             REAL NOT NULL,
                    frozen_cash      REAL DEFAULT 0,
                    total_value      REAL NOT NULL,
                    peak_value       REAL NOT NULL,
                    status           TEXT DEFAULT 'running',
                    started_at       TEXT NOT NULL,
                    updated_at       TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS paper_positions (
                    strategy_id    TEXT NOT NULL,
                    symbol         TEXT NOT NULL,
                    direction      TEXT NOT NULL DEFAULT 'long',
                    quantity       REAL NOT NULL,
                    entry_price    REAL NOT NULL,
                    entry_date     TEXT NOT NULL,
                    current_price  REAL DEFAULT 0,
                    market_value   REAL DEFAULT 0,
                    unrealized_pnl REAL DEFAULT 0,
                    realized_pnl   REAL DEFAULT 0,
                    updated_at     TEXT NOT NULL,
                    PRIMARY KEY (strategy_id, symbol)
                );

                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id        TEXT PRIMARY KEY,
                    strategy_id     TEXT NOT NULL,
                    symbol          TEXT NOT NULL,
                    side            TEXT NOT NULL,
                    order_type      TEXT DEFAULT 'market',
                    quantity        REAL NOT NULL,
                    price           REAL,
                    signal_id       TEXT,
                    client_order_id TEXT,
                    broker_order_id TEXT,
                    status          TEXT NOT NULL,
                    filled_qty      REAL DEFAULT 0,
                    filled_price    REAL DEFAULT 0,
                    reason          TEXT,
                    created_at      TEXT NOT NULL,
                    updated_at      TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_paper_orders_strategy ON paper_orders(strategy_id);
                CREATE INDEX IF NOT EXISTS idx_paper_orders_status ON paper_orders(status);
                CREATE INDEX IF NOT EXISTS idx_paper_orders_symbol ON paper_orders(symbol);

                CREATE TABLE IF NOT EXISTS paper_trades (
                    trade_id    TEXT PRIMARY KEY,
                    order_id    TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    symbol      TEXT NOT NULL,
                    side        TEXT NOT NULL,
                    quantity    REAL NOT NULL,
                    price       REAL NOT NULL,
                    amount      REAL NOT NULL,
                    commission  REAL DEFAULT 0,
                    slippage    REAL DEFAULT 0,
                    trade_date  TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES paper_orders(order_id)
                );
                CREATE INDEX IF NOT EXISTS idx_paper_trades_strategy ON paper_trades(strategy_id);
                CREATE INDEX IF NOT EXISTS idx_paper_trades_date ON paper_trades(trade_date);
                CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);

                CREATE TABLE IF NOT EXISTS paper_snapshots (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id     TEXT NOT NULL,
                    snapshot_time   TEXT NOT NULL,
                    cash            REAL NOT NULL,
                    position_value  REAL NOT NULL,
                    total_value     REAL NOT NULL,
                    daily_return    REAL DEFAULT 0,
                    realized_pnl    REAL DEFAULT 0,
                    unrealized_pnl  REAL DEFAULT 0,
                    max_drawdown    REAL DEFAULT 0,
                    bar_timestamp   TEXT,
                    created_at      TEXT NOT NULL,
                    UNIQUE(strategy_id, snapshot_time)
                );
                CREATE INDEX IF NOT EXISTS idx_paper_snapshots_strategy ON paper_snapshots(strategy_id);
                CREATE INDEX IF NOT EXISTS idx_paper_snapshots_time ON paper_snapshots(snapshot_time);
                """
            )

    # ------------------------------------------------------------------
    # 账户
    # ------------------------------------------------------------------
    def save_account(self, account: Dict[str, Any]) -> None:
        """upsert 账户。"""
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO paper_accounts
                    (strategy_id, strategy_name, version, mode, initial_capital,
                     cash, frozen_cash, total_value, peak_value, status,
                     started_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id) DO UPDATE SET
                    strategy_name=excluded.strategy_name,
                    version=excluded.version,
                    mode=excluded.mode,
                    initial_capital=excluded.initial_capital,
                    cash=excluded.cash,
                    frozen_cash=excluded.frozen_cash,
                    total_value=excluded.total_value,
                    peak_value=excluded.peak_value,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    account["strategy_id"],
                    account.get("strategy_name", ""),
                    account.get("version", "1.0"),
                    account.get("mode", "paper"),
                    account["initial_capital"],
                    account["cash"],
                    account.get("frozen_cash", 0),
                    account["total_value"],
                    account.get("peak_value", account["total_value"]),
                    account.get("status", "running"),
                    account.get("started_at", now),
                    now,
                ),
            )

    def load_account(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM paper_accounts WHERE strategy_id=?",
                (strategy_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_accounts(
        self, mode: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM paper_accounts WHERE 1=1"
        params: List[Any] = []
        if mode:
            sql += " AND mode=?"
            params.append(mode)
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY started_at DESC"
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def update_account_status(self, strategy_id: str, status: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "UPDATE paper_accounts SET status=?, updated_at=? WHERE strategy_id=?",
                (status, datetime.now().isoformat(), strategy_id),
            )

    def delete_account(self, strategy_id: str) -> None:
        with self._cursor() as cur:
            for tbl in ("paper_positions", "paper_orders", "paper_trades", "paper_snapshots"):
                cur.execute(
                    f"DELETE FROM {tbl} WHERE strategy_id=?", (strategy_id,)
                )
            cur.execute("DELETE FROM paper_accounts WHERE strategy_id=?", (strategy_id,))

    # ------------------------------------------------------------------
    # 持仓
    # ------------------------------------------------------------------
    def upsert_position(self, strategy_id: str, pos: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO paper_positions
                    (strategy_id, symbol, direction, quantity, entry_price,
                     entry_date, current_price, market_value, unrealized_pnl,
                     realized_pnl, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id, symbol) DO UPDATE SET
                    direction=excluded.direction,
                    quantity=excluded.quantity,
                    entry_price=excluded.entry_price,
                    current_price=excluded.current_price,
                    market_value=excluded.market_value,
                    unrealized_pnl=excluded.unrealized_pnl,
                    realized_pnl=excluded.realized_pnl,
                    updated_at=excluded.updated_at
                """,
                (
                    strategy_id,
                    pos["symbol"],
                    pos.get("direction", "long"),
                    pos["quantity"],
                    pos["entry_price"],
                    pos.get("entry_date", ""),
                    pos.get("current_price", 0),
                    pos.get("market_value", 0),
                    pos.get("unrealized_pnl", 0),
                    pos.get("realized_pnl", 0),
                    now,
                ),
            )

    def delete_position(self, strategy_id: str, symbol: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM paper_positions WHERE strategy_id=? AND symbol=?",
                (strategy_id, symbol),
            )

    def load_positions(self, strategy_id: str) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM paper_positions WHERE strategy_id=? ORDER BY symbol",
                (strategy_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # 订单
    # ------------------------------------------------------------------
    def insert_order(self, order: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO paper_orders
                    (order_id, strategy_id, symbol, side, order_type, quantity,
                     price, signal_id, client_order_id, broker_order_id, status,
                     filled_qty, filled_price, reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status=excluded.status,
                    filled_qty=excluded.filled_qty,
                    filled_price=excluded.filled_price,
                    broker_order_id=excluded.broker_order_id,
                    updated_at=excluded.updated_at
                """,
                (
                    order["order_id"],
                    order["strategy_id"],
                    order["symbol"],
                    order["side"],
                    order.get("order_type", "market"),
                    order["quantity"],
                    order.get("price"),
                    order.get("signal_id", ""),
                    order.get("client_order_id", ""),
                    order.get("broker_order_id", ""),
                    order["status"],
                    order.get("filled_qty", 0),
                    order.get("filled_price", 0),
                    order.get("reason", ""),
                    order.get("created_at", now),
                    now,
                ),
            )

    def update_order_status(
        self,
        order_id: str,
        status: str,
        filled_qty: float = 0,
        filled_price: float = 0,
        broker_order_id: str = "",
    ) -> None:
        with self._cursor() as cur:
            cur.execute(
                """
                UPDATE paper_orders
                SET status=?, filled_qty=?, filled_price=?,
                    broker_order_id=COALESCE(NULLIF(?, ''), broker_order_id),
                    updated_at=?
                WHERE order_id=?
                """,
                (
                    status,
                    filled_qty,
                    filled_price,
                    broker_order_id,
                    datetime.now().isoformat(),
                    order_id,
                ),
            )

    def load_orders(
        self,
        strategy_id: str,
        active_only: bool = False,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM paper_orders WHERE strategy_id=?"
        params: List[Any] = [strategy_id]
        if active_only:
            sql += " AND status IN ('NEW','PENDING_SUBMIT','SUBMITTED','PARTIAL')"
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def load_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM paper_orders WHERE order_id=?", (order_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # ------------------------------------------------------------------
    # 成交
    # ------------------------------------------------------------------
    def insert_trade(self, trade: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO paper_trades
                    (trade_id, order_id, strategy_id, symbol, side, quantity,
                     price, amount, commission, slippage, trade_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade["trade_id"],
                    trade["order_id"],
                    trade["strategy_id"],
                    trade["symbol"],
                    trade["side"],
                    trade["quantity"],
                    trade["price"],
                    trade["amount"],
                    trade.get("commission", 0),
                    trade.get("slippage", 0),
                    trade.get("trade_date", now),
                    now,
                ),
            )

    def load_trades(
        self,
        strategy_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM paper_trades WHERE strategy_id=? ORDER BY trade_date DESC LIMIT ?",
                (strategy_id, limit),
            )
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # 快照（Replay + Equity Curve）
    # ------------------------------------------------------------------
    def insert_snapshot(self, snap: Dict[str, Any]) -> None:
        now = datetime.now().isoformat()
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO paper_snapshots
                    (strategy_id, snapshot_time, cash, position_value, total_value,
                     daily_return, realized_pnl, unrealized_pnl, max_drawdown,
                     bar_timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(strategy_id, snapshot_time) DO UPDATE SET
                    cash=excluded.cash,
                    position_value=excluded.position_value,
                    total_value=excluded.total_value,
                    daily_return=excluded.daily_return,
                    realized_pnl=excluded.realized_pnl,
                    unrealized_pnl=excluded.unrealized_pnl,
                    max_drawdown=excluded.max_drawdown,
                    bar_timestamp=excluded.bar_timestamp
                """,
                (
                    snap["strategy_id"],
                    snap["snapshot_time"],
                    snap["cash"],
                    snap["position_value"],
                    snap["total_value"],
                    snap.get("daily_return", 0),
                    snap.get("realized_pnl", 0),
                    snap.get("unrealized_pnl", 0),
                    snap.get("max_drawdown", 0),
                    snap.get("bar_timestamp", ""),
                    now,
                ),
            )

    def load_snapshots(
        self,
        strategy_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM paper_snapshots WHERE strategy_id=?"
        params: List[Any] = [strategy_id]
        if start_time:
            sql += " AND snapshot_time >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND snapshot_time <= ?"
            params.append(end_time)
        sql += " ORDER BY snapshot_time ASC LIMIT ?"
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # 事件流（Replay Timeline 用，合并订单+成交+快照）
    # ------------------------------------------------------------------
    def load_timeline(
        self,
        strategy_id: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """返回合并后的事件时间线，按时间升序。"""
        events: List[Dict[str, Any]] = []
        with self._cursor() as cur:
            cur.execute(
                """SELECT order_id, symbol, side, status, filled_qty, filled_price,
                          created_at AS ts, 'order' AS event_type
                   FROM paper_orders WHERE strategy_id=? ORDER BY created_at ASC""",
                (strategy_id,),
            )
            for r in cur.fetchall():
                events.append(dict(r))
            cur.execute(
                """SELECT trade_id, order_id, symbol, side, quantity, price,
                          amount, commission, trade_date AS ts, 'trade' AS event_type
                   FROM paper_trades WHERE strategy_id=? ORDER BY trade_date ASC""",
                (strategy_id,),
            )
            for r in cur.fetchall():
                events.append(dict(r))
            cur.execute(
                """SELECT snapshot_time AS ts, total_value, cash, daily_return,
                          realized_pnl, unrealized_pnl, max_drawdown, 'snapshot' AS event_type
                   FROM paper_snapshots WHERE strategy_id=? ORDER BY snapshot_time ASC""",
                (strategy_id,),
            )
            for r in cur.fetchall():
                events.append(dict(r))
        events.sort(key=lambda e: e.get("ts", ""))
        if limit and len(events) > limit:
            events = events[-limit:]
        return events


# ----------------------------------------------------------------------
# 单例
# ----------------------------------------------------------------------
_persistence: Optional[TradingPersistence] = None


def get_trading_persistence(
    db_path: str = DEFAULT_DB_PATH,
) -> TradingPersistence:
    """获取 TradingPersistence 单例（线程安全）。"""
    global _persistence
    with threading.Lock():
        if _persistence is None:
            _persistence = TradingPersistence(db_path)
        return _persistence
