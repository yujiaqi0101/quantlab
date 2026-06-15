"""
Task API — 任务列表 / 详情

对应前端 Task Panel（底部任务栏）

端点：
  GET /api/v1/tasks        任务列表
  GET /api/v1/tasks/{id}   任务详情
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from ..runtime.task_manager import get_task_manager


router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("")
async def api_list_tasks(
    status: Optional[str] = Query(None, description="按状态过滤: PENDING/RUNNING/SUCCESS/FAILED/CANCELLED"),
    type_: Optional[str] = Query(None, description="按类型过滤: backtest/optimizer/..."),
) -> List[Dict[str, Any]]:
    """任务列表（最新在前）"""
    mgr = get_task_manager()
    tasks = mgr.list(status=status, type_=type_)
    return [t.to_dict() for t in tasks]


@router.get("/{task_id}")
async def api_get_task(task_id: str) -> Dict[str, Any]:
    """任务详情（含进度 / 状态 / 结果）"""
    mgr = get_task_manager()
    task = mgr.get(task_id)
    if task is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task.to_dict()
