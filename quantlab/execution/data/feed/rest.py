"""
REST Feed — 定时轮询获取行情数据

用于不支持 WebSocket 或作为 WebSocket 降级方案
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.data.feed.rest")


class RESTFeed:
    """
    REST 行情轮询

    用法：
        feed = RESTFeed(
            fetch_fn=lambda: api.get_tickers(["BTCUSDT"]),
            on_data=handler,
            interval=1.0,
        )
        feed.start()
        feed.stop()
    """

    def __init__(
        self,
        fetch_fn: Callable[[], List[Dict]],
        on_data: Callable[[List[Dict]], None],
        interval: float = 1.0,
    ) -> None:
        self._fetch_fn = fetch_fn
        self._on_data = on_data
        self._interval = interval
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_fetch: float = 0.0
        self._error_count: int = 0
        self._max_errors: int = 10

    @property
    def error_count(self) -> int:
        return self._error_count

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="RESTFeed"
        )
        self._thread.start()
        logger.info("RESTFeed started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("RESTFeed stopped")

    def _loop(self) -> None:
        while self._running:
            try:
                data = self._fetch_fn()
                if data:
                    self._on_data(data)
                self._error_count = 0
                self._last_fetch = time.time()
            except Exception as e:
                self._error_count += 1
                logger.error(
                    f"RESTFeed error #{self._error_count}: {e}"
                )
                if self._error_count >= self._max_errors:
                    logger.error("RESTFeed max errors reached, pausing")
                    time.sleep(self._interval * 5)
                    self._error_count = 0

            time.sleep(self._interval)
