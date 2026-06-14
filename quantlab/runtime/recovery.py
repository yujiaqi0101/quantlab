"""
RecoveryManager：启动恢复（V3.3 第三件事）

boot 流程：
    1) 读 CheckpointManager.latest()
    2) 拿到 StateSnapshot
    3) restore 到 portfolio / broker / tradebook
    4) 主循环从 snapshot.timestamp 之后继续

restore 内容：
    portfolio.cash         ← snap.cash
    portfolio.positions    ← snap.positions
    broker.positions       ← snap.positions
    broker.cash            ← snap.cash
    tradebook.closed_trades ← snap.closed_trades
    metrics  ← snap.metrics_snapshot
"""

from __future__ import annotations

import logging
from typing import Optional

from .state_store import StateSnapshot
from .checkpoint import CheckpointManager


logger = logging.getLogger("quantlab.recovery")


class RecoveryManager:
    """
    V3.3 启动恢复

    用法：
        cm = CheckpointManager(strategy="by_ticks", interval=100)
        rec = RecoveryManager(checkpoint_manager=cm)
        snapshot = rec.boot()
        if snapshot is not None:
            portfolio = rec.restore_portfolio(snapshot, initial_cash=100000)
        else:
            portfolio = Portfolio(initial_cash=100000)   # fresh
    """

    def __init__(self, checkpoint_manager: CheckpointManager):
        self.cm = checkpoint_manager

    def boot(self) -> Optional[StateSnapshot]:
        """读最新 checkpoint；没有返回 None"""
        snap = self.cm.latest()
        if snap is None:
            logger.info("no checkpoint found, fresh start")
            return None
        logger.info(
            f"recovered checkpoint v{snap.version} "
            f"from {snap.timestamp} "
            f"(equity={snap.equity:.2f})"
        )
        return snap

    def restore_portfolio(
        self,
        snap: StateSnapshot,
        portfolio,                       # Portfolio 实例
    ):
        """把 snapshot 状态灌回 portfolio"""
        portfolio.cash = snap.cash
        # 清空 positions
        portfolio.positions.clear()
        # 重建 Position
        from ..core.position import Position
        for s, p in snap.positions.items():
            pos = Position(symbol=s)
            pos.qty = p.get("qty", 0)
            pos.avg_price = p.get("avg_price", 0.0)
            pos.realized_pnl = p.get("realized_pnl", 0.0)
            portfolio.positions[s] = pos
        # 同步 last_prices
        if hasattr(portfolio, "last_prices"):
            portfolio.last_prices.clear()
            portfolio.last_prices.update(snap.last_prices)
        return portfolio

    def restore_broker(
        self,
        snap: StateSnapshot,
        broker,
    ):
        """
        V3.3 恢复 broker

        关键：cash 和 positions 必须和 portfolio 一致（一致性 check 的前提）
        """
        if hasattr(broker, "cash"):
            broker.cash = snap.cash
        if hasattr(broker, "positions"):
            broker.positions.clear()
            for s, p in snap.positions.items():
                broker.positions[s] = p.get("qty", 0)
        if hasattr(broker, "_last_prices"):
            broker._last_prices.clear()
            broker._last_prices.update(snap.last_prices)
        return broker

    def restore_tradebook(
        self,
        snap: StateSnapshot,
        tradebook,
    ):
        """tradebook 没法直接恢复（没有公开 API），先 best-effort"""
        # 简化：tradebook 内部是 append-only，可加 reset 接口
        if hasattr(tradebook, "trades"):
            tradebook.trades.clear()
        return tradebook

    def restore_metrics(
        self,
        snap: StateSnapshot,
        metrics,
    ):
        """从 snapshot 恢复指标"""
        ms = snap.metrics_snapshot or {}
        for k, v in ms.items():
            if hasattr(metrics, k):
                setattr(metrics, k, v)
        return metrics
