"""
最小回测引擎 (BarEngine)
========================

逐 bar 事件驱动回测引擎，完整流水线 (每根 bar):

    1) scores = strategy.signal(ctx).iloc[i-1]   # 前一根 bar 的信号
    2) target = portfolio_constructor.construct(scores, ts)
    3) 调仓: 按收盘价撮合目标权重
    4) 记录净值

最小可用版本特性:
    - 按收盘价撮合 (无滑点/佣金, 可选配置)
    - 全额调仓到目标权重
    - 现金 + 持仓市值 = 净值
    - 记录每日净值曲线 + 持仓快照

约束:
    - 信号基于前一根 bar (避免未来函数)
    - 调仓在当期收盘价执行
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import PortfolioConstructor, TargetPortfolio
from quantlab.signals.base import SignalStrategy

__all__ = ["BarEngine", "BacktestResult"]


@dataclass
class BacktestResult:
    """回测结果。"""
    equity_curve: pd.Series          # 每日净值
    positions_history: pd.DataFrame  # 每日持仓数量 (date × symbol)
    target_weights: pd.DataFrame     # 每日目标权重 (date × symbol)
    trades: list = field(default_factory=list)  # 成交记录

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1]) if len(self.equity_curve) else 0.0


class BarEngine:
    """逐 bar 回测引擎。

    Args:
        strategy: 信号策略
        portfolio_constructor: 组合构造器
        initial_cash: 初始现金
        commission_rate: 佣金费率 (按成交额, 如 0.0003 = 3bps)
        slippage_rate: 滑点费率 (按价格, 如 0.0002 = 2bps)
    """

    def __init__(
        self,
        strategy: SignalStrategy,
        portfolio_constructor: PortfolioConstructor,
        initial_cash: float = 100000.0,
        commission_rate: float = 0.0,
        slippage_rate: float = 0.0,
    ):
        self.strategy = strategy
        self.portfolio_constructor = portfolio_constructor
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

    def run(self, ctx: FactorContext) -> BacktestResult:
        """执行回测。

        Args:
            ctx: 因子数据上下文

        Returns:
            BacktestResult
        """
        close = ctx.close
        dates = close.index
        symbols = list(close.columns)
        n = len(dates)

        # 一次性计算全部信号 (向量化, 避免逐 bar 重复计算)
        signals = self.strategy.signal(ctx)

        # 持仓: symbol -> quantity
        positions: Dict[str, float] = {s: 0.0 for s in symbols}
        cash = self.initial_cash

        equity_list = []
        positions_rows = []
        weights_rows = []
        trades = []

        for i, ts in enumerate(dates):
            prices = close.iloc[i]

            # 信号: 用前一根 bar 的信号 (避免未来函数)
            if i == 0:
                scores = pd.Series(0.0, index=symbols)
                target = TargetPortfolio(timestamp=ts, weights={})
            else:
                scores = signals.iloc[i - 1]
                target = self.portfolio_constructor.construct(scores, ts)

            # 目标权重
            target_w = {s: 0.0 for s in symbols}
            for s, w in target.weights.items():
                target_w[s] = w

            # 调仓: 计算目标持仓并撮合
            equity = cash + sum(
                positions[s] * prices[s] for s in symbols
            )

            for s in symbols:
                price = prices[s]
                if np.isnan(price) or price <= 0:
                    continue
                # 应用滑点
                target_value = equity * target_w.get(s, 0.0)
                target_qty = target_value / price
                current_qty = positions[s]
                delta_qty = target_qty - current_qty
                if abs(delta_qty) < 1e-9:
                    continue
                # 撮合价 (买入加滑点, 卖出减滑点)
                if delta_qty > 0:
                    fill_price = price * (1 + self.slippage_rate)
                else:
                    fill_price = price * (1 - self.slippage_rate)
                trade_value = abs(delta_qty) * fill_price
                commission = trade_value * self.commission_rate
                cash -= delta_qty * fill_price + commission
                positions[s] = target_qty
                trades.append({
                    "timestamp": ts,
                    "symbol": s,
                    "quantity": delta_qty,
                    "price": fill_price,
                    "commission": commission,
                })

            # 记录收盘净值
            equity = cash + sum(
                positions[s] * prices[s] for s in symbols
            )
            equity_list.append(equity)
            positions_rows.append({s: positions[s] for s in symbols})
            weights_rows.append(target_w)

        equity_curve = pd.Series(equity_list, index=dates, name="equity")
        positions_history = pd.DataFrame(positions_rows, index=dates)
        target_weights = pd.DataFrame(weights_rows, index=dates)

        return BacktestResult(
            equity_curve=equity_curve,
            positions_history=positions_history,
            target_weights=target_weights,
            trades=trades,
        )
