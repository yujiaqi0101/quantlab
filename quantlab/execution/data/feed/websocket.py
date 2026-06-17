"""
WebSocket Feed — 自动断线重连

核心能力：
  1. 连接断开 → 自动重连
  2. 重连后 → 恢复订阅
  3. 心跳保活
  4. 指数退避重连策略

这是 Fault Tolerance 的核心组件
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("quantlab.execution.data.feed.ws")


class ReconnectingWebSocket:
    """
    自动重连 WebSocket

    用法：
        ws = ReconnectingWebSocket(
            url="wss://stream.binance.com/ws",
            on_message=handler,
            on_status=status_handler,
        )
        ws.start()
        ws.subscribe(["btcusdt@trade", "btcusdt@depth"])
        ws.stop()
    """

    def __init__(
        self,
        url: str,
        on_message: Optional[Callable[[Dict], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
        ping_interval: float = 20.0,
        reconnect_interval: float = 1.0,
        max_reconnect_interval: float = 60.0,
        max_retries: int = 50,
    ) -> None:
        self._url = url
        self._on_message = on_message
        self._on_status = on_status
        self._ping_interval = ping_interval
        self._reconnect_interval = reconnect_interval
        self._max_reconnect_interval = max_reconnect_interval
        self._max_retries = max_retries

        self._ws: Any = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._connected = False
        self._subscriptions: List[str] = []
        self._retry_count = 0
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def retry_count(self) -> int:
        return self._retry_count

    def subscribe(self, streams: List[str]) -> None:
        """添加订阅（重连后自动恢复）"""
        with self._lock:
            for s in streams:
                if s not in self._subscriptions:
                    self._subscriptions.append(s)
            # 如果已连接，立即订阅
            if self._connected and self._ws:
                self._send_subscribe(streams)

    def unsubscribe(self, streams: List[str]) -> None:
        with self._lock:
            for s in streams:
                if s in self._subscriptions:
                    self._subscriptions.remove(s)
            if self._connected and self._ws:
                self._send_unsubscribe(streams)

    def start(self) -> None:
        """启动 WebSocket 连接"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="WSFeed"
        )
        self._thread.start()
        logger.info(f"WebSocket feed started: {self._url}")

    def stop(self) -> None:
        """停止连接"""
        self._running = False
        self._connected = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)
        self._notify_status("STOPPED")
        logger.info("WebSocket feed stopped")

    def _run_loop(self) -> None:
        """主循环：连接 → 消息 → 断线 → 重连"""
        while self._running:
            try:
                self._connect_and_run()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")

            if not self._running:
                break

            # 指数退避
            self._retry_count += 1
            if self._retry_count > self._max_retries:
                logger.error(
                    f"WebSocket max retries ({self._max_retries}) exceeded"
                )
                self._notify_status("MAX_RETRIES_EXCEEDED")
                break

            wait = min(
                self._reconnect_interval * (2 ** min(self._retry_count, 6)),
                self._max_reconnect_interval,
            )
            logger.info(
                f"WebSocket reconnecting in {wait:.1f}s "
                f"(retry #{self._retry_count})"
            )
            self._notify_status(f"RECONNECTING({self._retry_count})")
            time.sleep(wait)

    def _connect_and_run(self) -> None:
        """建立连接并处理消息"""
        import websocket  # websocket-client

        self._notify_status("CONNECTING")

        self._ws = websocket.WebSocketApp(
            self._url,
            on_open=self._on_open,
            on_message=self._on_ws_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._ws.run_forever(
            ping_interval=self._ping_interval,
            ping_timeout=10,
        )

    def _on_open(self, ws) -> None:
        """连接成功 → 恢复订阅"""
        self._connected = True
        self._retry_count = 0
        logger.info(f"WebSocket connected: {self._url}")
        self._notify_status("CONNECTED")

        # 恢复订阅
        if self._subscriptions:
            self._send_subscribe(self._subscriptions)
            logger.info(
                f"Restored {len(self._subscriptions)} subscriptions"
            )

    def _on_ws_message(self, ws, message: str) -> None:
        """收到消息"""
        try:
            data = json.loads(message)
            if self._on_message:
                self._on_message(data)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON: {message[:100]}")
        except Exception as e:
            logger.error(f"Message handler error: {e}")

    def _on_error(self, ws, error) -> None:
        logger.error(f"WebSocket error: {error}")
        self._notify_status("ERROR")

    def _on_close(self, ws, code, reason) -> None:
        self._connected = False
        logger.warning(
            f"WebSocket closed: code={code}, reason={reason}"
        )
        self._notify_status("DISCONNECTED")

    def _send_subscribe(self, streams: List[str]) -> None:
        if not self._ws or not streams:
            return
        msg = {"op": "SUBSCRIBE", "params": streams}
        try:
            self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"Subscribe failed: {e}")

    def _send_unsubscribe(self, streams: List[str]) -> None:
        if not self._ws or not streams:
            return
        msg = {"op": "UNSUBSCRIBE", "params": streams}
        try:
            self._ws.send(json.dumps(msg))
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")

    def _notify_status(self, status: str) -> None:
        if self._on_status:
            try:
                self._on_status(status)
            except Exception:
                pass
