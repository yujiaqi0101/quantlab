"""
Replay Engine — 交易重放引擎

完整交易重放：
  1. 从 journal 加载历史事件
  2. 按时间顺序重放
  3. 支持加速 / 暂停 / 跳转
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.observe.replay")


class ReplayState(str, Enum):
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"


@dataclass
class ReplayEvent:
    """重放事件"""
    timestamp: int
    type: str
    data: Dict = field(default_factory=dict)
    replay_time: float = 0.0     # 重放时的实际时间

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "data": self.data,
            "replay_time": self.replay_time,
        }


class ReplayEngine:
    """
    交易重放引擎

    用法：
        engine = ReplayEngine()
        engine.load_events(events)
        engine.on_event(handler)
        engine.play(speed=10.0)  # 10 倍速
        engine.pause()
        engine.seek(timestamp)
    """

    def __init__(self) -> None:
        self._events: List[ReplayEvent] = []
        self._position: int = 0
        self._state = ReplayState.IDLE
        self._speed: float = 1.0
        self._handlers: List[Callable[[ReplayEvent], None]] = []
        self._start_ts: int = 0
        self._start_real: float = 0.0

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def position(self) -> int:
        return self._position

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def progress(self) -> float:
        if not self._events:
            return 0.0
        return self._position / len(self._events)

    def load_events(self, events: List[ReplayEvent]) -> None:
        """加载事件序列"""
        self._events = sorted(events, key=lambda e: e.timestamp)
        self._position = 0
        if self._events:
            self._start_ts = self._events[0].timestamp
        logger.info(f"ReplayEngine: loaded {len(self._events)} events")

    def on_event(self, handler: Callable[[ReplayEvent], None]) -> None:
        self._handlers.append(handler)

    def play(self, speed: float = 1.0) -> None:
        """开始/继续播放"""
        if not self._events:
            return
        self._speed = speed
        self._state = ReplayState.PLAYING
        self._start_real = time.time()

        if self._position == 0:
            self._start_ts = self._events[0].timestamp
        else:
            # 从当前位置继续
            self._start_ts = self._events[self._position].timestamp

        logger.info(f"ReplayEngine: playing at {speed}x speed")
        self._run()

    def pause(self) -> None:
        self._state = ReplayState.PAUSED
        logger.info("ReplayEngine: paused")

    def stop(self) -> None:
        self._state = ReplayState.STOPPED
        self._position = 0
        logger.info("ReplayEngine: stopped")

    def seek(self, timestamp: int) -> None:
        """跳转到指定时间点"""
        for i, event in enumerate(self._events):
            if event.timestamp >= timestamp:
                self._position = i
                break
        logger.info(f"ReplayEngine: seek to {timestamp}, position={self._position}")

    def _run(self) -> None:
        """执行重放"""
        while self._state == ReplayState.PLAYING and self._position < len(self._events):
            event = self._events[self._position]

            # 计算等待时间
            elapsed_real = time.time() - self._start_real
            elapsed_sim = (event.timestamp - self._start_ts) / 1000.0
            wait_time = elapsed_sim / self._speed - elapsed_real

            if wait_time > 0:
                time.sleep(min(wait_time, 0.1))
                continue

            # 发送事件
            event.replay_time = time.time()
            for handler in self._handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Replay handler error: {e}")

            self._position += 1

        if self._position >= len(self._events):
            self._state = ReplayState.FINISHED
            logger.info("ReplayEngine: finished")

    def get_status(self) -> Dict:
        return {
            "state": self._state.value,
            "position": self._position,
            "total_events": self.total_events,
            "progress": self.progress,
            "speed": self._speed,
        }
