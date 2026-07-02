"""
SignalStrategyAdapter — 信号策略适配器
====================================

将现有 SignalStrategy（signal() -> DataFrame 信号面板模式）
适配为 EventStrategy（on_bar -> List[OrderIntent] 事件驱动模式）。

不废弃现有 ML Lab / SignalSet，通过本适配器桥接到统一 TradingCore。

用法：
    from quantlab.trading_core.adapters import SignalStrategyAdapter
    from quantlab.signals.alpha_014 import Alpha014Strategy
    from quantlab.portfolio_construction.base import TopN

    signal_strategy = Alpha014Strategy(period=5)
    constructor = TopN(n=2)
    adapter = SignalStrategyAdapter(signal_strategy, constructor)
    core.deploy_strategy("alpha014", adapter, symbols=["000001.SZ", ...])
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List, Optional

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.signals.base import SignalStrategy

from ..interfaces import (
    Bar,
    EventStrategy,
    OrderIntent,
    TradingContext,
)

if TYPE_CHECKING:
    from quantlab.portfolio_construction.base import PortfolioConstructor

logger = logging.getLogger("quantlab.trading_core.adapters")

__all__ = ["SignalStrategyAdapter"]


class SignalStrategyAdapter(EventStrategy):
    """将 SignalStrategy 适配为 EventStrategy。

    SignalStrategy 产出信号面板 (date × symbol)，
    本适配器负责：
        1. 从 ctx.bar_data 构造 FactorContext
        2. 调用 signal_strategy.signal() 获取信号面板
        3. 取当日信号行（截面 scores）
        4. 用 portfolio_constructor 将信号转为目标权重
        5. 目标权重 vs 当前持仓 -> 差异 -> OrderIntent 列表
    """

    def __init__(
        self,
        signal_strategy: SignalStrategy,
        portfolio_constructor: Optional["PortfolioConstructor"] = None,
    ) -> None:
        """
        Args:
            signal_strategy: SignalStrategy 实例
            portfolio_constructor: 组合构造器（将信号转为目标权重），
                                   为 None 时无法生成订单（仅产出信号）
        """
        self._strategy = signal_strategy
        self._constructor = portfolio_constructor
        # SignalStrategy 没有 name 属性，用类名作为默认
        self.name = getattr(signal_strategy, "name", type(signal_strategy).__name__)
        self.version = "1.0"

    def on_init(self) -> None:
        """初始化钩子（委托给被适配策略）。"""
        if hasattr(self._strategy, "on_init"):
            try:
                self._strategy.on_init()  # type: ignore[attr-defined]
            except Exception as e:
                logger.warning(f"signal_strategy.on_init 异常: {e}")

    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        """每根K线到来时调用。

        流程：
            1. 从 ctx.bar_data 构造 FactorContext
            2. 调用 signal_strategy.signal() 获取信号面板
            3. 取当日信号行
            4. 用 portfolio_constructor 转为目标权重
            5. 目标权重 vs 当前持仓 -> OrderIntent 列表

        Args:
            bar: 当前K线
            ctx: 运行上下文

        Returns:
            订单意图列表
        """
        # 没有组合构造器，无法生成订单
        if self._constructor is None:
            return []

        # 1. 构造 FactorContext
        factor_ctx = self._build_factor_context(ctx)
        if factor_ctx is None:
            return []

        # 2. 调用 signal() 获取信号面板
        try:
            signal_df = self._strategy.signal(factor_ctx)
        except Exception as e:
            logger.warning(f"signal_strategy.signal() 调用异常: {e}")
            return []

        if signal_df is None or signal_df.empty:
            return []

        # 3. 取当日信号行（截面 scores）
        bar_date = pd.Timestamp(bar.timestamp.date())
        day_scores = self._get_day_signals(signal_df, bar_date)
        if day_scores is None or day_scores.empty:
            return []

        # 4. 用 portfolio_constructor 转为目标权重
        try:
            target_portfolio = self._constructor.construct(day_scores, bar_date)
        except Exception as e:
            logger.warning(f"portfolio_constructor.construct() 异常: {e}")
            return []

        target_weights = target_portfolio.weights

        # 5. 目标权重 vs 当前持仓 -> OrderIntent 列表
        return self._generate_orders(bar, ctx, target_weights)

    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        """出场逻辑（信号面板模式由权重差异自动处理）。"""
        return []

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _build_factor_context(self, ctx: TradingContext) -> Optional[FactorContext]:
        """从 ctx.bar_data 构造 FactorContext。

        Args:
            ctx: 运行上下文

        Returns:
            FactorContext 实例（失败返回 None）
        """
        if not ctx.bar_data:
            return None
        try:
            return FactorContext.from_dict(ctx.bar_data)
        except Exception as e:
            logger.warning(f"FactorContext 构造失败: {e}")
            return None

    @staticmethod
    def _get_day_signals(
        signal_df: pd.DataFrame,
        bar_date: pd.Timestamp,
    ) -> Optional[pd.Series]:
        """从信号面板中取指定日期的截面信号。

        Args:
            signal_df: 信号面板 (index=date, columns=symbol)
            bar_date: 目标日期

        Returns:
            截面信号 Series (index=symbol)，失败返回 None
        """
        # 尝试精确匹配
        if bar_date in signal_df.index:
            return signal_df.loc[bar_date].dropna()

        # 尝试用 asof 取最近的不超过 bar_date 的信号
        try:
            idx = signal_df.index.asof(bar_date)
            if idx is None:
                return None
            return signal_df.loc[idx].dropna()
        except (TypeError, KeyError):
            return None

    def _generate_orders(
        self,
        bar: Bar,
        ctx: TradingContext,
        target_weights: dict,
    ) -> List[OrderIntent]:
        """根据目标权重和当前持仓生成订单意图。

        策略：
            1. 对目标权重中的每个标的，计算目标数量与当前数量的差异
            2. 对不在目标权重中但有持仓的标的，生成平仓订单
            3. 数量差异小于阈值的不生成订单

        Args:
            bar: 当前K线
            ctx: 运行上下文
            target_weights: 目标权重 {symbol: weight}

        Returns:
            订单意图列表
        """
        intents: List[OrderIntent] = []
        total_value = ctx.total_value
        if total_value <= 0:
            return intents

        # 已处理的标的集合
        processed: set = set()

        # 1. 处理目标权重中的标的
        for symbol, weight in target_weights.items():
            processed.add(symbol)
            target_value = total_value * weight
            # 用当前持仓的市价或当前 bar 的收盘价
            current_price = self._get_price(ctx, bar, symbol)
            if current_price <= 0:
                continue

            target_qty = target_value / current_price
            current_qty = (
                ctx.positions[symbol].quantity
                if symbol in ctx.positions
                else 0.0
            )
            diff = target_qty - current_qty

            if abs(diff) < 1e-6:
                continue

            if diff > 0:
                side = "buy"
                quantity = diff
                reason = f"rebalance buy to weight={weight:.4f}"
            else:
                side = "sell"
                quantity = -diff
                reason = f"rebalance sell to weight={weight:.4f}"

            intents.append(OrderIntent(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="market",
                reason=reason,
            ))

        # 2. 处理不在目标权重中但有持仓的标的（平仓）
        for symbol, pos in ctx.positions.items():
            if symbol in processed:
                continue
            if abs(pos.quantity) < 1e-6:
                continue

            # 平仓：多头卖出，空头买入
            if pos.quantity > 0:
                side = "sell"
                quantity = pos.quantity
            else:
                side = "buy"
                quantity = -pos.quantity

            intents.append(OrderIntent(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type="market",
                reason="exit position not in target",
            ))

        return intents

    @staticmethod
    def _get_price(
        ctx: TradingContext,
        bar: Bar,
        symbol: str,
    ) -> float:
        """获取标的的当前价格。

        优先用当前持仓的市价，其次用当前 bar 的收盘价，
        最后从 bar_data 取最新收盘价。

        Args:
            ctx: 运行上下文
            bar: 当前K线
            symbol: 标的代码

        Returns:
            当前价格（失败返回 0.0）
        """
        # 优先用当前持仓的市价
        if symbol in ctx.positions and ctx.positions[symbol].current_price > 0:
            return ctx.positions[symbol].current_price
        # 当前 bar 的收盘价
        if symbol == bar.symbol:
            return bar.close
        # 从 bar_data 取最新收盘价
        if symbol in ctx.bar_data:
            df = ctx.bar_data[symbol]
            if not df.empty and "close" in df.columns:
                return float(df["close"].iloc[-1])
        return 0.0
