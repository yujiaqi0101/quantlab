"""
Signal Executor — 信号执行器

研究系统输出：signal = BUY / SELL / HOLD
实盘系统需要：order = {symbol, qty, price}

SignalExecutor 负责：
  Signal
    ↓
  Target Position（目标持仓）
    ↓
  Order（订单）

转换流程：
  1) 策略产出 Signal（方向 + 强度）
  2) SignalExecutor 把 Signal 转成 TargetPortfolio（目标权重）
  3) Execution 层（matcher）把 TargetPortfolio 转成 Order 列表

用法：
    from quantlab.execution.signal_executor import SignalExecutor

    executor = SignalExecutor(
        portfolio=portfolio,
        prices={"BTCUSDT": 50000, "ETHUSDT": 3000},
    )
    orders = executor.execute(
        signals={"BTCUSDT": Signal(side="BUY", strength=0.6)},
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..core.order import Order
from ..core.portfolio import Portfolio
from ..portfolio_construction.target_portfolio import TargetPortfolio
from .matcher import TargetWeightExecution

logger = logging.getLogger("quantlab.execution.signal_executor")


# ------------------------------------------------------------------
# Signal
# ------------------------------------------------------------------

class SignalSide(str, Enum):
    """信号方向"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """
    交易信号

    字段：
      symbol    标的
      side      方向（BUY/SELL/HOLD）
      strength  强度 [0, 1]，用于决定仓位大小
      price     信号生成时的价格（可选）
      timestamp 信号时间戳
      metadata  额外信息（alpha_id / strategy_id 等）
    """
    symbol: str
    side: SignalSide = SignalSide.HOLD
    strength: float = 0.0  # [0, 1]
    price: Optional[float] = None
    timestamp: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 归一化 strength
        self.strength = max(0.0, min(1.0, float(self.strength)))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "strength": self.strength,
            "price": self.price,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ------------------------------------------------------------------
# SignalExecutor
# ------------------------------------------------------------------

class SignalExecutor:
    """
    信号执行器

    把 Signal 转成 Order

    两种模式：
      1) weight_mode:  signal.strength → 目标权重 → 目标持仓 → Order
      2) quantity_mode: signal.strength → 直接目标数量 → Order
    """

    def __init__(
        self,
        portfolio: Portfolio,
        prices: Dict[str, float],
        max_weight: float = 1.0,
        lot_size: int = 1,
        position_tolerance: float = 0.02,
        mode: str = "weight",  # weight / quantity
    ) -> None:
        """
        参数：
          portfolio             当前组合
          prices                最新价格
          max_weight            单标的最大权重
          lot_size              最小交易单位
          position_tolerance    调仓容忍度
          mode                  weight（按权重）/ quantity（按数量）
        """
        self.portfolio = portfolio
        self.prices = prices
        self.max_weight = max_weight
        self.mode = mode
        self.matcher = TargetWeightExecution(
            lot_size=lot_size,
            position_tolerance=position_tolerance,
        )

    def execute(
        self,
        signals: Dict[str, Signal],
        timestamp: Optional[Any] = None,
    ) -> List[Order]:
        """
        执行一批信号，返回 Order 列表

        参数：
          signals   Dict[symbol, Signal]
          timestamp 本次执行时间戳

        返回：
          List[Order]
        """
        if not signals:
            return []

        # 1) Signal → TargetPortfolio
        target = self.signals_to_target(signals, timestamp)

        # 2) TargetPortfolio → Orders
        orders = self.matcher.generate_orders(
            portfolio=self.portfolio,
            target_portfolio=target,
            prices=self.prices,
        )

        logger.info(
            f"SignalExecutor: {len(signals)} signals → "
            f"{len(orders)} orders"
        )
        return orders

    def signals_to_target(
        self,
        signals: Dict[str, Signal],
        timestamp: Optional[Any] = None,
    ) -> TargetPortfolio:
        """
        把 Signal 转成 TargetPortfolio（目标权重）

        逻辑：
          BUY   → weight = strength * max_weight
          SELL  → weight = 0（清仓）
          HOLD  → 保持当前权重
        """
        weights: Dict[str, float] = {}

        # 先把当前持仓的 symbol 加入（保持未提及的仓位）
        for sym in self.portfolio.positions:
            if sym not in signals:
                # 保持当前权重
                pos = self.portfolio.positions[sym]
                price = self.prices.get(sym, pos.avg_price or 0)
                equity = self.portfolio.equity()
                if equity > 0 and price > 0:
                    weights[sym] = (pos.qty * price) / equity
                else:
                    weights[sym] = 0.0

        # 处理信号
        for sym, signal in signals.items():
            if signal.side == SignalSide.BUY:
                weights[sym] = signal.strength * self.max_weight
            elif signal.side == SignalSide.SELL:
                weights[sym] = 0.0
            elif signal.side == SignalSide.HOLD:
                # 保持当前
                pos = self.portfolio.positions.get(sym)
                if pos is not None:
                    price = self.prices.get(sym, pos.avg_price or 0)
                    equity = self.portfolio.equity()
                    if equity > 0 and price > 0:
                        weights[sym] = (pos.qty * price) / equity
                    else:
                        weights[sym] = 0.0
                else:
                    weights[sym] = 0.0

        return TargetPortfolio(
            timestamp=timestamp,
            weights=weights,
        )

    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新最新价格"""
        self.prices.update(prices)


# ------------------------------------------------------------------
# 便捷函数
# ------------------------------------------------------------------

def execute_signals(
    signals: Dict[str, Signal],
    portfolio: Portfolio,
    prices: Dict[str, float],
    **kwargs,
) -> List[Order]:
    """一键执行信号"""
    executor = SignalExecutor(portfolio=portfolio, prices=prices, **kwargs)
    return executor.execute(signals)
