"""
Trade Analytics — 交易分析

在成交数据上计算：
  - win_rate           胜率
  - profit_factor      盈亏比（总盈利 / 总亏损）
  - expectancy         期望值（每笔预期收益）
  - avg_win            平均盈利
  - avg_loss           平均亏损
  - long_win_rate      多头胜率
  - short_win_rate     空头胜率
  - max_consecutive_win   最大连胜
  - max_consecutive_loss  最大连亏

输入：trades 列表，每个 trade 是 dict：
  {
    "pnl": float,
    "side": "LONG"/"SHORT",
    "symbol": str,
  }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("quantlab.execution.observe.trade_analytics")


@dataclass
class TradeAnalyticsReport:
    """交易分析报告"""
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    n_breakeven: int = 0

    win_rate: float = 0.0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0

    total_pnl: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    max_consecutive_win: int = 0
    max_consecutive_loss: int = 0
    current_streak: int = 0

    n_long: int = 0
    n_short: int = 0
    n_long_wins: int = 0
    n_short_wins: int = 0
    long_pnl: float = 0.0
    short_pnl: float = 0.0

    largest_win: float = 0.0
    largest_loss: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "n_breakeven": self.n_breakeven,
            "win_rate": self.win_rate,
            "long_win_rate": self.long_win_rate,
            "short_win_rate": self.short_win_rate,
            "total_pnl": self.total_pnl,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "profit_factor": self.profit_factor,
            "expectancy": self.expectancy,
            "max_consecutive_win": self.max_consecutive_win,
            "max_consecutive_loss": self.max_consecutive_loss,
            "current_streak": self.current_streak,
            "n_long": self.n_long,
            "n_short": self.n_short,
            "n_long_wins": self.n_long_wins,
            "n_short_wins": self.n_short_wins,
            "long_pnl": self.long_pnl,
            "short_pnl": self.short_pnl,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
        }


class TradeAnalytics:
    """交易分析器"""

    def analyze(self, trades: List[Dict[str, Any]]) -> TradeAnalyticsReport:
        report = TradeAnalyticsReport()
        if not trades:
            return report

        report.n_trades = len(trades)

        consecutive_win = 0
        consecutive_loss = 0
        max_consec_win = 0
        max_consec_loss = 0

        for trade in trades:
            pnl = float(trade.get("pnl", 0.0))
            side = trade.get("side", "").upper()

            report.total_pnl += pnl

            if pnl > 0:
                report.n_wins += 1
                report.total_profit += pnl
                consecutive_win += 1
                consecutive_loss = 0
                if pnl > report.largest_win:
                    report.largest_win = pnl
            elif pnl < 0:
                report.n_losses += 1
                report.total_loss += abs(pnl)
                consecutive_loss += 1
                consecutive_win = 0
                if pnl < report.largest_loss:
                    report.largest_loss = pnl
            else:
                report.n_breakeven += 1
                consecutive_win = 0
                consecutive_loss = 0

            if consecutive_win > max_consec_win:
                max_consec_win = consecutive_win
            if consecutive_loss > max_consec_loss:
                max_consec_loss = consecutive_loss

            if side == "LONG":
                report.n_long += 1
                report.long_pnl += pnl
                if pnl > 0:
                    report.n_long_wins += 1
            elif side == "SHORT":
                report.n_short += 1
                report.short_pnl += pnl
                if pnl > 0:
                    report.n_short_wins += 1

        report.win_rate = report.n_wins / report.n_trades if report.n_trades > 0 else 0.0
        report.long_win_rate = report.n_long_wins / report.n_long if report.n_long > 0 else 0.0
        report.short_win_rate = report.n_short_wins / report.n_short if report.n_short > 0 else 0.0

        report.avg_win = report.total_profit / report.n_wins if report.n_wins > 0 else 0.0
        report.avg_loss = report.total_loss / report.n_losses if report.n_losses > 0 else 0.0

        report.profit_factor = (
            report.total_profit / report.total_loss
            if report.total_loss > 0
            else float("inf") if report.total_profit > 0 else 0.0
        )

        report.expectancy = report.total_pnl / report.n_trades if report.n_trades > 0 else 0.0

        report.max_consecutive_win = max_consec_win
        report.max_consecutive_loss = max_consec_loss
        report.current_streak = consecutive_win if consecutive_win > 0 else -consecutive_loss

        return report
