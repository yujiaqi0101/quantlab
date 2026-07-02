"""
Trading Studio 测试套件
=======================

覆盖范围：
    1. Persistence — 5 张 paper_* 表 CRUD
    2. Service — 会话管理（创建/启动/停止/删除/状态）
    3. API 路由 — 注册验证 + 端点响应

运行命令：
    python -X utf8 -m pytest tests/test_trading_studio.py -v
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from typing import Dict, Any

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.trading_core.persistence import TradingPersistence
from quantlab.api.trading_service import TradingStudioService
from quantlab.api.trading import router


# ======================================================================
# Fixture：临时数据库
# ======================================================================
@pytest.fixture
def tmp_db(tmp_path) -> str:
    return str(tmp_path / "test_trading.db")


@pytest.fixture
def persistence(tmp_db) -> TradingPersistence:
    return TradingPersistence(db_path=tmp_db)


@pytest.fixture
def service(persistence) -> TradingStudioService:
    return TradingStudioService(persistence=persistence)


# ======================================================================
# 1. Persistence 层测试
# ======================================================================
class TestPersistence:
    """5 张 paper_* 表 CRUD。"""

    def test_table_creation(self, persistence):
        """建表后应能查询 5 张表。"""
        with persistence._cursor() as cur:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cur.fetchall()}
        for tbl in ("paper_accounts", "paper_positions", "paper_orders",
                     "paper_trades", "paper_snapshots"):
            assert tbl in tables, f"missing table: {tbl}"

    def test_account_crud(self, persistence):
        """账户 upsert/load/list/update_status/delete。"""
        sid = "TEST-ACC-001"
        now = datetime.now().isoformat()
        persistence.save_account({
            "strategy_id": sid,
            "strategy_name": "Test Strategy",
            "mode": "paper",
            "initial_capital": 1_000_000,
            "cash": 1_000_000,
            "total_value": 1_000_000,
            "started_at": now,
        })
        acc = persistence.load_account(sid)
        assert acc is not None
        assert acc["strategy_id"] == sid
        assert acc["mode"] == "paper"
        assert acc["cash"] == 1_000_000

        # list
        accounts = persistence.list_accounts()
        assert any(a["strategy_id"] == sid for a in accounts)

        # update status
        persistence.update_account_status(sid, "running")
        acc = persistence.load_account(sid)
        assert acc["status"] == "running"

        # delete
        persistence.delete_account(sid)
        assert persistence.load_account(sid) is None

    def test_position_upsert(self, persistence):
        """持仓 upsert/load/delete。"""
        sid = "TEST-POS-001"
        persistence.save_account({
            "strategy_id": sid, "strategy_name": "T", "mode": "paper",
            "initial_capital": 100000, "cash": 100000,
            "total_value": 100000, "started_at": datetime.now().isoformat(),
        })
        persistence.upsert_position(sid, {
            "symbol": "000001",
            "direction": "long",
            "quantity": 100,
            "entry_price": 10.0,
            "entry_date": datetime.now().isoformat(),
            "current_price": 11.0,
            "market_value": 1100,
            "unrealized_pnl": 100,
        })
        positions = persistence.load_positions(sid)
        assert len(positions) == 1
        assert positions[0]["symbol"] == "000001"
        assert positions[0]["quantity"] == 100

        # update
        persistence.upsert_position(sid, {
            "symbol": "000001", "quantity": 200, "entry_price": 10.0,
            "entry_date": "", "current_price": 12.0, "market_value": 2400,
            "unrealized_pnl": 400,
        })
        positions = persistence.load_positions(sid)
        assert positions[0]["quantity"] == 200

        # delete
        persistence.delete_position(sid, "000001")
        assert len(persistence.load_positions(sid)) == 0

    def test_order_insert(self, persistence):
        """订单 insert/load/update_status。"""
        sid = "TEST-ORD-001"
        persistence.save_account({
            "strategy_id": sid, "strategy_name": "T", "mode": "paper",
            "initial_capital": 100000, "cash": 100000,
            "total_value": 100000, "started_at": datetime.now().isoformat(),
        })
        persistence.insert_order({
            "order_id": "ORD-001",
            "strategy_id": sid,
            "symbol": "000001",
            "side": "buy",
            "order_type": "market",
            "quantity": 100,
            "price": 10.0,
            "status": "SUBMITTED",
        })
        orders = persistence.load_orders(sid)
        assert len(orders) == 1
        assert orders[0]["order_id"] == "ORD-001"
        assert orders[0]["status"] == "SUBMITTED"

        # update status
        persistence.update_order_status("ORD-001", "FILLED", 100, 10.05)
        order = persistence.load_order("ORD-001")
        assert order["status"] == "FILLED"
        assert order["filled_qty"] == 100

        # active_only filter
        persistence.insert_order({
            "order_id": "ORD-002", "strategy_id": sid, "symbol": "000002",
            "side": "sell", "quantity": 50, "status": "NEW",
        })
        active = persistence.load_orders(sid, active_only=True)
        assert len(active) == 1  # only NEW

    def test_trade_insert(self, persistence):
        """成交 insert/load。"""
        sid = "TEST-TRD-001"
        persistence.save_account({
            "strategy_id": sid, "strategy_name": "T", "mode": "paper",
            "initial_capital": 100000, "cash": 100000,
            "total_value": 100000, "started_at": datetime.now().isoformat(),
        })
        persistence.insert_order({
            "order_id": "ORD-T1", "strategy_id": sid, "symbol": "000001",
            "side": "buy", "quantity": 100, "status": "FILLED",
        })
        persistence.insert_trade({
            "trade_id": "TRD-001",
            "order_id": "ORD-T1",
            "strategy_id": sid,
            "symbol": "000001",
            "side": "buy",
            "quantity": 100,
            "price": 10.05,
            "amount": 1005,
            "commission": 0.3,
        })
        trades = persistence.load_trades(sid)
        assert len(trades) == 1
        assert trades[0]["trade_id"] == "TRD-001"
        assert trades[0]["price"] == 10.05

    def test_snapshot_insert(self, persistence):
        """快照 insert/load。"""
        sid = "TEST-SNP-001"
        persistence.save_account({
            "strategy_id": sid, "strategy_name": "T", "mode": "paper",
            "initial_capital": 100000, "cash": 100000,
            "total_value": 100000, "started_at": datetime.now().isoformat(),
        })
        persistence.insert_snapshot({
            "strategy_id": sid,
            "snapshot_time": "2026-07-02T10:00:00",
            "cash": 99000,
            "position_value": 11000,
            "total_value": 110000,
            "daily_return": 0.1,
            "realized_pnl": 0,
            "unrealized_pnl": 1000,
            "max_drawdown": 0,
        })
        snaps = persistence.load_snapshots(sid)
        assert len(snaps) == 1
        assert snaps[0]["total_value"] == 110000


# ======================================================================
# 2. Service 层测试
# ======================================================================
class TestTradingService:
    """会话管理 + 数据查询。"""

    def test_create_session(self, service):
        """创建 paper 会话。"""
        meta = service.create_session(
            mode="paper",
            strategy_id="rsi",
            strategy_name="RSI Strategy",
            initial_capital=500_000,
            symbols=["000001", "000002"],
        )
        assert meta["mode"] == "paper"
        assert meta["strategy_id"]  # sid generated
        assert meta["strategy_name"] == "RSI Strategy"
        assert meta["initial_capital"] == 500_000
        assert meta["status"] == "created"
        # 内存有 core
        assert meta["sid"] in service._sessions

    def test_create_invalid_mode(self, service):
        """非法 mode 应报错。"""
        with pytest.raises(ValueError):
            service.create_session(mode="invalid")

    def test_session_lifecycle(self, service):
        """created → running → paused → running → stopped。"""
        meta = service.create_session(mode="paper")
        sid = meta["sid"]

        # start
        status = service.start_session(sid)
        assert status["status"] == "running"

        # pause
        status = service.pause_session(sid)
        assert status["status"] == "paused"

        # resume
        status = service.resume_session(sid)
        assert status["status"] == "running"

        # stop
        status = service.stop_session(sid)
        assert status["status"] == "stopped"
        assert sid not in service._sessions  # removed from memory

    def test_delete_session(self, service):
        """删除会话后 DB 也清除。"""
        meta = service.create_session(mode="paper")
        sid = meta["sid"]
        assert service.delete_session(sid) is True
        assert sid not in service._meta
        assert service.persistence.load_account(sid) is None

    def test_list_sessions(self, service):
        """列出会话。"""
        service.create_session(mode="paper", strategy_id="s1")
        service.create_session(mode="paper", strategy_id="s2")
        sessions = service.list_sessions()
        assert len(sessions) >= 2

    def test_get_status_not_found(self, service):
        """未知名 sid 返回 not_found。"""
        status = service.get_session_status("NONEXIST")
        assert status["status"] == "not_found"


# ======================================================================
# 3. API 路由测试
# ======================================================================
class TestAPIRoutes:
    """路由注册 + 端点路径验证。"""

    def test_router_prefix(self):
        """路由前缀 = /api/v1/trading。"""
        assert router.prefix == "/api/v1/trading"

    def test_routes_registered(self):
        """关键端点已注册。"""
        paths = {r.path for r in router.routes}
        # 会话管理（路径含完整前缀）
        assert "/api/v1/trading/sessions" in paths
        # 策略库
        assert "/api/v1/trading/strategies" in paths

    def test_route_count(self):
        """路由数 >= 20。"""
        assert len(router.routes) >= 20

    def test_session_endpoints_have_sid(self):
        """带 sid 的端点路径正确。"""
        paths = {r.path for r in router.routes}
        sid_paths = [p for p in paths if "{sid}" in p]
        assert len(sid_paths) > 0  # 至少有 /sessions/{sid}/...


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
