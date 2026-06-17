"""
Heartbeat — 心跳检测

定期检测各组件是否存活
超时未响应 → 触发告警
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.health.heartbeat")


@dataclass
class HeartbeatRecord:
    """心跳记录"""
    component: str
    last_beat: float = 0.0
    interval: float = 5.0       # 预期间隔
    timeout: float = 15.0       # 超时阈值
    alive: bool = True
    beat_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "component": self.component,
            "last_beat": self.last_beat,
            "interval": self.interval,
            "timeout": self.timeout,
            "alive": self.alive,
            "beat_count": self.beat_count,
            "seconds_since_beat": time.time() - self.last_beat if self.last_beat else -1,
        }


class HeartbeatMonitor:
    """
    心跳监控器

    用法：
        monitor = HeartbeatMonitor()
        monitor.register("oms", timeout=15)
        monitor.register("broker", timeout=10)
        monitor.beat("oms")  # OMS 报活
        monitor.start()      # 后台检测
        monitor.stop()
    """

    def __init__(self) -> None:
        self._components: Dict[str, HeartbeatRecord] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._on_timeout = None
        self._lock = threading.RLock()

    def register(
        self,
        component: str,
        interval: float = 5.0,
        timeout: float = 15.0,
    ) -> None:
        with self._lock:
            self._components[component] = HeartbeatRecord(
                component=component,
                interval=interval,
                timeout=timeout,
                last_beat=time.time(),
            )
            logger.info(f"Heartbeat registered: {component} (timeout={timeout}s)")

    def unregister(self, component: str) -> None:
        with self._lock:
            self._components.pop(component, None)

    def beat(self, component: str) -> None:
        """组件报活"""
        with self._lock:
            if component in self._components:
                rec = self._components[component]
                rec.last_beat = time.time()
                rec.beat_count += 1
                rec.alive = True

    def on_timeout(self, callback) -> None:
        self._on_timeout = callback

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="Heartbeat"
        )
        self._thread.start()
        logger.info("HeartbeatMonitor started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("HeartbeatMonitor stopped")

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                components = list(self._components.values())

            for rec in components:
                if now - rec.last_beat > rec.timeout:
                    if rec.alive:
                        rec.alive = False
                        logger.warning(
                            f"Heartbeat timeout: {rec.component} "
                            f"({now - rec.last_beat:.1f}s)"
                        )
                        if self._on_timeout:
                            try:
                                self._on_timeout(rec.component)
                            except Exception:
                                pass

            time.sleep(1.0)

    def get_status(self) -> List[Dict]:
        with self._lock:
            return [r.to_dict() for r in self._components.values()]

    def all_alive(self) -> bool:
        with self._lock:
            return all(r.alive for r in self._components.values())
