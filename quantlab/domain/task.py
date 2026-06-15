"""
Domain — Task

异步任务的核心状态机。
Backtest / Optimizer / WalkForward / Validation / 实盘启动
全部继承这个状态机。

状态转移：
  PENDING ──► RUNNING ──► SUCCESS
                     │
                     ├──► FAILED
                     │
                     └──► CANCELLED

重要：
  - Task 是不可变快照 + 状态字段的混合体
  - TaskManager 持有所有 Task 引用，并发地更新 progress / status
  - Task.result 存"业务结果"（experiment_id 等），由 service 在终态填入
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @classmethod
    def terminal(cls) -> list:
        return [cls.SUCCESS, cls.FAILED, cls.CANCELLED]


class TaskType(str, Enum):
    """任务类型（决定 service 派发到哪个执行器）"""
    BACKTEST = "backtest"
    OPTIMIZER = "optimizer"
    WALK_FORWARD = "walk_forward"
    VALIDATION = "validation"
    RUNTIME_START = "runtime_start"
    RUNTIME_STOP = "runtime_stop"
    REPORT = "report"
    OTHER = "other"


@dataclass(slots=True)
class Task:
    """
    任务模型

    字段：
      id            任务 ID
      type          TaskType
      status        TaskStatus
      progress      0.0 ~ 100.0
      message       描述（"loading data" / "failed: ..."）
      created_at    ISO 字符串
      started_at    开始时间
      finished_at   结束时间
      metadata      自定义元信息（strategy_id / params / dataset ...）
      result        业务结果（success 时填：experiment_id 等）
      error         错误（failed 时填）
    """
    id: str
    type: str = TaskType.OTHER.value
    status: str = TaskStatus.PENDING.value
    progress: float = 0.0
    message: str = ""
    created_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    # ---------------------------------------------------------
    # 行为（不修改状态，仅计算）
    # ---------------------------------------------------------
    @property
    def is_terminal(self) -> bool:
        try:
            return TaskStatus(self.status) in TaskStatus.terminal()
        except ValueError:
            return False

    @property
    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING.value

    @property
    def duration_sec(self) -> Optional[float]:
        if not self.started_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at)
            end = (
                datetime.fromisoformat(self.finished_at)
                if self.finished_at
                else datetime.utcnow()
            )
            return (end - start).total_seconds()
        except Exception:
            return None

    # ---------------------------------------------------------
    # 序列化
    # ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Task":
        # 容错：只取已知字段，缺省走默认
        return cls(
            id=d.get("id", ""),
            type=d.get("type", TaskType.OTHER.value),
            status=d.get("status", TaskStatus.PENDING.value),
            progress=float(d.get("progress", 0.0) or 0.0),
            message=d.get("message", "") or "",
            created_at=d.get("created_at", "") or "",
            started_at=d.get("started_at"),
            finished_at=d.get("finished_at"),
            metadata=dict(d.get("metadata") or {}),
            result=dict(d.get("result") or {}),
            error=d.get("error"),
        )


def now_iso() -> str:
    return datetime.utcnow().isoformat()


def new_task(
    type_: str,
    task_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Task:
    """构造一个 PENDING 任务（task_id 必须由调用方生成）"""
    return Task(
        id=task_id,
        type=type_,
        status=TaskStatus.PENDING.value,
        created_at=now_iso(),
        metadata=dict(metadata or {}),
    )
