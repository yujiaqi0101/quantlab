"""
TradingCore — 统一交易核心
=========================

Backtest/Paper/Live 三模式共享同一套引擎：
    - 同一套 Strategy Engine（EventStrategy 事件驱动接口）
    - 同一套 OMS（OMSOrder 状态机）
    - 同一套 Portfolio Engine（PositionBook + PortfolioBook）
    - 唯一变化：数据来源（DataFeed）和 Broker 类型（由 TradingMode 决定）

核心数据流：
    Bar → 更新价格 → 构造TradingContext → 策略on_exit/on_bar
        → OrderIntent → _submit_intent → OMS + Broker
        → Fill → PositionBook/PortfolioBook → 模式后处理

用法：
    from quantlab.trading_core import TradingCore
    from quantlab.trading_core.modes import BacktestMode

    mode = BacktestMode()
    core = TradingCore(mode, initial_capital=1_000_000)
    core.deploy_strategy("alpha014", strategy, symbols=["000001.SZ"])
    core.on_bar(bar)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from quantlab.execution.broker.base import Broker, OrderRequest
from quantlab.execution.core.oms import (
    OMSOrder,
    OrderManager,
    OrderSide,
    OrderState,
    OrderType,
)
from quantlab.execution.portfolio_book import PortfolioBook
from quantlab.execution.position_book import PositionBook

from .interfaces import (
    Bar,
    EventStrategy,
    OrderIntent,
    Position,
    TradingContext,
)

logger = logging.getLogger("quantlab.trading_core")

__all__ = ["TradingCore"]


class TradingCore:
    """统一交易核心 — Backtest/Paper/Live 三模式共享。

    整合 OMS / Broker / PositionBook / PortfolioBook，
    通过 EventStrategy 接口驱动策略。
    """

    def __init__(
        self,
        mode: "TradingMode",
        initial_capital: float = 1_000_000,
        broker: Optional[Broker] = None,
        max_bar_history: int = 500,
    ) -> None:
        """
        Args:
            mode: 交易模式实例（BacktestMode/PaperMode/LiveMode）
            initial_capital: 初始资金
            broker: 可选 Broker 实例，为 None 时由 mode 创建
            max_bar_history: 每个标的保留的K线历史最大长度
        """
        self.mode = mode
        self.initial_capital = initial_capital
        self.broker: Broker = broker or mode.create_broker(initial_capital)

        # 共享组件（直接复用 execution/ 现有代码）
        # 注意：PortfolioBook 内部已包含 PositionBook，这里直接引用同一实例，
        # 避免两个 PositionBook 数据不同步。
        self.oms = OrderManager()
        self.portfolio_book = PortfolioBook(initial_capital)
        self.position_book = self.portfolio_book.position_book

        # 策略注册表 {strategy_id: (strategy, symbols)}
        self._strategies: Dict[str, tuple] = {}
        # K线历史缓冲 {symbol: List[Bar]}，用于构建 bar_data
        self._bar_history: Dict[str, List[Bar]] = {}
        self._max_bar_history = max_bar_history

        # 当前最新价格 {symbol: price}
        self._latest_prices: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # 策略管理
    # ------------------------------------------------------------------
    def deploy_strategy(
        self,
        strategy_id: str,
        strategy: EventStrategy,
        symbols: List[str],
    ) -> None:
        """部署策略。

        Args:
            strategy_id: 策略唯一ID
            strategy: EventStrategy 实例
            symbols: 策略交易的标的列表
        """
        if strategy_id in self._strategies:
            logger.warning(f"策略 {strategy_id} 已存在，将覆盖")
        strategy.on_init()
        self._strategies[strategy_id] = (strategy, list(symbols))
        logger.info(
            f"部署策略 {strategy_id} ({strategy.name}@{strategy.version}), "
            f"symbols={symbols}"
        )

    def undeploy_strategy(self, strategy_id: str) -> bool:
        """卸载策略。

        Args:
            strategy_id: 策略唯一ID

        Returns:
            是否成功卸载
        """
        if strategy_id in self._strategies:
            del self._strategies[strategy_id]
            logger.info(f"卸载策略 {strategy_id}")
            return True
        return False

    # ------------------------------------------------------------------
    # 核心数据流
    # ------------------------------------------------------------------
    def on_bar(self, bar: Bar) -> None:
        """行情驱动入口（三模式统一）。

        流程：
            1. 更新 broker 和 portfolio_book 的市场价格
            2. 更新 K线历史缓冲
            3. 构造 TradingContext
            4. 遍历策略：先 on_exit 后 on_bar，收集 OrderIntent
            5. 逐个 _submit_intent
            6. 调用 mode.on_post_bar 做模式特定后处理

        Args:
            bar: 当前K线
        """
        # 1. 更新价格（broker 和 portfolio_book 都需要更新）
        price_dict = {bar.symbol: bar.close}
        self.broker.update_market_prices(price_dict)
        self.portfolio_book.update_prices(price_dict)
        self._latest_prices[bar.symbol] = bar.close

        # 2. 更新 K线历史缓冲
        self._update_bar_history(bar)

        # 3. 构造 TradingContext
        ctx = self._build_context(bar)

        # 4. 遍历策略：先 on_exit 后 on_bar
        for strategy_id, (strategy, _symbols) in list(self._strategies.items()):
            try:
                exit_orders = strategy.on_exit(ctx) or []
                entry_orders = strategy.on_bar(bar, ctx) or []
            except Exception as e:
                logger.exception(f"策略 {strategy_id} 执行异常: {e}")
                continue

            # 5. 逐个提交订单（先出场后入场）
            for intent in exit_orders + entry_orders:
                self._submit_intent(strategy_id, intent)

        # 6. 模式特定后处理
        self.mode.on_post_bar(bar, self)

    def _submit_intent(
        self,
        strategy_id: str,
        intent: OrderIntent,
    ) -> Optional[OMSOrder]:
        """将 OrderIntent 转为 OMSOrder 并提交 Broker。

        流程：
            1. OrderIntent -> OrderRequest (side大写, qty=quantity, order_type大写)
            2. oms.create_order() 创建 OMSOrder
            3. oms.submit(order_id)
            4. broker.submit_order(req) -> OrderResponse
            5. 如果 FILLED：oms.apply_fill(), portfolio_book.apply_fill()
            6. 如果 REJECTED：oms.reject()
            7. 返回 OMSOrder

        Args:
            strategy_id: 策略ID
            intent: 订单意图

        Returns:
            创建的 OMSOrder（失败返回 None）
        """
        # 1. OrderIntent -> OrderRequest
        req = OrderRequest(
            symbol=intent.symbol,
            side=intent.side.upper(),  # BUY / SELL
            qty=intent.quantity,
            order_type=intent.order_type.upper(),  # MARKET / LIMIT
            price=intent.price,
            strategy_id=strategy_id,
        )

        # 2. OMS 创建订单（side/order_type 转 Enum）
        side_enum = OrderSide.BUY if intent.side.upper() == "BUY" else OrderSide.SELL
        type_enum = (
            OrderType.LIMIT
            if intent.order_type.upper() == "LIMIT"
            else OrderType.MARKET
        )

        oms_order = self.oms.create_order(
            symbol=intent.symbol,
            side=side_enum,
            quantity=intent.quantity,
            order_type=type_enum,
            price=intent.price,
            strategy_id=strategy_id,
            account_id=self.broker.account_id,
        )
        if oms_order is None:
            logger.warning(f"OMS 创建订单失败: {intent}")
            return None

        # 3. OMS 提交（状态机：NEW → PENDING_SUBMIT → SUBMITTED）
        # 注意：OrderManager.submit 直接尝试转到 SUBMITTED，
        # 但 OMSOrder 状态机要求 NEW → PENDING_SUBMIT → SUBMITTED，
        # 因此先手动转到 PENDING_SUBMIT，再调用 oms.submit。
        oms_order.transition_to(OrderState.PENDING_SUBMIT, "PENDING_SUBMIT")
        self.oms.submit(oms_order.id)

        # 4. Broker 提交
        response = self.broker.submit_order(req)

        # 5. 处理响应
        if response.status == "FILLED":
            # 计算成交价和手续费（适配 PaperBroker 的滑点逻辑）
            fill_price, commission = self._compute_fill_price_and_commission(
                intent=intent,
                market_price=self._latest_prices.get(intent.symbol, 0.0),
            )
            # 更新 OMS 成交
            self.oms.apply_fill(
                order_id=oms_order.id,
                fill_qty=intent.quantity,
                fill_price=fill_price,
            )
            # 更新 broker_order_id 映射
            if response.broker_order_id:
                oms_order.broker_order_id = response.broker_order_id
            # 更新 PortfolioBook（含 PositionBook）
            self.portfolio_book.apply_fill(
                symbol=intent.symbol,
                side=intent.side.upper(),
                qty=intent.quantity,
                price=fill_price,
                commission=commission,
                strategy_id=strategy_id,
            )
            # 更新持仓的 market_price（apply_fill 不会自动更新 market_price，
            # 需要用最新市场价刷新，否则 equity 计算不正确）
            latest_price = self._latest_prices.get(intent.symbol, fill_price)
            self.portfolio_book.update_prices({intent.symbol: latest_price})
            logger.info(
                f"成交: {intent.side} {intent.quantity} {intent.symbol} "
                f"@ {fill_price:.4f} (fee={commission:.4f})"
            )
        elif response.status == "REJECTED":
            self.oms.reject(oms_order.id, response.reject_reason)
            logger.warning(
                f"订单被拒: {oms_order.id} reason={response.reject_reason}"
            )
        else:
            # SUBMITTED 等其他状态（PaperBroker 不会出现，但兼容扩展）
            logger.info(f"订单状态: {response.status} for {oms_order.id}")

        return oms_order

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------
    def _update_bar_history(self, bar: Bar) -> None:
        """更新 K线历史缓冲。"""
        if bar.symbol not in self._bar_history:
            self._bar_history[bar.symbol] = []
        self._bar_history[bar.symbol].append(bar)
        # 限制历史长度
        if len(self._bar_history[bar.symbol]) > self._max_bar_history:
            self._bar_history[bar.symbol] = self._bar_history[bar.symbol][
                -self._max_bar_history:
            ]

    def _build_context(self, bar: Bar) -> TradingContext:
        """构造策略运行上下文。

        Args:
            bar: 当前K线

        Returns:
            TradingContext 实例
        """
        # 收集 universe（所有策略的 symbols 并集）
        universe: List[str] = []
        seen = set()
        for _strategy, symbols in self._strategies.values():
            for s in symbols:
                if s not in seen:
                    universe.append(s)
                    seen.add(s)
        # 确保 bar.symbol 在 universe 中
        if bar.symbol not in seen:
            universe.append(bar.symbol)

        # 构造 positions（从 position_book 转换为 trading_core.Position）
        positions: Dict[str, Position] = {}
        for pos in self.position_book.get_positions(include_closed=False):
            positions[pos.symbol] = Position(
                symbol=pos.symbol,
                quantity=pos.qty,
                entry_price=pos.avg_price,
                entry_date=self._format_entry_date(pos.updated_at),
                current_price=pos.market_price,
                direction="long" if pos.qty > 0 else "short",
            )

        # 构造 bar_data {symbol: DataFrame}
        bar_data: Dict[str, pd.DataFrame] = {}
        for symbol in universe:
            bar_data[symbol] = self._build_bar_data(symbol)

        return TradingContext(
            timestamp=bar.timestamp,
            cash=self.portfolio_book.cash,
            frozen_cash=0.0,  # PaperBroker 即时成交，无冻结现金
            positions=positions,
            bar_data=bar_data,
            universe=universe,
        )

    def _build_bar_data(self, symbol: str) -> pd.DataFrame:
        """从历史缓冲构建K线 DataFrame。

        Args:
            symbol: 标的代码

        Returns:
            DataFrame(index=datetime, columns=[open,high,low,close,volume])
        """
        bars = self._bar_history.get(symbol, [])
        if not bars:
            return pd.DataFrame()
        data = [
            {
                "datetime": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ]
        df = pd.DataFrame(data)
        df.set_index("datetime", inplace=True)
        return df

    @staticmethod
    def _format_entry_date(updated_at: int) -> str:
        """将毫秒时间戳格式化为日期字符串。

        Args:
            updated_at: 毫秒时间戳

        Returns:
            日期字符串 (YYYY-MM-DD)
        """
        if updated_at <= 0:
            return ""
        try:
            return datetime.fromtimestamp(updated_at / 1000).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return ""

    def _compute_fill_price_and_commission(
        self,
        intent: OrderIntent,
        market_price: float,
    ) -> tuple:
        """计算成交价和手续费（适配 PaperBroker 的滑点逻辑）。

        PaperBroker 的成交价逻辑：
            - LIMIT 单: base_price = intent.price
            - MARKET 单 BUY: base_price = market_price * (1 + slippage_rate)
            - MARKET 单 SELL: base_price = market_price * (1 - slippage_rate)
            - commission = base_price * qty * fee_rate

        对于非 PaperBroker，用 market_price 作为成交价，手续费为 0。

        Args:
            intent: 订单意图
            market_price: 当前市场价格

        Returns:
            (fill_price, commission) 元组
        """
        # 获取 broker 的费率参数（PaperBroker 有 fee_rate/slippage_rate 属性）
        fee_rate = getattr(self.broker, "fee_rate", 0.0)
        slippage_rate = getattr(self.broker, "slippage_rate", 0.0)

        # 计算成交价
        if intent.order_type.upper() == "LIMIT" and intent.price is not None:
            fill_price = intent.price
        else:
            if intent.side.upper() == "BUY":
                fill_price = market_price * (1 + slippage_rate)
            else:
                fill_price = market_price * (1 - slippage_rate)

        # 计算手续费
        commission = fill_price * intent.quantity * fee_rate

        return fill_price, commission

    # ------------------------------------------------------------------
    # 查询接口
    # ------------------------------------------------------------------
    def get_account(self) -> Dict[str, Any]:
        """获取账户信息（从 portfolio_book 聚合）。

        Returns:
            账户信息字典
        """
        return {
            "initial_capital": self.portfolio_book.initial_capital,
            "cash": self.portfolio_book.cash,
            "equity": self.portfolio_book.equity(),
            "invested_value": self.portfolio_book.invested_value(),
            "net_invested": self.portfolio_book.net_invested(),
            "margin": self.portfolio_book.margin(),
            "exposure": self.portfolio_book.exposure(),
            "realized_pnl": self.portfolio_book.realized_pnl(),
            "unrealized_pnl": self.portfolio_book.unrealized_pnl(),
            "total_pnl": self.portfolio_book.total_pnl(),
            "total_return": self.portfolio_book.total_return(),
            "max_drawdown": self.portfolio_book.max_drawdown(),
            "current_drawdown": self.portfolio_book.current_drawdown(),
            "n_open_positions": self.portfolio_book.n_open_positions(),
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        """获取持仓列表（从 position_book）。

        Returns:
            持仓字典列表
        """
        return [p.to_dict() for p in self.position_book.get_positions()]

    def get_orders(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """获取订单列表（从 oms）。

        Args:
            active_only: 是否只返回活动订单

        Returns:
            订单字典列表
        """
        if active_only:
            orders = self.oms.get_active_orders()
        else:
            orders = self.oms.get_all_orders()
        return [o.to_dict() for o in orders]

    def get_status(self) -> Dict[str, Any]:
        """获取综合状态。

        Returns:
            综合状态字典（含账户/持仓/订单/策略信息）
        """
        return {
            "mode": self.mode.name,
            "broker": self.broker.to_dict(),
            "account": self.get_account(),
            "positions": self.get_positions(),
            "orders": {
                "active": len(self.oms.get_active_orders()),
                "total": len(self.oms.get_all_orders()),
            },
            "strategies": {
                sid: {"name": s.name, "version": s.version, "symbols": syms}
                for sid, (s, syms) in self._strategies.items()
            },
        }
