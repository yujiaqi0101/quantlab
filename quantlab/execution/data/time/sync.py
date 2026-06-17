"""
时间同步管理器 — 定期从交易所拉取服务器时间

职责：
  1. 定期调用交易所 API 获取 server time
  2. 更新 ExchangeClock
  3. 检测时钟漂移并告警
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from .clock import ExchangeClock, get_clock

logger = logging.getLogger("quantlab.execution.data.time.sync")


class TimeSyncManager:
    """
    时间同步管理器

    用法：
        sync = TimeSyncManager(
            fetch_server_time=lambda: exchange.get_server_time(),
            interval=30,
        )
        sync.start()  # 后台线程定期同步
        sync.stop()
    """

    def __init__(
        self,
        fetch_server_time: Callable[[], int],
        clock: Optional[ExchangeClock] = None,
        interval: float = 30.0,
    ) -> None:
        self._fetch = fetch_server_time
        self._clock = clock or get_clock()
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def sync_once(self) -> bool:
        """执行一次同步，返回是否成功"""
        try:
            server_ms = self._fetch()
            if server_ms and server_ms > 0:
                self._clock.sync(server_ms)
                return True
        except Exception as e:
            logger.error(f"TimeSync failed: {e}")
        return False

    def start(self) -> None:
        """启动后台同步线程"""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="TimeSync"
            )
            self._thread.start()
            logger.info("TimeSyncManager started")

    def stop(self) -> None:
        """停止同步"""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            logger.info("TimeSyncManager stopped")

    def _loop(self) -> None:
        import time
        # 首次立即同步
        self.sync_once()
        while self._running:
            time.sleep(self._interval)
            if self._running:
                self.sync_once()
