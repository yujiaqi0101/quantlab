"""
Scheduler — 策略定时调度

让策略按固定周期自动运行：
  每分钟 / 每 5 分钟 / 每小时 / 每天

触发：
  strategy.on_bar(bar_close, timestamp)

用法：
    from quantlab.execution.scheduler import Scheduler, ScheduleRule

    scheduler = Scheduler()

    # 每分钟触发
    scheduler.add("rsi_strategy", ScheduleRule.every_minutes(1), on_bar_callback)

    # 每小时触发
    scheduler.add("trend_strategy", ScheduleRule.every_hours(1), on_bar_callback)

    # 每天 09:30 触发
    scheduler.add("daily_strategy", ScheduleRule.daily_at("09:30"), on_bar_callback)

    # 启动
    scheduler.start()

    # 停止
    scheduler.stop()
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.scheduler")


# ------------------------------------------------------------------
# ScheduleRule
# ------------------------------------------------------------------

@dataclass
class ScheduleRule:
    """
    调度规则

    支持的规则：
      every_minutes(n)      每 n 分钟
      every_hours(n)        每 n 小时
      every_seconds(n)      每 n 秒
      daily_at("09:30")     每天固定时间
      cron(...)             cron 表达式（后续扩展）
    """

    # 周期类型："interval" / "daily"
    kind: str = "interval"
    # interval 模式：间隔秒数
    interval_seconds: int = 60
    # daily 模式：HH:MM
    daily_time: str = "00:00"
    # 描述
    description: str = ""

    @staticmethod
    def every_seconds(n: int) -> "ScheduleRule":
        return ScheduleRule(
            kind="interval",
            interval_seconds=n,
            description=f"every {n}s",
        )

    @staticmethod
    def every_minutes(n: int) -> "ScheduleRule":
        return ScheduleRule(
            kind="interval",
            interval_seconds=n * 60,
            description=f"every {n}min",
        )

    @staticmethod
    def every_hours(n: int) -> "ScheduleRule":
        return ScheduleRule(
            kind="interval",
            interval_seconds=n * 3600,
            description=f"every {n}h",
        )

    @staticmethod
    def daily_at(hhmm: str) -> "ScheduleRule":
        return ScheduleRule(
            kind="daily",
            daily_time=hhmm,
            description=f"daily at {hhmm}",
        )

    def next_run_time(self, now: Optional[datetime] = None) -> datetime:
        """计算下次运行时间"""
        now = now or datetime.now()

        if self.kind == "interval":
            return now + timedelta(seconds=self.interval_seconds)
        elif self.kind == "daily":
            # 今天的 hh:mm
            hh, mm = self.daily_time.split(":")
            target = now.replace(
                hour=int(hh),
                minute=int(mm),
                second=0,
                microsecond=0,
            )
            # 如果今天的时间已过，明天
            if target <= now:
                target += timedelta(days=1)
            return target
        else:
            return now + timedelta(seconds=60)

    def __repr__(self) -> str:
        return f"ScheduleRule({self.description})"


# ------------------------------------------------------------------
# ScheduledJob
# ------------------------------------------------------------------

@dataclass
class ScheduledJob:
    """一个调度任务"""
    job_id: str
    rule: ScheduleRule
    callback: Callable[[datetime], None]
    # 状态
    next_run: datetime = field(default_factory=datetime.now)
    last_run: Optional[datetime] = None
    run_count: int = 0
    last_error: Optional[str] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "rule": self.rule.description,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "last_error": self.last_error,
            "enabled": self.enabled,
        }


# ------------------------------------------------------------------
# Scheduler
# ------------------------------------------------------------------

class Scheduler:
    """
    策略调度器

    后台线程按规则触发回调。

    用法：
        scheduler = Scheduler()
        scheduler.add("rsi", ScheduleRule.every_minutes(1), on_bar)
        scheduler.start()
        ...
        scheduler.stop()
    """

    def __init__(self, tick_interval: float = 1.0) -> None:
        """
        参数：
          tick_interval  调度器内部检查间隔（秒）
        """
        self.tick_interval = tick_interval
        self._jobs: Dict[str, ScheduledJob] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # 任务管理
    # ------------------------------------------------------------------

    def add(
        self,
        job_id: str,
        rule: ScheduleRule,
        callback: Callable[[datetime], None],
        enabled: bool = True,
    ) -> ScheduledJob:
        """添加调度任务"""
        with self._lock:
            job = ScheduledJob(
                job_id=job_id,
                rule=rule,
                callback=callback,
                enabled=enabled,
                next_run=rule.next_run_time(),
            )
            self._jobs[job_id] = job
            logger.info(
                f"Scheduler: added job {job_id} ({rule.description}), "
                f"next_run={job.next_run}"
            )
            return job

    def remove(self, job_id: str) -> bool:
        """移除任务"""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]
                logger.info(f"Scheduler: removed job {job_id}")
                return True
            return False

    def enable(self, job_id: str) -> bool:
        """启用任务"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.enabled = True
                return True
            return False

    def disable(self, job_id: str) -> bool:
        """禁用任务"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.enabled = False
                return True
            return False

    def get(self, job_id: str) -> Optional[ScheduledJob]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> List[ScheduledJob]:
        with self._lock:
            return list(self._jobs.values())

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self) -> None:
        """启动调度器（后台线程）"""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="QuantLabScheduler",
            daemon=True,
        )
        self._thread.start()
        self._running = True
        logger.info(
            f"Scheduler started ({len(self._jobs)} jobs)"
        )

    def stop(self, timeout: float = 5.0) -> None:
        """停止调度器"""
        if not self._running:
            return

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._running = False
        logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """调度主循环"""
        logger.info("Scheduler loop started")

        while not self._stop_event.is_set():
            now = datetime.now()

            with self._lock:
                jobs_to_run = [
                    job for job in self._jobs.values()
                    if job.enabled and job.next_run <= now
                ]

            for job in jobs_to_run:
                self._execute_job(job, now)

            # 等待下一个 tick
            self._stop_event.wait(self.tick_interval)

        logger.info("Scheduler loop exited")

    def _execute_job(self, job: ScheduledJob, now: datetime) -> None:
        """执行单个任务"""
        try:
            logger.debug(f"Scheduler: running job {job.job_id}")
            job.callback(now)
            job.last_run = now
            job.run_count += 1
            job.last_error = None
        except Exception as e:
            job.last_error = str(e)
            logger.error(
                f"Scheduler: job {job.job_id} failed: {e}",
                exc_info=True,
            )
        finally:
            # 计算下次运行时间
            job.next_run = job.rule.next_run_time(now)

    # ------------------------------------------------------------------
    # 手动触发
    # ------------------------------------------------------------------

    def trigger(self, job_id: str) -> bool:
        """手动触发一次任务"""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

        now = datetime.now()
        self._execute_job(job, now)
        return True

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "n_jobs": len(self._jobs),
                "n_enabled": sum(1 for j in self._jobs.values() if j.enabled),
                "total_runs": sum(j.run_count for j in self._jobs.values()),
                "jobs": [j.to_dict() for j in self._jobs.values()],
            }


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_scheduler: Optional[Scheduler] = None


def get_scheduler() -> Scheduler:
    """获取全局 Scheduler"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = Scheduler()
    return _global_scheduler


def set_scheduler(scheduler: Scheduler) -> None:
    global _global_scheduler
    _global_scheduler = scheduler
