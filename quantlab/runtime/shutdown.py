"""
ShutdownManager：优雅停机（V3.3 第七件事）

触发方式：
    1) Ctrl+C / SIGTERM
    2) ConsistencyChecker 报警
    3) KillSwitch 触发
    4) 代码主动 request_shutdown(reason=...)

流程：
    request_shutdown()
        ↓
    主循环看见 shutdown.is_set()
        ↓
    save final snapshot (V3.3)
        ↓
    cancel_all_orders (broker)
        ↓
    broker.disconnect()
        ↓
    event_bus.shutdown()
        ↓
    退出主循环

shutdown 状态：
    .is_set()  →  True / False
    .reason    →  字符串
    .ts        →  触发时间
"""

from __future__ import annotations

import logging
import os
import signal
import threading
import time
from datetime import datetime
from typing import Any, Callable, Optional

from .state_store import StateSnapshot


logger = logging.getLogger("quantlab.shutdown")


class ShutdownManager:
    """
    V3.3 优雅停机

    用法：
        shutdown = ShutdownManager()
        shutdown.install_signal_handlers()    # Ctrl+C 自动触发

        # 在主循环：
        if shutdown.is_set():
            break

        # 在一致性 check 失败时：
        shutdown.request_shutdown(reason="consistency break")
    """

    def __init__(self):
        self._event = threading.Event()
        self.reason: str = ""
        self.timestamp: str = ""
        self._final_snapshot: Optional[StateSnapshot] = None
        self._callbacks: list = []

    # ---- 决策 ----
    def is_set(self) -> bool:
        return self._event.is_set()

    def request_shutdown(self, reason: str = "") -> None:
        if self._event.is_set():
            return
        self._event.set()
        self.reason = reason
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        logger.warning(
            f"SHUTDOWN requested: {reason}"
        )
        for cb in self._callbacks:
            try:
                cb(reason)
            except Exception:
                pass

    def reset(self) -> None:
        """V3.3 重置（仅测试用）"""
        self._event.clear()
        self.reason = ""
        self.timestamp = ""

    # ---- 钩子 ----
    def on_shutdown(self, callback: Callable) -> None:
        self._callbacks.append(callback)

    def set_final_snapshot(self, snap: StateSnapshot) -> None:
        self._final_snapshot = snap

    def save_final_snapshot(self, path: str = "checkpoints/000FINAL.json") -> str:
        if self._final_snapshot is None:
            return ""
        self._final_snapshot.save(path)
        logger.info(
            f"final snapshot saved → {path}"
        )
        return path

    # ---- 信号 ----
    def install_signal_handlers(self) -> None:
        def handler(signum, frame):
            self.request_shutdown(reason=f"signal {signum}")
        try:
            signal.signal(signal.SIGINT, handler)
            signal.signal(signal.SIGTERM, handler)
        except Exception:
            # Windows / Jupyter 下不一定有 SIGTERM
            pass
