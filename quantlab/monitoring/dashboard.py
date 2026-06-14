"""
Dashboard：matplotlib 轻量可视化（V3.2）

V3.2 不做 streamlit（依赖重）
改用 matplotlib 多子图：
    subplot 1: Equity Curve
    subplot 2: Drawdown
    subplot 3: Positions
    subplot 4: PnL 分布

API:
    dash = Dashboard(metrics, portfolio, tradebook)
    dash.show()    # plt.show()
    dash.save(path) # savefig
    dash.equity_plot()  # 单独画一个
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd

try:
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


class Dashboard:
    """
    V3.2 简化 Dashboard

    用法：
        dash = Dashboard(
            metrics=metrics_collector,
            portfolio=portfolio,
            tradebook=tradebook,
        )
        dash.show()
        dash.save("dashboard.png")
    """

    def __init__(
        self,
        metrics=None,
        portfolio=None,
        tradebook=None,
    ):
        self.metrics = metrics
        self.portfolio = portfolio
        self.tradebook = tradebook

    # ---- 主面板 ----
    def show(self) -> None:
        if not _HAS_MPL:
            print("matplotlib not installed, skip dashboard")
            return
        fig, axes = plt.subplots(
            2, 2, figsize=(14, 8)
        )
        self._plot_equity(axes[0, 0])
        self._plot_drawdown(axes[0, 1])
        self._plot_positions(axes[1, 0])
        self._plot_pnl_dist(axes[1, 1])
        plt.tight_layout()
        plt.show()

    def save(self, path: str = "dashboard.png") -> None:
        if not _HAS_MPL:
            print("matplotlib not installed, skip")
            return
        os.makedirs(
            os.path.dirname(path) or ".", exist_ok=True
        )
        fig, axes = plt.subplots(
            2, 2, figsize=(14, 8)
        )
        self._plot_equity(axes[0, 0])
        self._plot_drawdown(axes[0, 1])
        self._plot_positions(axes[1, 0])
        self._plot_pnl_dist(axes[1, 1])
        plt.tight_layout()
        plt.savefig(path, dpi=100, bbox_inches="tight")
        plt.close(fig)

    # ---- 单图 ----
    def equity_plot(self, ax=None) -> None:
        if not _HAS_MPL:
            return
        if ax is None:
            _, ax = plt.subplots(figsize=(10, 4))
        self._plot_equity(ax)

    # ---- 子图 ----
    def _plot_equity(self, ax) -> None:
        if self.portfolio is None or not self.portfolio.equity_curve:
            ax.set_title("Equity Curve (no data)")
            return
        ts = self.portfolio.timestamps
        eq = self.portfolio.equity_curve
        if ts is not None and len(ts) == len(eq):
            ax.plot(ts, eq, label="Equity")
        else:
            ax.plot(eq, label="Equity")
        ax.set_title("Equity Curve")
        ax.set_xlabel("Time")
        ax.set_ylabel("Equity")
        ax.grid(True, alpha=0.3)
        ax.legend()

    def _plot_drawdown(self, ax) -> None:
        if self.metrics is None:
            ax.set_title("Drawdown (no metrics)")
            return
        hist = self.metrics.history_df()
        if hist.empty or "drawdown" not in hist.columns:
            ax.set_title("Drawdown (empty)")
            return
        ax.fill_between(
            hist.index,
            hist["drawdown"] * 100,
            0,
            color="red", alpha=0.4,
        )
        ax.set_title("Drawdown %")
        ax.set_ylabel("%")
        ax.grid(True, alpha=0.3)

    def _plot_positions(self, ax) -> None:
        if self.portfolio is None:
            ax.set_title("Positions (no portfolio)")
            return
        # portfolio.positions 是 Dict[symbol, Position]
        positions = getattr(self.portfolio, "positions", None) or {}
        if hasattr(positions, "items") and not positions:
            ax.set_title("Positions (empty)")
            return
        syms = []
        qtys = []
        for s, pos in positions.items():
            qty = (
                pos.qty
                if hasattr(pos, "qty")
                else pos
            )
            if qty == 0:
                continue
            syms.append(s)
            qtys.append(qty)
        if not syms:
            ax.set_title("Positions (empty)")
            return
        colors = [
            "green" if q > 0 else "red" for q in qtys
        ]
        ax.bar(syms, qtys, color=colors)
        ax.axhline(0, color="black", linewidth=0.5)
        ax.set_title("Current Positions")
        ax.set_ylabel("Quantity")
        ax.grid(True, alpha=0.3, axis="y")

    def _plot_pnl_dist(self, ax) -> None:
        if self.tradebook is None:
            ax.set_title("PnL Distribution (no tradebook)")
            return
        pnls = [
            t.pnl for t in self.tradebook.closed_trades
        ]
        if not pnls:
            ax.set_title("PnL Distribution (empty)")
            return
        ax.hist(pnls, bins=20, color="steelblue", alpha=0.7)
        ax.axvline(0, color="red", linestyle="--", linewidth=0.7)
        ax.set_title("Trade PnL Distribution")
        ax.set_xlabel("PnL")
        ax.set_ylabel("Count")
        ax.grid(True, alpha=0.3)
