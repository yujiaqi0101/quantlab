"""
Watchdog — 看门狗

监控系统健康，检测异常行为：
  1. 内存/CPU 超限
  2. 事件积压
  3. 延迟飙升
  4. 错误率飙升
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.health.watchdog")


@dataclass
class WatchdogConfig:
    """看门狗配置"""
    max_memory_mb: float = 2048          # 内存上限
    max_cpu_pct: float = 90.0             # CPU 上限
    max_event_lag: int = 1000             # 事件积压上限
    max_error_rate: float = 0.1           # 错误率上限 (10%)
    max_latency_ms: float = 5000          # 延迟上限
    check_interval: float = 5.0           # 检查间隔


@dataclass
class WatchdogAlert:
    """看门狗告警"""
    level: str       # WARNING / CRITICAL
    category: str    # MEMORY / CPU / EVENT_LAG / ERROR_RATE / LATENCY
    message: str
    value: float
    threshold: float
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
        }


class Watchdog:
    """
    看门狗

    用法：
        watchdog = Watchdog(config)
        watchdog.on_alert(alert_handler)
        watchdog.start()
        watchdog.stop()
    """

    def __init__(self, config: WatchdogConfig = WatchdogConfig()) -> None:
        self.config = config
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: List[Callable[[WatchdogAlert], None]] = []
        self._alerts: List[WatchdogAlert] = []
        self._metrics: Dict = {}

    def on_alert(self, callback: Callable[[WatchdogAlert], None]) -> None:
        self._callbacks.append(callback)

    def update_metrics(self, metrics: Dict) -> None:
        """更新系统指标"""
        self._metrics.update(metrics)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="Watchdog"
        )
        self._thread.start()
        logger.info("Watchdog started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Watchdog stopped")

    def _loop(self) -> None:
        while self._running:
            try:
                self._check()
            except Exception as e:
                logger.error(f"Watchdog check error: {e}")
            time.sleep(self.config.check_interval)

    def _check(self) -> None:
        """执行检查"""
        now = time.time()

        # 内存检查
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / 1024 / 1024
            if mem_mb > self.config.max_memory_mb:
                self._alert(WatchdogAlert(
                    level="WARNING",
                    category="MEMORY",
                    message=f"Memory {mem_mb:.0f}MB > {self.config.max_memory_mb:.0f}MB",
                    value=mem_mb,
                    threshold=self.config.max_memory_mb,
                    timestamp=now,
                ))
        except ImportError:
            pass

        # 事件积压检查
        event_lag = self._metrics.get("event_lag", 0)
        if event_lag > self.config.max_event_lag:
            self._alert(WatchdogAlert(
                level="WARNING",
                category="EVENT_LAG",
                message=f"Event lag {event_lag} > {self.config.max_event_lag}",
                value=float(event_lag),
                threshold=float(self.config.max_event_lag),
                timestamp=now,
            ))

        # 错误率检查
        error_rate = self._metrics.get("error_rate", 0.0)
        if error_rate > self.config.max_error_rate:
            self._alert(WatchdogAlert(
                level="CRITICAL",
                category="ERROR_RATE",
                message=f"Error rate {error_rate:.2%} > {self.config.max_error_rate:.2%}",
                value=error_rate,
                threshold=self.config.max_error_rate,
                timestamp=now,
            ))

        # 延迟检查
        latency = self._metrics.get("latency_ms", 0.0)
        if latency > self.config.max_latency_ms:
            self._alert(WatchdogAlert(
                level="CRITICAL",
                category="LATENCY",
                message=f"Latency {latency:.0f}ms > {self.config.max_latency_ms:.0f}ms",
                value=latency,
                threshold=self.config.max_latency_ms,
                timestamp=now,
            ))

    def _alert(self, alert: WatchdogAlert) -> None:
        self._alerts.append(alert)
        logger.warning(f"Watchdog alert: {alert.category} - {alert.message}")
        for cb in self._callbacks:
            try:
                cb(alert)
            except Exception as e:
                logger.error(f"Watchdog callback error: {e}")

    def get_alerts(self, limit: int = 50) -> List[WatchdogAlert]:
        return self._alerts[-limit:]

    def clear_alerts(self) -> None:
        self._alerts.clear()
