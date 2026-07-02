"""
Replay Engine — 时间机器
========================

从 paper_snapshots + paper_orders + paper_trades 重建任意时间点的完整状态。

核心能力：
    - get_timeline(strategy_id): 返回所有事件时间点（订单/成交/快照）
    - get_snapshot(strategy_id, time): 返回指定时间的完整状态快照
    - restore_to(strategy_id, time): 恢复到指定时间点（返回重建后的状态）

重建逻辑：
    1. 找到 <= time 的最近一个 snapshot 作为基准
    2. 回放该 snapshot 之后到 time 之间的所有 trade 事件
    3. 重算账户/持仓/PnL
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .persistence import TradingPersistence, get_trading_persistence

logger = logging.getLogger("quantlab.trading_core.replay")


class ReplayEngine:
    """时间机器：从历史数据重建任意时间点状态。"""

    def __init__(
        self,
        persistence: Optional[TradingPersistence] = None,
    ) -> None:
        self.persistence = persistence or get_trading_persistence()

    # ------------------------------------------------------------------
    # 时间线
    # ------------------------------------------------------------------
    def get_timeline(
        self,
        strategy_id: str,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """返回所有事件时间点，按时间升序。

        每个事件包含：
            - ts: 时间戳
            - event_type: order / trade / snapshot
            - 其他字段根据事件类型不同
        """
        events = self.persistence.load_timeline(strategy_id, limit=limit)
        # 标注是否可恢复
        for e in events:
            e["restorable"] = True
        return events

    # ------------------------------------------------------------------
    # 单点快照
    # ------------------------------------------------------------------
    def get_snapshot(
        self,
        strategy_id: str,
        time: str,
    ) -> Dict[str, Any]:
        """返回指定时间的完整状态。

        Args:
            strategy_id: 策略ID
            time: ISO 格式时间字符串

        Returns:
            {
                "time": time,
                "account": {...},
                "positions": [...],
                "orders": [...],
                "trades": [...],
                "equity_point": {...},
            }
        """
        account = self.persistence.load_account(strategy_id)
        if account is None:
            return {
                "time": time,
                "account": None,
                "positions": [],
                "orders": [],
                "trades": [],
                "equity_point": None,
                "error": "session not found",
            }

        # 找到 <= time 的最近快照
        snaps = self.persistence.load_snapshots(strategy_id, end_time=time, limit=1)
        base_snap = snaps[-1] if snaps else None

        # 该时间点之前的所有订单/成交
        orders = self.persistence.load_orders(strategy_id, limit=1000)
        orders_before = [o for o in orders if o.get("created_at", "") <= time]

        trades = self.persistence.load_trades(strategy_id, limit=1000)
        trades_before = [t for t in trades if t.get("trade_date", "") <= time]

        # 持仓：基于最近快照 + 之后到 time 的成交重算
        positions = self._rebuild_positions(strategy_id, trades_before)

        # 账户：基于快照 + 之后成交的 PnL 重算
        equity_point = self._build_equity_point(base_snap, trades_before, account)

        return {
            "time": time,
            "account": {
                "strategy_id": strategy_id,
                "mode": account.get("mode", "paper"),
                "initial_capital": account.get("initial_capital", 0),
                "cash": equity_point.get("cash", 0),
                "total_value": equity_point.get("total_value", 0),
                "status": account.get("status", "stopped"),
            },
            "positions": positions,
            "orders": orders_before,
            "trades": trades_before,
            "equity_point": equity_point,
            "base_snapshot": base_snap,
        }

    # ------------------------------------------------------------------
    # 恢复
    # ------------------------------------------------------------------
    def restore_to(
        self,
        strategy_id: str,
        time: str,
    ) -> Dict[str, Any]:
        """恢复到指定时间点（返回重建后的完整状态）。

        与 get_snapshot 的区别：restore_to 用于"切换 Replay 视图到该时间点"，
        会额外返回恢复后的 Equity Curve（截至该时间点）。

        Args:
            strategy_id: 策略ID
            time: ISO 格式时间字符串

        Returns:
            {
                "time": time,
                "state": {完整状态},
                "equity_curve": [截至该时间点的净值序列],
            }
        """
        state = self.get_snapshot(strategy_id, time)

        # Equity Curve：截至该时间点的所有快照
        snaps = self.persistence.load_snapshots(
            strategy_id, end_time=time, limit=10000
        )
        equity_curve = [
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

        return {
            "time": time,
            "state": state,
            "equity_curve": equity_curve,
            "timeline_events_before": len(
                [e for e in self.get_timeline(strategy_id) if e.get("ts", "") <= time]
            ),
        }

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _rebuild_positions(
        self,
        strategy_id: str,
        trades: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """根据成交记录重建持仓。"""
        positions: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            sym = t["symbol"]
            side = t["side"].upper()
            qty = float(t["quantity"])
            price = float(t["price"])

            if sym not in positions:
                positions[sym] = {
                    "symbol": sym,
                    "direction": "long",
                    "quantity": 0.0,
                    "entry_price": 0.0,
                    "entry_date": t.get("trade_date", ""),
                    "current_price": price,
                    "market_value": 0.0,
                    "unrealized_pnl": 0.0,
                    "realized_pnl": 0.0,
                }

            pos = positions[sym]
            if side == "BUY":
                # 加仓
                total_cost = pos["entry_price"] * pos["quantity"] + price * qty
                pos["quantity"] += qty
                pos["entry_price"] = (
                    total_cost / pos["quantity"] if pos["quantity"] != 0 else 0
                )
            else:
                # 减仓
                if pos["quantity"] > 0:
                    realized = (price - pos["entry_price"]) * min(qty, pos["quantity"])
                    pos["realized_pnl"] += realized
                pos["quantity"] -= qty
                if abs(pos["quantity"]) < 1e-9:
                    pos["quantity"] = 0.0
                    pos["entry_price"] = 0.0

            pos["current_price"] = price
            pos["market_value"] = pos["quantity"] * price
            pos["unrealized_pnl"] = (
                (price - pos["entry_price"]) * pos["quantity"]
                if pos["quantity"] != 0
                else 0.0
            )
            pos["direction"] = "long" if pos["quantity"] >= 0 else "short"

        # 过滤掉已平仓且 quantity=0 的持仓
        return [p for p in positions.values() if abs(p["quantity"]) > 1e-9]

    def _build_equity_point(
        self,
        base_snap: Optional[Dict[str, Any]],
        trades: List[Dict[str, Any]],
        account: Dict[str, Any],
    ) -> Dict[str, Any]:
        """基于基准快照 + 成交重算净值点。"""
        if base_snap:
            cash = float(base_snap["cash"])
            total_value = float(base_snap["total_value"])
            realized_pnl = float(base_snap.get("realized_pnl", 0))
            unrealized_pnl = float(base_snap.get("unrealized_pnl", 0))
            max_drawdown = float(base_snap.get("max_drawdown", 0))
        else:
            cash = float(account.get("initial_capital", 0))
            total_value = cash
            realized_pnl = 0.0
            unrealized_pnl = 0.0
            max_drawdown = 0.0

        # 累加基准之后的成交对手续费影响
        for t in trades:
            commission = float(t.get("commission", 0))
            cash -= commission
            total_value -= commission

        return {
            "cash": cash,
            "total_value": total_value,
            "realized_pnl": realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "max_drawdown": max_drawdown,
            "daily_return": 0.0,
        }
