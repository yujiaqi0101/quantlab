"""
Scheduler — 任务调度器

定期执行：
  1. Checkpoint
  2. Reconciliation
  3. Health Check
  4. Time Sync
  5. PnL Attribution
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.scheduler")


@dataclass
class ScheduledTask:
    """定时任务"""
    name: str
    interval: float               # 秒
    callback: Callable
    last_run: float = 0.0
    enabled: bool = True
    run_count: int = 0
    error_count: int = 0


class Scheduler:
    """
    任务调度器

    用法：
        scheduler = Scheduler()
        scheduler.add_task("checkpoint", 60.0, do_checkpoint)
        scheduler.add_task("reconcile", 30.0, do_reconcile)
        scheduler.start()
        scheduler.stop()
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, ScheduledTask] = {}
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.RLock()

    def add_task(
        self,
        name: str,
        interval: float,
        callback: Callable,
    ) -> None:
        with self._lock:
            self._tasks[name] = ScheduledTask(
                name=name,
                interval=interval,
                callback=callback,
            )
            logger.info(f"Scheduler add task: {name} (interval={interval}s)")

    def remove_task(self, name: str) -> None:
        with self._lock:
            self._tasks.pop(name, None)

    def enable_task(self, name: str) -> None:
        if name in self._tasks:
            self._tasks[name].enabled = True

    def disable_task(self, name: str) -> None:
        if name in self._tasks:
            self._tasks[name].enabled = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="Scheduler"
        )
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            with self._lock:
                tasks = list(self._tasks.values())

            for task in tasks:
                if not task.enabled:
                    continue
                if now - task.last_run < task.interval:
                    continue

                try:
                    task.callback()
                    task.run_count += 1
                except Exception as e:
                    task.error_count += 1
                    logger.error(f"Scheduler task '{task.name}' error: {e}")
                finally:
                    task.last_run = now

            time.sleep(0.1)

    def get_status(self) -> List[Dict]:
        return [
            {
                "name": t.name,
                "interval": t.interval,
                "enabled": t.enabled,
                "run_count": t.run_count,
                "error_count": t.error_count,
                "last_run": t.last_run,
            }
            for t in self._tasks.values()
        ]
