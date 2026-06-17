"""
Market Impact Backtest — 冲击回测

普通回测：假设无限成交
真实回测：订单影响价格

结果：真实收益 ≠ 理论收益
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger("quantlab.execution.alpha_aware.impact_backtest")


@dataclass
class BacktestTrade:
    """回测交易"""
    timestamp: int
    symbol: str
    side: str               # BUY / SELL
    qty: float
    intended_price: float   # 意图价格（无冲击）
    actual_price: float = 0.0   # 实际成交价（含冲击）
    impact_bps: float = 0.0
    cost: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "intended_price": self.intended_price,
            "actual_price": self.actual_price,
            "impact_bps": self.impact_bps,
            "cost": self.cost,
        }


@dataclass
class ImpactBacktestResult:
    """冲击回测结果"""
    # 纸面指标
    paper_sharpe: float = 0.0
    paper_return: float = 0.0
    paper_drawdown: float = 0.0

    # 真实指标
    real_sharpe: float = 0.0
    real_return: float = 0.0
    real_drawdown: float = 0.0

    # 冲击影响
    total_impact_cost: float = 0.0
    avg_impact_bps: float = 0.0
    max_impact_bps: float = 0.0
    impact_drag_bps: float = 0.0      # 冲击拖累（年化 bps）

    # 衰减
    sharpe_decay: float = 0.0         # 夏普衰减率
    return_decay: float = 0.0         # 收益衰减率

    trades: List[BacktestTrade] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "paper_sharpe": self.paper_sharpe,
            "paper_return": self.paper_return,
            "paper_drawdown": self.paper_drawdown,
            "real_sharpe": self.real_sharpe,
            "real_return": self.real_return,
            "real_drawdown": self.real_drawdown,
            "total_impact_cost": self.total_impact_cost,
            "avg_impact_bps": self.avg_impact_bps,
            "max_impact_bps": self.max_impact_bps,
            "impact_drag_bps": self.impact_drag_bps,
            "sharpe_decay": self.sharpe_decay,
            "return_decay": self.return_decay,
            "trade_count": len(self.trades),
            "trades": [t.to_dict() for t in self.trades[:50]],  # 限制返回数量
        }


class MarketImpactBacktest:
    """
    冲击回测

    用法：
        bt = MarketImpactBacktest(
            impact_coefficient=0.1,
            volume=1_000_000,
        )
        result = bt.run(
            trades=[
                BacktestTrade(timestamp=1, symbol="BTC", side="BUY", qty=10, intended_price=50000),
                ...
            ],
            paper_sharpe=2.0,
            paper_return=0.3,
        )
    """

    def __init__(
        self,
        impact_coefficient: float = 0.1,    # 冲击系数（sqrt 模型）
        volume: float = 1_000_000,           # 市场成交量
        volatility: float = 0.02,
        fee_rate: float = 0.0004,
    ) -> None:
        self.impact_coefficient = impact_coefficient
        self.volume = volume
        self.volatility = volatility
        self.fee_rate = fee_rate

    def run(
        self,
        trades: List[BacktestTrade],
        paper_sharpe: float = 0.0,
        paper_return: float = 0.0,
        paper_drawdown: float = 0.0,
    ) -> ImpactBacktestResult:
        """运行冲击回测"""
        result = ImpactBacktestResult(
            paper_sharpe=paper_sharpe,
            paper_return=paper_return,
            paper_drawdown=paper_drawdown,
        )

        total_impact_bps = 0.0
        max_impact_bps = 0.0
        total_cost = 0.0

        for trade in trades:
            # 计算冲击（sqrt 模型）
            participation = trade.qty / self.volume if self.volume > 0 else 0
            impact_bps = self.volatility * self.impact_coefficient * math.sqrt(participation) * 10000

            # 实际成交价
            direction = 1 if trade.side == "BUY" else -1
            price_impact = trade.intended_price * impact_bps / 10000 * direction
            trade.actual_price = trade.intended_price + price_impact
            trade.impact_bps = impact_bps

            # 成本
            notional = trade.qty * trade.actual_price
            fee = notional * self.fee_rate
            impact_cost = abs(price_impact) * trade.qty
            trade.cost = fee + impact_cost

            total_impact_bps += impact_bps
            max_impact_bps = max(max_impact_bps, impact_bps)
            total_cost += trade.cost

            result.trades.append(trade)

        # 汇总
        n_trades = len(trades)
        result.avg_impact_bps = total_impact_bps / n_trades if n_trades > 0 else 0
        result.max_impact_bps = max_impact_bps
        result.total_impact_cost = total_cost

        # 年化拖累（简化：假设 252 交易日，每笔 notional 占总资金 10%）
        if n_trades > 0:
            avg_notional = sum(t.qty * t.intended_price for t in trades) / n_trades
            daily_cost_ratio = total_cost / (avg_notional * n_trades) if avg_notional > 0 else 0
            result.impact_drag_bps = daily_cost_ratio * 252 * 10000

        # 真实指标
        cost_drag_return = total_cost / 1_000_000  # 假设 100 万资金
        result.real_return = paper_return - cost_drag_return

        # 真实夏普（简化）
        if paper_return > 0:
            cost_ratio = cost_drag_return / paper_return
            result.real_sharpe = paper_sharpe * (1 - cost_ratio)
        else:
            result.real_sharpe = paper_sharpe

        result.real_drawdown = paper_drawdown + abs(cost_drag_return) * 0.5

        # 衰减
        if paper_sharpe > 0:
            result.sharpe_decay = 1 - result.real_sharpe / paper_sharpe
        if paper_return > 0:
            result.return_decay = 1 - result.real_return / paper_return

        return result
