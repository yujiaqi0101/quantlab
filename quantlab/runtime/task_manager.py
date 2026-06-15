"""
TaskManager — 异步任务中心（V4.0 Application Layer 基础设施）

为什么需要：
  Backtest / Optimizer / WalkForward / 实盘启动 都可能跑很久，
  不能让 HTTP 长连接等在那里。
  Service 层把每次操作包成 Task，前端用：

      POST /backtests         →  task_id
      GET  /tasks/{id}        →  status / progress
      WS   /ws/tasks          →  实时进度推送

Task 状态机：
  PENDING ──► RUNNING ──► SUCCESS
                     │
                     ├──► FAILED
                     │
                     └──► CANCELLED

注意：
  - TaskManager 是**进程内**的，跨进程需要外部存储（Redis/DB）。
    V4.0 默认单进程，后续可替换 backend。
  - 提供 subscribe() 回调，WebSocket 层可订阅实时变化。
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional

from ..dto.task import Task, TaskStatus, TaskType, new_task


logger = logging.getLogger("quantlab.task_manager")


# -------------------------------------------------------------
# 任务回调
# -------------------------------------------------------------
TaskCallback = Callable[[Task], None]


class TaskManager:
    """
    进程内任务管理器（线程安全）

    用法：
        mgr = TaskManager()
        task = mgr.create_task(TaskType.BACKTEST, metadata={...})
        mgr.start(task.id)
        mgr.update_progress(task.id, 0.5, "running")
        mgr.complete(task.id, result={...})
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._counter: int = 0
        self._lock = threading.RLock()
        self._subscribers: List[TaskCallback] = []

    # ---------------------------------------------------------
    # 订阅（WebSocket / 监控 都会用）
    # ---------------------------------------------------------
    def subscribe(self, callback: TaskCallback) -> None:
        with self._lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: TaskCallback) -> None:
        with self._lock:
            try:
                self._subscribers.remove(callback)
            except ValueError:
                pass

    def _notify(self, task: Task) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(task)
            except Exception as exc:  # 订阅者异常不能影响主流程
                logger.warning(
                    "task subscriber raised: %s", exc
                )

    # ---------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------
    def _new_id(self) -> str:
        with self._lock:
            self._counter += 1
        # 短 id 前缀 + 8位 uuid
        return f"task_{self._counter:08d}_{uuid.uuid4().hex[:6]}"

    def create_task(
        self,
        type_: str = TaskType.OTHER.value,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
    ) -> Task:
        """创建 PENDING 任务"""
        tid = task_id or self._new_id()
        task = new_task(type_=type_, task_id=tid, metadata=metadata)
        with self._lock:
            self._tasks[tid] = task
        logger.info("task created: %s (%s)", tid, type_)
        self._notify(task)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        with self._lock:
            t = self._tasks.get(task_id)
            return t

    def list(
        self,
        status: Optional[str] = None,
        type_: Optional[str] = None,
    ) -> List[Task]:
        """按状态 / 类型过滤列出（最新在前）"""
        with self._lock:
            items = list(self._tasks.values())
        if status:
            items = [t for t in items if t.status == status]
        if type_:
            items = [t for t in items if t.type == type_]
        items.sort(key=lambda t: t.created_at, reverse=True)
        return items

    # ---------------------------------------------------------
    # 状态机
    # ---------------------------------------------------------
    def _set(
        self,
        task_id: str,
        *,
        status: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        started: bool = False,
        finished: bool = False,
    ) -> Optional[Task]:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = max(0.0, min(100.0, float(progress)))
            if message is not None:
                task.message = message
            if result is not None:
                task.result = dict(result)
            if error is not None:
                task.error = error
            if started and not task.started_at:
                task.started_at = datetime.utcnow().isoformat()
            if finished:
                task.finished_at = datetime.utcnow().isoformat()
        self._notify(task)
        return task

    def start(self, task_id: str, message: str = "started") -> Optional[Task]:
        return self._set(
            task_id,
            status=TaskStatus.RUNNING.value,
            message=message,
            started=True,
        )

    def update_progress(
        self,
        task_id: str,
        progress: float,
        message: Optional[str] = None,
    ) -> Optional[Task]:
        return self._set(
            task_id,
            progress=progress,
            message=message,
        )

    def complete(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None,
        message: str = "completed",
    ) -> Optional[Task]:
        return self._set(
            task_id,
            status=TaskStatus.SUCCESS.value,
            progress=100.0,
            message=message,
            result=result,
            finished=True,
        )

    def fail(
        self,
        task_id: str,
        error: str,
        message: Optional[str] = None,
    ) -> Optional[Task]:
        return self._set(
            task_id,
            status=TaskStatus.FAILED.value,
            error=error,
            message=message or f"failed: {error}",
            finished=True,
        )

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.is_terminal:
                return False
            task.status = TaskStatus.CANCELLED.value
            task.finished_at = datetime.utcnow().isoformat()
            task.message = task.message or "cancelled"
        self._notify(task)
        return True

    # ---------------------------------------------------------
    # 上下文管理器（推荐用法）
    # ---------------------------------------------------------
    def runnable(
        self,
        type_: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "_TaskContext":
        """with mgr.runnable("backtest", {...}) as ctx: ..."""
        return _TaskContext(self, type_, metadata)


class _TaskContext:
    """with-block 风格任务管理"""

    def __init__(
        self,
        mgr: TaskManager,
        type_: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.mgr = mgr
        self.type_ = type_
        self.metadata = metadata
        self.task: Optional[Task] = None

    def __enter__(self) -> "_TaskContext":
        self.task = self.mgr.create_task(
            type_=self.type_, metadata=self.metadata
        )
        self.mgr.start(self.task.id)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.task is None:
            return False
        if exc_type is None:
            self.mgr.complete(
                self.task.id,
                result=self.task.result,
            )
        else:
            self.mgr.fail(
                self.task.id,
                error=str(exc),
            )
        return False  # 不吞异常

    # 透传快捷方法
    def update(self, progress: float, message: Optional[str] = None) -> None:
        if self.task:
            self.mgr.update_progress(
                self.task.id, progress, message
            )

    def set_result(self, result: Dict[str, Any]) -> None:
        if self.task:
            self.task.result.update(result)


# -------------------------------------------------------------
# 全局单例（service / api / ws 共享同一个 TaskManager）
# -------------------------------------------------------------
_default: Optional[TaskManager] = None
_default_lock = threading.Lock()


def get_task_manager() -> TaskManager:
    """获取/创建全局 TaskManager"""
    global _default
    with _default_lock:
        if _default is None:
            _default = TaskManager()
            logger.info("default TaskManager initialized")
        return _default


def set_task_manager(mgr: TaskManager) -> None:
    """替换全局 TaskManager（用于测试或多实例）"""
    global _default
    with _default_lock:
        _default = mgr
