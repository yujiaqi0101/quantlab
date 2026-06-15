"""
DTO — Task

**从 domain.task 重新导出**。
之所以保留这个文件：
  - 上层（API、CLI、Web）已经 `from quantlab.dto import Task`
  - 当 dto 扩展为"传输层"时（例如 to_response DTO），可以加方法而 domain 不动
"""

from ..domain.task import (
    Task,
    TaskStatus,
    TaskType,
    new_task,
)


__all__ = [
    "Task",
    "TaskStatus",
    "TaskType",
    "new_task",
]
