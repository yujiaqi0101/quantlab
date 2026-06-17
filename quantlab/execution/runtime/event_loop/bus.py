"""
Event Bus — 事件总线

系统内部通信的统一通道
单向数据流：Market → Signal → Order → Fill → Position
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.event_loop.bus")


class EventType(str, Enum):
    MARKET_TICK = "MARKET_TICK"
    MARKET_BAR = "MARKET_BAR"
    SIGNAL = "SIGNAL"
    ORDER_NEW = "ORDER_NEW"
    ORDER_UPDATE = "ORDER_UPDATE"
    FILL = "FILL"
    POSITION_UPDATE = "POSITION_UPDATE"
    RISK_ALERT = "RISK_ALERT"
    KILL_SWITCH = "KILL_SWITCH"
    SYSTEM = "SYSTEM"


@dataclass
class Event:
    """统一事件"""
    type: EventType
    data: Dict = field(default_factory=dict)
    timestamp: int = 0
    source: str = ""
    trace_id: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = int(time.time() * 1000)
        if not self.trace_id:
            import uuid
            self.trace_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "trace_id": self.trace_id,
        }


class EventBus:
    """
    事件总线 — 发布/订阅模式

    用法：
        bus = EventBus()
        bus.subscribe(EventType.SIGNAL, signal_handler)
        bus.subscribe(EventType.FILL, fill_handler)
        bus.publish(Event(type=EventType.SIGNAL, data={...}))
    """

    def __init__(self) -> None:
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self._history: List[Event] = []
        self._max_history: int = 10000

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
    ) -> None:
        self._subscribers[event_type].append(callback)
        logger.debug(f"EventBus subscribe: {event_type.value}")

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable,
    ) -> None:
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        """发布事件"""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        for callback in self._subscribers.get(event.type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"EventBus handler error for {event.type.value}: {e}"
                )

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_history(self) -> None:
        self._history.clear()
