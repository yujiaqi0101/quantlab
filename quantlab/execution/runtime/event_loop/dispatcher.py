"""
Event Dispatcher — 事件分发器

从 EventBus 获取事件，分发到对应处理器
实现单向数据流的编排
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from .bus import EventBus, Event, EventType

logger = logging.getLogger("quantlab.execution.runtime.event_loop.dispatcher")


class EventDispatcher:
    """
    事件分发器

    定义标准数据流：
      MARKET_TICK → strategy → SIGNAL
      SIGNAL → risk check → ORDER_NEW
      ORDER_NEW → broker → FILL
      FILL → portfolio → POSITION_UPDATE

    用法：
        dispatcher = EventDispatcher(bus)
        dispatcher.set_pipeline(
            on_market=tick_handler,
            on_signal=signal_handler,
            on_order=order_handler,
            on_fill=fill_handler,
        )
        dispatcher.start()
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._handlers: Dict[EventType, Callable] = {}
        self._active: bool = False

    def set_handler(self, event_type: EventType, handler: Callable) -> None:
        self._handlers[event_type] = handler

    def start(self) -> None:
        """注册到 EventBus"""
        for event_type, handler in self._handlers.items():
            self.bus.subscribe(event_type, self._wrap_handler(event_type, handler))
        self._active = True
        logger.info("EventDispatcher started")

    def stop(self) -> None:
        self._active = False
        logger.info("EventDispatcher stopped")

    def _wrap_handler(self, event_type: EventType, handler: Callable) -> Callable:
        def wrapped(event: Event) -> None:
            if not self._active:
                return
            try:
                result = handler(event)
                # 如果 handler 返回 Event，自动发布到 bus
                if isinstance(result, Event):
                    self.bus.publish(result)
            except Exception as e:
                logger.error(
                    f"Dispatcher handler error for {event_type.value}: {e}"
                )
        return wrapped

    @property
    def active(self) -> bool:
        return self._active
