"""
Runtime Entry — 统一运行时入口

T1 第七模块：统一入口

    runtime = start(strategy=my_strategy)
    runtime.stop()

整合：
  - ProductionRuntime（主循环）
  - Scheduler（定时任务）
  - Broker（Paper / Binance）
  - OMS（订单管理）
  - PositionBook（持仓簿）
  - PortfolioBook（组合簿）
  - PaperExchange（撮合引擎）
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..broker import Broker, PaperBroker, OrderRequest
from ..core.oms import OrderManager, OMSOrder, OrderSide, OrderType
from ..paper_exchange import PaperExchange, ExchangeConfig
from ..portfolio_book import PortfolioBook
from ..position_book import PositionBook
from .engine import ProductionRuntime, RuntimeConfig, RuntimeState
from .scheduler import Scheduler
from .strategy_runner import StrategyConfig, StrategyRunner

logger = logging.getLogger("quantlab.execution.runtime.entry")


@dataclass
class RuntimeContext:
    """运行时上下文 — 所有组件的容器"""
    runtime: ProductionRuntime
    scheduler: Scheduler
    broker: Broker
    oms: OrderManager
    position_book: PositionBook
    portfolio_book: PortfolioBook
    exchange: Optional[PaperExchange] = None
    strategy_runners: Dict[str, StrategyRunner] = field(default_factory=dict)


class Runtime:
    """
    统一运行时 — 整合所有交易组件

    用法：
        runtime = Runtime(initial_capital=100000)
        runtime.start()
        runtime.deploy_strategy(strategy_id="rsi", symbols=["BTCUSDT"])
        runtime.stop()
    """

    def __init__(
        self,
        initial_capital: float = 100000.0,
        broker: Optional[Broker] = None,
        exchange: Optional[PaperExchange] = None,
        config: RuntimeConfig = RuntimeConfig(),
    ) -> None:
        self.runtime = ProductionRuntime(config)
        self.scheduler = Scheduler()
        self.broker = broker or PaperBroker(initial_capital=initial_capital)
        self.oms = OrderManager()
        self.position_book = PositionBook()
        self.portfolio_book = PortfolioBook(initial_capital=initial_capital)
        self.exchange = exchange or PaperExchange()
        self._strategy_runners: Dict[str, StrategyRunner] = {}
        self._started = False

    @property
    def state(self) -> RuntimeState:
        return self.runtime.state

    @property
    def is_running(self) -> bool:
        return self._started and self.runtime.is_running

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def start(self) -> None:
        """启动运行时"""
        if self._started:
            return
        self.runtime.start()
        self.scheduler.start()
        self._started = True
        logger.info("Runtime started (broker=%s)", self.broker.name)

    def stop(self) -> None:
        """停止运行时"""
        if not self._started:
            return
        # 停止所有策略
        for runner in self._strategy_runners.values():
            runner.stop()
        self.scheduler.stop()
        self.runtime.stop()
        self._started = False
        logger.info("Runtime stopped")

    def pause(self) -> None:
        self.runtime.pause()

    def resume(self) -> None:
        self.runtime.resume()

    # ------------------------------------------------------------------
    # 策略管理
    # ------------------------------------------------------------------
    def deploy_strategy(
        self,
        strategy_id: str,
        symbols: List[str],
        params: Optional[Dict] = None,
        on_signal: Optional[Callable] = None,
    ) -> StrategyRunner:
        """部署策略"""
        config = StrategyConfig(
            strategy_id=strategy_id,
            name=strategy_id,
            symbols=symbols,
            params=params or {},
        )
        runner = StrategyRunner(config=config, on_signal=on_signal)
        self._strategy_runners[strategy_id] = runner
        if self.is_running:
            runner.start()
        logger.info(f"Strategy deployed: {strategy_id} (symbols={symbols})")
        return runner

    def undeploy_strategy(self, strategy_id: str) -> bool:
        """卸载策略"""
        runner = self._strategy_runners.pop(strategy_id, None)
        if runner:
            runner.stop()
            logger.info(f"Strategy undeployed: {strategy_id}")
            return True
        return False

    def get_strategies(self) -> List[Dict]:
        """获取所有策略状态"""
        return [r.get_status() for r in self._strategy_runners.values()]

    # ------------------------------------------------------------------
    # 下单
    # ------------------------------------------------------------------
    def submit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        strategy_id: str = "",
        signal_id: str = "",
    ) -> Optional[OMSOrder]:
        """提交订单"""
        # 1. OMS 创建订单
        order = self.oms.create_order(
            symbol=symbol,
            side=OrderSide(side),
            quantity=int(qty) if qty == int(qty) else qty,
            order_type=OrderType(order_type),
            price=price,
            strategy_id=strategy_id,
            signal_id=signal_id,
        )
        if not order:
            return None

        # 2. Broker 提交
        req = OrderRequest(
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            price=price,
            strategy_id=strategy_id,
            signal_id=signal_id,
        )
        resp = self.broker.submit_order(req)

        if resp.status == "REJECTED":
            self.oms.reject(order.id, reason=resp.reject_reason)
            logger.warning(f"Order rejected: {resp.reject_reason}")
            return order

        # 3. OMS 更新状态
        self.oms.submit(order.id, broker_order_id=resp.broker_order_id)

        # 4. Paper Broker 立即成交 → 应用到 PositionBook / PortfolioBook
        if resp.status == "FILLED":
            market_price = self.broker.get_market_price(symbol)
            commission = market_price * qty * 0.001  # 简化
            self.oms.apply_fill(order.id, fill_qty=int(qty) if qty == int(qty) else qty, fill_price=market_price)
            self.portfolio_book.apply_fill(
                symbol=symbol,
                side=side,
                qty=qty,
                price=market_price,
                commission=commission,
                strategy_id=strategy_id,
            )

        return order

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.oms.get_order(order_id)
        if not order:
            return False
        if order.broker_order_id:
            self.broker.cancel_order(order.broker_order_id)
        return self.oms.cancel(order_id)

    # ------------------------------------------------------------------
    # 行情
    # ------------------------------------------------------------------
    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新市场价格"""
        self.broker.update_market_prices(prices)
        self.portfolio_book.update_prices(prices)
        for symbol, price in prices.items():
            self.exchange.update_price(symbol, price)

    def on_tick(self, handler: Callable) -> None:
        """注册 tick 处理器"""
        self.runtime.on_tick(handler)

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    def get_status(self) -> Dict:
        """获取完整状态"""
        return {
            "runtime": self.runtime.get_status(),
            "broker": self.broker.to_dict(),
            "oms": {
                "n_orders": len(self.oms.get_all_orders()),
                "n_active": len(self.oms.get_active_orders()),
            },
            "portfolio": self.portfolio_book.to_dict(),
            "strategies": self.get_strategies(),
            "scheduler": self.scheduler.get_status(),
        }

    def get_account(self) -> Dict:
        """获取账户信息"""
        return self.broker.get_account().to_dict()

    def get_positions(self) -> List[Dict]:
        """获取持仓"""
        return [p.to_dict() for p in self.portfolio_book.get_positions()]

    def get_orders(self, active_only: bool = False) -> List[Dict]:
        """获取订单"""
        orders = self.oms.get_active_orders() if active_only else self.oms.get_all_orders()
        return [o.to_dict() for o in orders]

    def get_context(self) -> RuntimeContext:
        """获取运行时上下文（供高级用户使用）"""
        return RuntimeContext(
            runtime=self.runtime,
            scheduler=self.scheduler,
            broker=self.broker,
            oms=self.oms,
            position_book=self.position_book,
            portfolio_book=self.portfolio_book,
            exchange=self.exchange,
            strategy_runners=self._strategy_runners,
        )


# ------------------------------------------------------------------
# 模块级单例 + 便捷函数
# ------------------------------------------------------------------

_runtime: Optional[Runtime] = None


def get_runtime() -> Runtime:
    """获取全局 Runtime 单例"""
    global _runtime
    if _runtime is None:
        _runtime = Runtime()
    return _runtime


def start(
    strategy: Optional[Any] = None,
    initial_capital: float = 100000.0,
    symbols: Optional[List[str]] = None,
    **kwargs,
) -> Runtime:
    """
    启动运行时（统一入口）

    用法：
        runtime = start(strategy=my_strategy, symbols=["BTCUSDT"])
        runtime.stop()
    """
    global _runtime
    _runtime = Runtime(initial_capital=initial_capital, **kwargs)
    _runtime.start()

    if strategy is not None:
        strategy_id = getattr(strategy, "strategy_id", "default")
        syms = symbols or getattr(strategy, "symbols", ["BTCUSDT"])
        _runtime.deploy_strategy(
            strategy_id=strategy_id,
            symbols=syms,
        )

    return _runtime


def stop() -> None:
    """停止全局 Runtime"""
    global _runtime
    if _runtime is not None:
        _runtime.stop()
        _runtime = None
