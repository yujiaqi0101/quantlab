"""
Live PnL Attribution — 实时盈亏归因

拆解收益来源：
  1. 行情 (Market)
  2. 策略 (Strategy)
  3. 执行 (Execution)
  4. 滑点 (Slippage)
  5. 手续费 (Commission)

实时计算每个来源的贡献
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.observe.pnl_attribution")


@dataclass
class PnLAttribution:
    """盈亏归因"""
    timestamp: int
    total_pnl: float = 0.0
    market_pnl: float = 0.0          # 行情变动带来的盈亏
    strategy_pnl: float = 0.0        # 策略选择带来的盈亏
    execution_pnl: float = 0.0       # 执行质量
    slippage_cost: float = 0.0       # 滑点成本（负值）
    commission_cost: float = 0.0     # 手续费成本（负值）
    funding_cost: float = 0.0        # 资金费率成本

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "total_pnl": self.total_pnl,
            "market_pnl": self.market_pnl,
            "strategy_pnl": self.strategy_pnl,
            "execution_pnl": self.execution_pnl,
            "slippage_cost": self.slippage_cost,
            "commission_cost": self.commission_cost,
            "funding_cost": self.funding_cost,
            "net_pnl": self.total_pnl - self.slippage_cost - self.commission_cost - self.funding_cost,
        }


@dataclass
class TradeRecord:
    """交易记录（用于归因）"""
    symbol: str
    side: str
    qty: float
    price: float
    timestamp: int
    strategy_id: str = ""
    signal_price: float = 0.0       # 信号产生时的价格
    fill_price: float = 0.0         # 实际成交价
    commission: float = 0.0
    slippage: float = 0.0


class PnLAttributionEngine:
    """
    实时盈亏归因引擎

    用法：
        engine = PnLAttributionEngine()
        engine.record_trade(trade)
        engine.update_price("BTCUSDT", 51000)
        attribution = engine.compute_attribution()
    """

    def __init__(self) -> None:
        self._trades: List[TradeRecord] = []
        self._positions: Dict[str, float] = {}          # symbol → qty
        self._avg_prices: Dict[str, float] = {}          # symbol → avg_price
        self._last_prices: Dict[str, float] = {}         # symbol → last_price
        self._signal_prices: Dict[str, float] = {}       # symbol → signal_price
        self._cumulative: PnLAttribution = PnLAttribution(timestamp=0)
        self._history: List[PnLAttribution] = []

    def record_trade(self, trade: TradeRecord) -> None:
        """记录交易"""
        self._trades.append(trade)

        # 更新持仓
        old_qty = self._positions.get(trade.symbol, 0)
        old_avg = self._avg_prices.get(trade.symbol, 0)

        if old_qty == 0:
            new_avg = trade.fill_price
        elif (old_qty > 0) == (trade.qty > 0):
            # 加仓
            total_value = old_qty * old_avg + trade.qty * trade.fill_price
            new_qty = old_qty + trade.qty
            new_avg = total_value / new_qty if new_qty != 0 else 0
        else:
            # 减仓
            new_qty = old_qty + trade.qty
            new_avg = old_avg if new_qty != 0 else 0

        self._positions[trade.symbol] = new_qty
        self._avg_prices[trade.symbol] = new_avg

        # 记录信号价格
        if trade.signal_price > 0:
            self._signal_prices[trade.symbol] = trade.signal_price

        # 累计成本
        self._cumulative.slippage_cost += trade.slippage * abs(trade.qty)
        self._cumulative.commission_cost += trade.commission

    def update_price(self, symbol: str, price: float) -> None:
        """更新市场价格"""
        self._last_prices[symbol] = price

    def compute_attribution(self) -> PnLAttribution:
        """计算当前盈亏归因"""
        now = int(time.time() * 1000)
        attribution = PnLAttribution(timestamp=now)

        # 1. 市场盈亏：持仓 × 价格变动
        for symbol, qty in self._positions.items():
            if qty == 0:
                continue
            avg_price = self._avg_prices.get(symbol, 0)
            last_price = self._last_prices.get(symbol, avg_price)
            market_pnl = (last_price - avg_price) * qty
            attribution.market_pnl += market_pnl

        # 2. 策略盈亏：信号价格 vs 当前价格的差异
        for symbol, signal_price in self._signal_prices.items():
            qty = self._positions.get(symbol, 0)
            if qty == 0:
                continue
            last_price = self._last_prices.get(symbol, signal_price)
            strategy_pnl = (last_price - signal_price) * qty
            attribution.strategy_pnl += strategy_pnl

        # 3. 执行盈亏：信号价格 vs 成交价格的差异
        for trade in self._trades[-100:]:  # 最近 100 笔
            if trade.signal_price > 0:
                exec_pnl = (trade.fill_price - trade.signal_price) * trade.qty
                if trade.side == "SELL":
                    exec_pnl = -exec_pnl
                attribution.execution_pnl += exec_pnl

        # 4. 滑点成本
        attribution.slippage_cost = self._cumulative.slippage_cost

        # 5. 手续费成本
        attribution.commission_cost = self._cumulative.commission_cost

        # 总盈亏
        attribution.total_pnl = (
            attribution.market_pnl
            + attribution.execution_pnl
            - attribution.slippage_cost
            - attribution.commission_cost
        )

        self._cumulative.total_pnl = attribution.total_pnl
        self._history.append(attribution)

        return attribution

    def get_history(self, limit: int = 100) -> List[PnLAttribution]:
        return self._history[-limit:]

    def get_summary(self) -> Dict:
        """获取归因摘要"""
        current = self.compute_attribution()
        return {
            "current": current.to_dict(),
            "trade_count": len(self._trades),
            "open_positions": {
                s: q for s, q in self._positions.items() if q != 0
            },
        }
