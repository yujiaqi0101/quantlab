"""
SystemContext：统一入口（V3.2）

V3.2 核心思想：
    以前：模块 A 直接 import 模块 B（耦合严重）
    现在：所有模块只 import context
    context 内有：
        strategy
        portfolio
        execution
        broker
        risk_manager
        logger (TradeLogger)
        metrics (MetricsCollector)
        tracer (EventTracer)
        alerts  (AlertManager)
        dashboard (Dashboard)

依赖方向：
    modules → context  ✓
    context → modules  ✗  (context 不反向依赖)

    modules 通过 self.context.xxx 拿东西
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .logger import TradeLogger, new_trace_id
from .metrics import MetricsCollector
from .tracer import EventTracer
from .alert import AlertManager
from .dashboard import Dashboard


@dataclass
class SystemContext:
    """
    V3.2 SystemContext

    用法：
        ctx = SystemContext(
            source="paper",
            strategy=strategy,
            portfolio=portfolio,
            execution=exec_,
            broker=broker,
            risk_manager=risk,
        )
        # 内部自动建 logger / metrics / tracer / alerts / dashboard

        # 模块访问
        ctx.logger.trade(symbol, qty, price, ts)
        ctx.metrics.update(equity=...)
        ctx.tracer.span(trace_id, "SIGNAL", score=0.8)
        ctx.alerts.check_and_dispatch(snapshot)
    """

    # 必填
    source: str              # backtest / paper / live
    strategy: Any
    portfolio: Any
    execution: Any
    broker: Any
    risk_manager: Any

    # 可选 / 自动建
    log_dir: str = "logs"
    initial_equity: float = 0.0

    logger: Optional[TradeLogger] = None
    metrics: Optional[MetricsCollector] = None
    tracer: Optional[EventTracer] = None
    alerts: Optional[AlertManager] = None
    dashboard: Optional[Dashboard] = None

    # Market data
    market_data: Any = None

    # 其它对象
    tradebook: Any = None

    # 系统元数据
    extras: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.logger is None:
            self.logger = TradeLogger(
                source=self.source,
                log_dir=self.log_dir,
            )
        if self.metrics is None:
            self.metrics = MetricsCollector(
                initial_equity=self.initial_equity
                or (
                    self.portfolio.initial_cash
                    if self.portfolio is not None
                    else 0.0
                )
            )
        if self.tracer is None:
            self.tracer = EventTracer(
                log_dir=self.log_dir,
            )
        if self.alerts is None:
            self.alerts = AlertManager(
                log_dir=self.log_dir,
            )
        if self.dashboard is None:
            self.dashboard = Dashboard(
                metrics=self.metrics,
                portfolio=self.portfolio,
                tradebook=self.tradebook,
            )

    # ---- 一键触发所有告警 / 写盘 ----
    def tick(self, **snapshot) -> None:
        """
        V3.2 主循环钩子
        在每根 bar / 拍时调用一次，自动 update metrics + check alerts
        """
        self.metrics.update(**snapshot)
        if self.metrics.trade_count > 0:
            self.metrics.record(**snapshot)
        self.alerts.check_and_dispatch(self.metrics.snapshot())

    def attach_event_bus(self, bus) -> None:
        """
        把 EventBus 事件自动转给 logger
        V3.2 串联 EventBus
        """
        from ..event.event_types import (
            FillEvent,
            OrderEvent,
        )

        def on_order(ev: OrderEvent):
            tid = getattr(ev, "trace_id", "") or new_trace_id()
            self.logger.order(
                local_id=ev.type,
                symbol=ev.symbol,
                qty=ev.quantity,
                ts=ev.timestamp,
            )
            self.metrics.update_reject = self.metrics.update_reject   # noqa

        def on_fill(ev: FillEvent):
            self.logger.trade(
                symbol=ev.symbol,
                qty=ev.quantity,
                price=ev.price,
                ts=ev.timestamp,
            )
            self.metrics.update_trade(
                pnl=0.0,
                symbol=ev.symbol,
                timestamp=ev.timestamp,
            )
            self.metrics.update(
                pnl=self.metrics.pnl,
            )

        try:
            bus.subscribe("ORDER", on_order)
            bus.subscribe("FILL", on_fill)
        except Exception:
            pass
