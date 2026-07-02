"""
Trading Studio Service
======================

协调 TradingCore + Persistence + ReplayEngine，对接 API 层。

职责：
    - 管理内存中的活跃会话（TradingCore 实例）
    - 创建/启动/暂停/停止会话
    - 状态同步到 persistence（落库）
    - 提供 9 个 Workspace 的数据查询
    - 手动下单/撤单/Kill Switch
    - Replay 查询

会话生命周期：
    created → running → paused → running → stopped
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..execution.core.oms import OrderSide, OrderType
from ..execution.strategy_registry import get_registry
from ..trading_core.core import TradingCore
from ..trading_core.interfaces import OrderIntent
from ..trading_core.modes import PaperMode
from ..trading_core.persistence import TradingPersistence, get_trading_persistence
from ..trading_core.replay import ReplayEngine

logger = logging.getLogger("quantlab.api.trading_service")


class TradingStudioService:
    """Trading Studio 后端服务（单例）。"""

    def __init__(
        self,
        persistence: Optional[TradingPersistence] = None,
    ) -> None:
        self.persistence = persistence or get_trading_persistence()
        self.replay = ReplayEngine(self.persistence)
        # 内存活跃会话 {sid: TradingCore}
        self._sessions: Dict[str, TradingCore] = {}
        # 会话元数据 {sid: {...}}
        self._meta: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # 会话管理
    # ------------------------------------------------------------------
    def list_sessions(
        self,
        mode: Optional[str] = None,
        include_stopped: bool = True,
    ) -> List[Dict[str, Any]]:
        """列出所有会话（合并内存 + DB）。"""
        # 从 DB 加载（含历史）
        accounts = self.persistence.list_accounts()
        seen = set()
        result: List[Dict[str, Any]] = []
        for acc in accounts:
            sid = acc["strategy_id"]
            seen.add(sid)
            # 内存覆盖（实时状态）
            if sid in self._sessions:
                acc["is_active"] = True
                acc["status"] = self._meta.get(sid, {}).get("status", "running")
            else:
                acc["is_active"] = False
                if not include_stopped and acc.get("status") == "stopped":
                    continue
            if mode and acc.get("mode") != mode:
                continue
            result.append(acc)
        return result

    def create_session(
        self,
        mode: str = "paper",
        strategy_id: str = "",
        strategy_name: str = "",
        initial_capital: float = 1_000_000,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建新会话。

        Args:
            mode: paper / live / replay
            strategy_id: 策略ID（可选，用于关联策略元信息）
            strategy_name: 策略显示名
            initial_capital: 初始资金
            symbols: 交易标的列表

        Returns:
            会话信息字典
        """
        if mode not in ("paper", "live", "replay"):
            raise ValueError(f"unsupported mode: {mode}")
        if mode == "live":
            logger.warning("Live mode is not fully supported yet, falling back to paper skeleton")

        sid = f"TS-{mode.upper()[:3]}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        symbols = symbols or []

        # 创建 TradingCore（replay 模式不创建 core，仅查询历史）
        core: Optional[TradingCore] = None
        if mode != "replay":
            paper_mode = PaperMode()
            core = TradingCore(
                mode=paper_mode,
                initial_capital=initial_capital,
            )
            self._sessions[sid] = core

        # 元数据
        meta = {
            "sid": sid,
            "mode": mode,
            "strategy_id": strategy_id,
            "strategy_name": strategy_name or strategy_id or "Manual Session",
            "initial_capital": initial_capital,
            "symbols": symbols,
            "status": "created",
            "started_at": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
        }
        self._meta[sid] = meta

        # 落库
        self.persistence.save_account(
            {
                "strategy_id": sid,
                "strategy_name": meta["strategy_name"],
                "version": "1.0",
                "mode": mode,
                "initial_capital": initial_capital,
                "cash": initial_capital,
                "frozen_cash": 0,
                "total_value": initial_capital,
                "peak_value": initial_capital,
                "status": "created",
                "started_at": meta["started_at"],
            }
        )

        logger.info(f"Session created: {sid} (mode={mode}, capital={initial_capital})")
        return meta

    def start_session(self, sid: str) -> Dict[str, Any]:
        """启动会话。"""
        self._require_session(sid)
        meta = self._meta.setdefault(sid, {})
        meta["status"] = "running"
        self.persistence.update_account_status(sid, "running")
        logger.info(f"Session started: {sid}")
        return self.get_session_status(sid)

    def pause_session(self, sid: str) -> Dict[str, Any]:
        self._require_session(sid)
        self._meta.setdefault(sid, {})["status"] = "paused"
        self.persistence.update_account_status(sid, "paused")
        return self.get_session_status(sid)

    def resume_session(self, sid: str) -> Dict[str, Any]:
        self._require_session(sid)
        self._meta.setdefault(sid, {})["status"] = "running"
        self.persistence.update_account_status(sid, "running")
        return self.get_session_status(sid)

    def stop_session(self, sid: str) -> Dict[str, Any]:
        self._require_session(sid)
        self._meta.setdefault(sid, {})["status"] = "stopped"
        self.persistence.update_account_status(sid, "stopped")
        # 从内存移除
        self._sessions.pop(sid, None)
        logger.info(f"Session stopped: {sid}")
        return self.get_session_status(sid)

    def delete_session(self, sid: str) -> bool:
        self._sessions.pop(sid, None)
        self._meta.pop(sid, None)
        self.persistence.delete_account(sid)
        logger.info(f"Session deleted: {sid}")
        return True

    def get_session_status(self, sid: str) -> Dict[str, Any]:
        """获取会话运行时状态。"""
        meta = self._meta.get(sid, {})
        account = self.persistence.load_account(sid)
        if account is None:
            return {"sid": sid, "status": "not_found"}
        core = self._sessions.get(sid)
        is_active = core is not None
        return {
            "sid": sid,
            "mode": account.get("mode", "paper"),
            "strategy_id": account.get("strategy_id", ""),
            "strategy_name": account.get("strategy_name", ""),
            "status": meta.get("status", account.get("status", "stopped")),
            "is_active": is_active,
            "initial_capital": account.get("initial_capital", 0),
            "cash": account.get("cash", 0),
            "total_value": account.get("total_value", 0),
            "started_at": account.get("started_at", ""),
        }

    # ------------------------------------------------------------------
    # 数据查询（9 个 Workspace）
    # ------------------------------------------------------------------
    def get_overview(self, sid: str) -> Dict[str, Any]:
        """Overview：今日收益/PnL/Cash/Exposure/Sharpe/Drawdown。"""
        core = self._sessions.get(sid)
        if core is not None:
            acct = core.get_account()
            orders = core.get_orders()
            positions = core.get_positions()
        else:
            acct = self._account_from_db(sid)
            orders = self.persistence.load_orders(sid, limit=1000)
            positions = self.persistence.load_positions(sid)

        initial = acct.get("initial_capital", 0)
        equity = acct.get("equity", acct.get("total_value", 0))
        total_pnl = equity - initial
        total_return = (total_pnl / initial) if initial > 0 else 0.0

        return {
            "sid": sid,
            "today_return": total_return,
            "today_pnl": total_pnl,
            "total_pnl": total_pnl,
            "cash": acct.get("cash", 0),
            "equity": equity,
            "exposure": acct.get("exposure", 0),
            "invested_value": acct.get("invested_value", 0),
            "realized_pnl": acct.get("realized_pnl", 0),
            "unrealized_pnl": acct.get("unrealized_pnl", 0),
            "max_drawdown": acct.get("max_drawdown", 0),
            "current_drawdown": acct.get("current_drawdown", 0),
            "sharpe": 0.0,  # TODO: 计算 Sharpe（需要更多历史数据）
            "n_positions": len(positions),
            "n_orders": len(orders),
            "n_open_orders": len([o for o in orders if o.get("state", o.get("status", "")) in ("NEW", "SUBMITTED", "PARTIAL")]),
        }

    def get_market(
        self,
        sid: str,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Market：行情数据。"""
        meta = self._meta.get(sid, {})
        target_symbols = symbols or meta.get("symbols", [])
        core = self._sessions.get(sid)
        quotes: List[Dict[str, Any]] = []
        if core is not None:
            for sym in target_symbols:
                price = core._latest_prices.get(sym, 0)
                quotes.append({
                    "symbol": sym,
                    "last": price,
                    "change_pct": 0.0,
                    "volume": 0,
                    "bid": price,
                    "ask": price,
                })
        return {"sid": sid, "symbols": target_symbols, "quotes": quotes}

    def get_signals(
        self,
        sid: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Signals：从订单中提取信号（每个订单关联 signal_id）。"""
        orders = self.persistence.load_orders(sid, limit=limit)
        signals: List[Dict[str, Any]] = []
        for o in orders:
            if o.get("signal_id"):
                signals.append({
                    "signal_id": o["signal_id"],
                    "time": o.get("created_at", ""),
                    "symbol": o["symbol"],
                    "direction": o["side"],
                    "score": 0.0,
                    "confidence": 0.0,
                    "reason": o.get("reason", ""),
                    "status": o.get("status", ""),
                    "order_id": o["order_id"],
                })
        return signals

    def get_orders(
        self,
        sid: str,
        status: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """Orders：订单列表。"""
        orders = self.persistence.load_orders(sid, limit=limit)
        if status:
            orders = [o for o in orders if o.get("status", "").upper() == status.upper()]
        return orders

    def get_positions(self, sid: str) -> List[Dict[str, Any]]:
        """Positions：持仓列表。"""
        core = self._sessions.get(sid)
        if core is not None:
            return core.get_positions()
        return self.persistence.load_positions(sid)

    def get_portfolio(self, sid: str) -> Dict[str, Any]:
        """Portfolio：组合分析。"""
        core = self._sessions.get(sid)
        if core is not None:
            acct = core.get_account()
            positions = core.get_positions()
        else:
            acct = self._account_from_db(sid)
            positions = self.persistence.load_positions(sid)

        # 持仓权重
        equity = acct.get("equity", acct.get("total_value", 0))
        weights = []
        for p in positions:
            sym = p.get("symbol", "")
            mv = abs(float(p.get("market_value", p.get("market_value", 0))))
            w = (mv / equity) if equity > 0 else 0
            weights.append({"symbol": sym, "weight": w, "market_value": mv})

        return {
            "sid": sid,
            "total_equity": equity,
            "cash": acct.get("cash", 0),
            "invested": acct.get("invested_value", 0),
            "exposure": acct.get("exposure", 0),
            "leverage": 0.0,
            "weights": weights,
            "n_positions": len(positions),
        }

    def get_risk(self, sid: str) -> Dict[str, Any]:
        """Risk：风险指标。"""
        core = self._sessions.get(sid)
        if core is not None:
            acct = core.get_account()
        else:
            acct = self._account_from_db(sid)
        positions = self.get_positions(sid)

        # 集中度（最大持仓占比）
        equity = acct.get("equity", acct.get("total_value", 0))
        max_concentration = 0.0
        for p in positions:
            mv = abs(float(p.get("market_value", 0)))
            if equity > 0:
                max_concentration = max(max_concentration, mv / equity)

        return {
            "sid": sid,
            "var_95": 0.0,  # TODO: VaR 计算
            "max_drawdown": acct.get("max_drawdown", 0),
            "current_drawdown": acct.get("current_drawdown", 0),
            "turnover": 0.0,  # TODO: 换手率
            "concentration": max_concentration,
            "exposure": acct.get("exposure", 0),
            "beta": 1.0,  # TODO: Beta
            "n_positions": len(positions),
        }

    def get_journal(
        self,
        sid: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Journal：交易日志（从成交记录生成）。"""
        trades = self.persistence.load_trades(sid, limit=limit)
        orders = {o["order_id"]: o for o in self.persistence.load_orders(sid, limit=1000)}
        journal = []
        for t in trades:
            order = orders.get(t.get("order_id", ""), {})
            journal.append({
                "time": t.get("trade_date", ""),
                "type": "trade",
                "symbol": t.get("symbol", ""),
                "side": t.get("side", ""),
                "quantity": t.get("quantity", 0),
                "price": t.get("price", 0),
                "amount": t.get("amount", 0),
                "commission": t.get("commission", 0),
                "slippage": t.get("slippage", 0),
                "reason": order.get("reason", ""),
                "order_id": t.get("order_id", ""),
                "trade_id": t.get("trade_id", ""),
            })
        return journal

    def get_equity_curve(
        self,
        sid: str,
        points: int = 500,
    ) -> List[Dict[str, Any]]:
        """Equity Curve：净值曲线。"""
        snaps = self.persistence.load_snapshots(sid, limit=points)
        return [
            {
                "time": s["snapshot_time"],
                "total_value": s["total_value"],
                "cash": s["cash"],
                "daily_return": s.get("daily_return", 0),
                "realized_pnl": s.get("realized_pnl", 0),
                "unrealized_pnl": s.get("unrealized_pnl", 0),
                "max_drawdown": s.get("max_drawdown", 0),
            }
            for s in snaps
        ]

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def manual_order(
        self,
        sid: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """手动下单。"""
        core = self._require_active_session(sid)
        side = side.upper()
        if side not in ("BUY", "SELL"):
            raise ValueError(f"invalid side: {side}")

        # 确保有市场价格
        if price is not None and price > 0:
            core._latest_prices[symbol] = price
            core.broker.update_market_prices({symbol: price})
            core.portfolio_book.update_prices({symbol: price})
        elif symbol not in core._latest_prices:
            raise ValueError(f"no market price for {symbol}, please provide price")

        intent = OrderIntent(
            symbol=symbol,
            side=side.lower(),
            quantity=quantity,
            order_type=order_type.lower(),
            price=price,
            reason=reason or "manual_order",
        )

        oms_order = core._submit_intent(self._meta[sid].get("strategy_id", sid), intent)
        if oms_order is None:
            raise RuntimeError("order submission failed (OMS rejected)")

        # 落库
        order_dict = oms_order.to_dict()
        self.persistence.insert_order({
            "order_id": oms_order.id,
            "strategy_id": sid,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "signal_id": f"manual-{uuid.uuid4().hex[:8]}",
            "client_order_id": oms_order.client_order_id,
            "broker_order_id": oms_order.broker_order_id,
            "status": oms_order.state.value,
            "filled_qty": oms_order.filled_qty,
            "filled_price": oms_order.avg_fill_price,
            "reason": reason,
        })

        # 如果成交，落库 trade + 更新持仓 + 快照
        if oms_order.state.value == "FILLED":
            fill_price = oms_order.avg_fill_price
            commission = fill_price * quantity * getattr(core.broker, "fee_rate", 0.0)
            slippage = 0.0
            trade_id = f"TRD-{uuid.uuid4().hex[:12]}"
            self.persistence.insert_trade({
                "trade_id": trade_id,
                "order_id": oms_order.id,
                "strategy_id": sid,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": fill_price,
                "amount": fill_price * quantity,
                "commission": commission,
                "slippage": slippage,
                "trade_date": datetime.now().isoformat(),
            })
            # 更新持仓
            self._sync_positions(sid, core)
            # 更新账户 + 快照
            self._sync_account_and_snapshot(sid, core)

        return {
            "order_id": oms_order.id,
            "status": oms_order.state.value,
            "filled_qty": oms_order.filled_qty,
            "filled_price": oms_order.avg_fill_price,
        }

    def cancel_order(self, sid: str, order_id: str) -> Dict[str, Any]:
        """撤单。"""
        core = self._require_active_session(sid)
        ok = core.oms.cancel(order_id)
        new_status = core.oms.get_order(order_id).state.value if core.oms.get_order(order_id) else "UNKNOWN"
        self.persistence.update_order_status(order_id, new_status)
        return {"order_id": order_id, "cancelled": ok, "status": new_status}

    def kill_switch(self, sid: str) -> Dict[str, Any]:
        """触发 Kill Switch：取消所有活动订单 + 停止会话。"""
        core = self._sessions.get(sid)
        cancelled = 0
        if core is not None:
            cancelled = core.oms.cancel_all()
            # 落库所有活动订单状态
            for o in core.oms.get_all_orders():
                if o.state.value == "CANCELLED":
                    self.persistence.update_order_status(o.id, "CANCELLED")
        self.stop_session(sid)
        logger.warning(f"Kill Switch triggered: {sid}, cancelled {cancelled} orders")
        return {
            "sid": sid,
            "kill_switch": True,
            "cancelled_orders": cancelled,
            "status": "stopped",
        }

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------
    def get_replay_timeline(self, sid: str, limit: int = 500) -> List[Dict[str, Any]]:
        return self.replay.get_timeline(sid, limit=limit)

    def get_replay_snapshot(self, sid: str, time_str: str) -> Dict[str, Any]:
        return self.replay.get_snapshot(sid, time_str)

    def restore_replay(self, sid: str, time_str: str) -> Dict[str, Any]:
        return self.replay.restore_to(sid, time_str)

    # ------------------------------------------------------------------
    # 策略库
    # ------------------------------------------------------------------
    def list_strategies(self) -> List[Dict[str, Any]]:
        try:
            reg = get_registry()
            return [s.to_dict() for s in reg.list_strategies(enabled_only=True)]
        except Exception as e:
            logger.warning(f"list_strategies failed: {e}")
            return []

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        try:
            reg = get_registry()
            s = reg.get_strategy(strategy_id)
            return s.to_dict() if s else None
        except Exception as e:
            logger.warning(f"get_strategy failed: {e}")
            return None

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _require_session(self, sid: str) -> None:
        if self.persistence.load_account(sid) is None and sid not in self._sessions:
            raise ValueError(f"session not found: {sid}")

    def _require_active_session(self, sid: str) -> TradingCore:
        core = self._sessions.get(sid)
        if core is None:
            raise ValueError(f"session not active (stopped or replay mode): {sid}")
        if self._meta.get(sid, {}).get("status") != "running":
            raise RuntimeError(f"session not running: {sid}")
        return core

    def _account_from_db(self, sid: str) -> Dict[str, Any]:
        acc = self.persistence.load_account(sid)
        if acc is None:
            return {}
        return {
            "initial_capital": acc.get("initial_capital", 0),
            "cash": acc.get("cash", 0),
            "equity": acc.get("total_value", 0),
            "total_value": acc.get("total_value", 0),
            "invested_value": acc.get("total_value", 0) - acc.get("cash", 0),
            "exposure": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "max_drawdown": 0.0,
            "current_drawdown": 0.0,
        }

    def _sync_positions(self, sid: str, core: TradingCore) -> None:
        """同步内存持仓到 DB。"""
        db_positions = {p["symbol"]: p for p in self.persistence.load_positions(sid)}
        for pos in core.position_book.get_positions():
            entry_date = ""
            if pos.updated_at > 0:
                try:
                    entry_date = datetime.fromtimestamp(pos.updated_at / 1000).strftime("%Y-%m-%d")
                except Exception:
                    pass
            self.persistence.upsert_position(sid, {
                "symbol": pos.symbol,
                "direction": "long" if pos.qty > 0 else "short",
                "quantity": pos.qty,
                "entry_price": pos.avg_price,
                "entry_date": entry_date,
                "current_price": pos.market_price,
                "market_value": pos.market_value,
                "unrealized_pnl": pos.unrealized_pnl,
                "realized_pnl": pos.realized_pnl,
            })
        # 清理已平仓的持仓（内存中 qty=0 但 DB 还有的）
        for sym, p in db_positions.items():
            if sym not in core.position_book.positions:
                self.persistence.delete_position(sid, sym)

    def _sync_account_and_snapshot(self, sid: str, core: TradingCore) -> None:
        """同步账户 + 写入快照。"""
        acct = core.get_account()
        now = datetime.now()
        now_iso = now.isoformat()
        # 更新账户
        self.persistence.save_account({
            "strategy_id": sid,
            "strategy_name": self._meta.get(sid, {}).get("strategy_name", ""),
            "mode": self._meta.get(sid, {}).get("mode", "paper"),
            "initial_capital": acct["initial_capital"],
            "cash": acct["cash"],
            "frozen_cash": 0,
            "total_value": acct["equity"],
            "peak_value": max(acct["equity"], acct.get("initial_capital", 0)),
            "status": self._meta.get(sid, {}).get("status", "running"),
            "started_at": self._meta.get(sid, {}).get("started_at", now_iso),
        })
        # 写入快照
        self.persistence.insert_snapshot({
            "strategy_id": sid,
            "snapshot_time": now_iso,
            "cash": acct["cash"],
            "position_value": acct["invested_value"],
            "total_value": acct["equity"],
            "daily_return": 0.0,
            "realized_pnl": acct.get("realized_pnl", 0),
            "unrealized_pnl": acct.get("unrealized_pnl", 0),
            "max_drawdown": acct.get("max_drawdown", 0),
            "bar_timestamp": now_iso,
        })


# ----------------------------------------------------------------------
# 单例
# ----------------------------------------------------------------------
_service: Optional[TradingStudioService] = None


def get_trading_service() -> TradingStudioService:
    global _service
    if _service is None:
        _service = TradingStudioService()
    return _service
