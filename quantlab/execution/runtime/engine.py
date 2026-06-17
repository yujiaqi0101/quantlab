"""
Production Runtime Engine — 运行时引擎

系统主循环，串联所有生命线：
  Data → Signal → Risk → OMS → Broker → Fill → Portfolio

核心原则：
  1. 单向数据流
  2. 可恢复性优先
  3. 所有组件通过 Runtime Engine 协调
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.engine")


class RuntimeState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    READONLY = "READONLY"          # Kill Switch 后只读模式
    RECOVERING = "RECOVERING"


@dataclass
class RuntimeConfig:
    """运行时配置"""
    tick_interval: float = 0.1          # 主循环间隔（秒）
    checkpoint_interval: float = 60.0   # checkpoint 间隔
    reconcile_interval: float = 30.0    # 对账间隔
    health_check_interval: float = 10.0 # 健康检查间隔
    max_recovery_attempts: int = 3      # 最大恢复尝试次数


class ProductionRuntime:
    """
    生产运行时引擎

    用法：
        runtime = ProductionRuntime(config)
        runtime.on_tick(handler)
        runtime.start()
        runtime.stop()
    """

    def __init__(self, config: RuntimeConfig = RuntimeConfig()) -> None:
        self.config = config
        self._state = RuntimeState.IDLE
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._tick_handlers: List[Callable] = []
        self._state_handlers: List[Callable] = []
        self._last_tick: float = 0.0
        self._last_checkpoint: float = 0.0
        self._last_reconcile: float = 0.0
        self._last_health_check: float = 0.0
        self._tick_count: int = 0
        self._error_count: int = 0
        self._readonly: bool = False

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def is_running(self) -> bool:
        return self._state == RuntimeState.RUNNING

    @property
    def is_readonly(self) -> bool:
        return self._readonly

    def on_tick(self, handler: Callable) -> None:
        self._tick_handlers.append(handler)

    def on_state_change(self, handler: Callable) -> None:
        self._state_handlers.append(handler)

    def start(self) -> None:
        with self._lock:
            if self._state in (RuntimeState.RUNNING, RuntimeState.RECOVERING):
                return
            self._set_state(RuntimeState.RUNNING)
            self._thread = threading.Thread(
                target=self._main_loop, daemon=True, name="ProductionRuntime"
            )
            self._thread.start()
            logger.info("ProductionRuntime started")

    def stop(self) -> None:
        with self._lock:
            if self._state == RuntimeState.STOPPED:
                return
            self._set_state(RuntimeState.STOPPING)
        if self._thread:
            self._thread.join(timeout=10)
        self._set_state(RuntimeState.STOPPED)
        logger.info("ProductionRuntime stopped")

    def pause(self) -> None:
        self._set_state(RuntimeState.PAUSED)
        logger.info("ProductionRuntime paused")

    def resume(self) -> None:
        if self._state == RuntimeState.PAUSED:
            self._set_state(RuntimeState.RUNNING)
            logger.info("ProductionRuntime resumed")

    def enable_readonly(self) -> None:
        """切换只读模式（Kill Switch 用）"""
        self._readonly = True
        self._set_state(RuntimeState.READONLY)
        logger.critical("ProductionRuntime: READONLY mode enabled")

    def disable_readonly(self) -> None:
        self._readonly = False
        if self._state == RuntimeState.READONLY:
            self._set_state(RuntimeState.RUNNING)
            logger.info("ProductionRuntime: READONLY mode disabled")

    def _set_state(self, state: RuntimeState) -> None:
        old = self._state
        self._state = state
        if old != state:
            logger.info(f"Runtime state: {old.value} → {state.value}")
            for handler in self._state_handlers:
                try:
                    handler(old, state)
                except Exception as e:
                    logger.error(f"State handler error: {e}")

    def _main_loop(self) -> None:
        """主循环"""
        while self._state not in (RuntimeState.STOPPED, RuntimeState.STOPPING):
            if self._state == RuntimeState.PAUSED:
                time.sleep(0.5)
                continue

            try:
                now = time.time()
                self._tick_count += 1
                self._last_tick = now

                # 执行 tick handlers
                for handler in self._tick_handlers:
                    try:
                        handler(now)
                    except Exception as e:
                        self._error_count += 1
                        logger.error(f"Tick handler error: {e}")

                # 定期任务
                if now - self._last_checkpoint >= self.config.checkpoint_interval:
                    self._do_checkpoint()
                    self._last_checkpoint = now

                if now - self._last_reconcile >= self.config.reconcile_interval:
                    self._do_reconcile()
                    self._last_reconcile = now

                if now - self._last_health_check >= self.config.health_check_interval:
                    self._do_health_check()
                    self._last_health_check = now

            except Exception as e:
                self._error_count += 1
                logger.error(f"Runtime loop error: {e}")

            time.sleep(self.config.tick_interval)

    def _do_checkpoint(self) -> None:
        """checkpoint 回调"""
        pass  # 由外部注册

    def _do_reconcile(self) -> None:
        """对账回调"""
        pass  # 由外部注册

    def _do_health_check(self) -> None:
        """健康检查回调"""
        pass  # 由外部注册

    def get_status(self) -> Dict:
        return {
            "state": self._state.value,
            "tick_count": self._tick_count,
            "error_count": self._error_count,
            "readonly": self._readonly,
            "last_tick": self._last_tick,
            "uptime_seconds": time.time() - self._last_tick if self._last_tick else 0,
        }
