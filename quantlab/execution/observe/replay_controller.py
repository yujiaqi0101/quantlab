"""
Replay Controller — 重放控制器

支持：
    Play       播放
    Pause      暂停
    Stop       停止
    Next       下一事件
    Previous   上一事件
    Seek       跳转到事件索引

前端体验类似视频播放器。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .event_store import EventStore, StoredEvent, get_event_store
from .replay_state import ReplayState

logger = logging.getLogger("quantlab.execution.observe.replay_controller")


class ReplayStatus(str, Enum):
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    FINISHED = "FINISHED"


@dataclass
class ReplaySnapshot:
    """重放快照"""
    status: ReplayStatus
    session_id: str
    position: int
    total_events: int
    progress: float
    speed: float
    current_event: Optional[StoredEvent]
    state: ReplayState

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "session_id": self.session_id,
            "position": self.position,
            "total_events": self.total_events,
            "progress": self.progress,
            "speed": self.speed,
            "current_event": self.current_event.to_dict() if self.current_event else None,
            "state": self.state.to_dict(),
        }


class ReplayController:
    """
    重放控制器

    用法：
        ctrl = ReplayController()
        ctrl.load_session("session_id")
        ctrl.play(speed=10.0)
        ctrl.next_event()
        ctrl.previous_event()
        snapshot = ctrl.get_snapshot()
    """

    def __init__(
        self,
        store: Optional[EventStore] = None,
        initial_cash: float = 10000.0,
    ) -> None:
        self.store = store or get_event_store()
        self.initial_cash = initial_cash

        self._events: List[StoredEvent] = []
        self._position: int = 0
        self._status: ReplayStatus = ReplayStatus.IDLE
        self._speed: float = 1.0
        self._session_id: str = ""
        self._state: ReplayState = ReplayState(initial_cash=initial_cash)

        self._lock = threading.RLock()
        self._play_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # 默认不暂停

        self._on_event_callbacks: List[Callable[[StoredEvent, ReplayState], None]] = []
        self._on_state_change: List[Callable[[ReplayStatus], None]] = []

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def status(self) -> ReplayStatus:
        return self._status

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

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def state(self) -> ReplayState:
        return self._state

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------

    def load_session(self, session_id: str) -> int:
        """加载会话事件"""
        with self._lock:
            self.stop()
            self._session_id = session_id
            self._events = self.store.query(session_id=session_id, limit=100000, order="asc")
            self._position = 0
            self._state = ReplayState(initial_cash=self.initial_cash)
            self._status = ReplayStatus.IDLE
            logger.info(f"ReplayController: loaded {len(self._events)} events for session {session_id}")
            return len(self._events)

    def load_events(self, events: List[StoredEvent], session_id: str = "ad-hoc") -> int:
        """直接加载事件列表"""
        with self._lock:
            self.stop()
            self._session_id = session_id
            self._events = sorted(events, key=lambda e: e.timestamp)
            self._position = 0
            self._state = ReplayState(initial_cash=self.initial_cash)
            self._status = ReplayStatus.IDLE
            return len(self._events)

    # ------------------------------------------------------------------
    # 播放控制
    # ------------------------------------------------------------------

    def play(self, speed: float = 1.0) -> None:
        """播放"""
        with self._lock:
            if not self._events:
                return
            if self._status == ReplayStatus.FINISHED:
                # 重新开始
                self._position = 0
                self._state = ReplayState(initial_cash=self.initial_cash)

            self._speed = speed
            self._status = ReplayStatus.PLAYING
            self._stop_flag.clear()
            self._pause_event.set()

            # 启动播放线程
            if self._play_thread and self._play_thread.is_alive():
                return
            self._play_thread = threading.Thread(target=self._play_loop, daemon=True)
            self._play_thread.start()
            self._notify_state_change()

    def pause(self) -> None:
        """暂停"""
        with self._lock:
            if self._status == ReplayStatus.PLAYING:
                self._status = ReplayStatus.PAUSED
                self._pause_event.clear()
                self._notify_state_change()

    def resume(self) -> None:
        """恢复"""
        with self._lock:
            if self._status == ReplayStatus.PAUSED:
                self._status = ReplayStatus.PLAYING
                self._pause_event.set()
                self._notify_state_change()

    def stop(self) -> None:
        """停止"""
        with self._lock:
            self._stop_flag.set()
            self._pause_event.set()
            if self._play_thread and self._play_thread.is_alive():
                self._play_thread.join(timeout=1.0)
            self._play_thread = None
            self._position = 0
            self._state = ReplayState(initial_cash=self.initial_cash)
            self._status = ReplayStatus.STOPPED
            self._notify_state_change()

    def next_event(self) -> Optional[StoredEvent]:
        """前进一个事件"""
        with self._lock:
            if self._position >= len(self._events):
                return None
            event = self._events[self._position]
            self._state.apply(event)
            self._position += 1
            self._notify_event(event)
            if self._position >= len(self._events):
                self._status = ReplayStatus.FINISHED
                self._notify_state_change()
            return event

    def previous_event(self) -> Optional[StoredEvent]:
        """后退一个事件（重新计算状态）"""
        with self._lock:
            if self._position <= 0:
                return None
            self._position -= 1
            # 重新从头计算状态
            self._state = ReplayState(initial_cash=self.initial_cash)
            for i in range(self._position):
                self._state.apply(self._events[i])
            event = self._events[self._position] if self._position < len(self._events) else None
            if event:
                self._notify_event(event)
            return event

    def seek(self, position: int) -> None:
        """跳转到指定位置"""
        with self._lock:
            position = max(0, min(position, len(self._events)))
            self._position = position
            # 重新计算状态
            self._state = ReplayState(initial_cash=self.initial_cash)
            for i in range(position):
                self._state.apply(self._events[i])
            self._status = ReplayStatus.PAUSED
            self._notify_state_change()

    def set_speed(self, speed: float) -> None:
        """设置播放速度"""
        with self._lock:
            self._speed = max(0.1, min(speed, 1000.0))

    # ------------------------------------------------------------------
    # 快照
    # ------------------------------------------------------------------

    def get_snapshot(self) -> ReplaySnapshot:
        """获取当前快照"""
        with self._lock:
            current_event = self._events[self._position - 1] if 0 < self._position <= len(self._events) else None
            return ReplaySnapshot(
                status=self._status,
                session_id=self._session_id,
                position=self._position,
                total_events=len(self._events),
                progress=self.progress,
                speed=self._speed,
                current_event=current_event,
                state=self._state,
            )

    def get_events_range(self, start: int = 0, limit: int = 100) -> List[StoredEvent]:
        """获取事件范围"""
        with self._lock:
            return self._events[start:start + limit]

    # ------------------------------------------------------------------
    # 回调
    # ------------------------------------------------------------------

    def on_event(self, callback: Callable[[StoredEvent, ReplayState], None]) -> None:
        """注册事件回调"""
        self._on_event_callbacks.append(callback)

    def on_state_change(self, callback: Callable[[ReplayStatus], None]) -> None:
        """注册状态变化回调"""
        self._on_state_change.append(callback)

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _play_loop(self) -> None:
        """播放循环（后台线程）"""
        logger.info(f"ReplayController: play loop started at {self._speed}x")
        last_ts = 0
        while not self._stop_flag.is_set():
            if self._status != ReplayStatus.PLAYING:
                break

            # 暂停检查
            self._pause_event.wait()
            if self._stop_flag.is_set() or self._status != ReplayStatus.PLAYING:
                break

            if self._position >= len(self._events):
                with self._lock:
                    self._status = ReplayStatus.FINISHED
                    self._notify_state_change()
                break

            event = self._events[self._position]

            # 按时间间隔播放
            if last_ts > 0 and self._speed > 0:
                gap_ms = event.timestamp - last_ts
                wait_sec = gap_ms / 1000.0 / self._speed
                if wait_sec > 0:
                    # 分段等待，便于响应 stop
                    slept = 0.0
                    while slept < wait_sec:
                        if self._stop_flag.is_set() or self._status != ReplayStatus.PLAYING:
                            break
                        step = min(0.05, wait_sec - slept)
                        time.sleep(step)
                        slept += step
                    if self._stop_flag.is_set() or self._status != ReplayStatus.PLAYING:
                        break

            with self._lock:
                if self._status != ReplayStatus.PLAYING:
                    break
                self._state.apply(event)
                self._position += 1
                last_ts = event.timestamp
                self._notify_event(event)

        logger.info("ReplayController: play loop exited")

    def _notify_event(self, event: StoredEvent) -> None:
        for cb in self._on_event_callbacks:
            try:
                cb(event, self._state)
            except Exception as e:
                logger.error(f"Replay event callback error: {e}")

    def _notify_state_change(self) -> None:
        for cb in self._on_state_change:
            try:
                cb(self._status)
            except Exception as e:
                logger.error(f"Replay state change callback error: {e}")


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_controller: Optional[ReplayController] = None


def get_replay_controller() -> ReplayController:
    global _global_controller
    if _global_controller is None:
        _global_controller = ReplayController()
    return _global_controller
