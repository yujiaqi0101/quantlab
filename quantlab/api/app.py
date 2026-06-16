"""
QuantLab Studio — FastAPI 主入口

启动方式：
  uvicorn quantlab.api.app:app --reload --port 8000

或：
  python -m quantlab.api.app
"""

from __future__ import annotations

import asyncio
import json
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .strategies import router as strategies_router
from .datasets import router as datasets_router
from .backtests import router as backtests_router
from .tasks import router as tasks_router
from .experiments import router as experiments_router
from .factors import router as factors_router
from .signals import router as signals_router
from .research import router as research_router
from .strategy_builder import router as strategy_builder_router


# ---- App 创建 ----
app = FastAPI(
    title="QuantLab Studio API",
    version="4.2.0",
    description="V4.2 Strategy Workspace 后端 API",
)

# ---- CORS（前端开发用）----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 注册路由 ----
app.include_router(strategies_router)
app.include_router(datasets_router)
app.include_router(backtests_router)
app.include_router(tasks_router)
app.include_router(experiments_router)
app.include_router(factors_router)
app.include_router(signals_router)
app.include_router(research_router)
app.include_router(strategy_builder_router)


# ---- WebSocket 任务推送 ----
class TaskWSManager:
    """管理 WebSocket 连接，任务状态变化时推送"""

    def __init__(self) -> None:
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def broadcast(self, message: dict) -> None:
        data = json.dumps(message, ensure_ascii=False, default=str)
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self.active -= dead


ws_manager = TaskWSManager()


@app.websocket("/api/v1/ws/tasks")
async def ws_tasks(websocket: WebSocket):
    """WebSocket 端点：实时推送任务状态变化"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接，等待客户端消息（心跳）
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ---- TaskManager 订阅：状态变化 → WebSocket 推送 ----
def _on_task_change(task) -> None:
    """TaskManager 回调：任务状态变化时广播"""
    msg = task.to_dict()
    # 用 asyncio.run_coroutine_threadsafe 从非 async 上下文调度
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(ws_manager.broadcast(msg))
    except RuntimeError:
        pass


def _setup_task_subscriber() -> None:
    """启动时注册 TaskManager 订阅"""
    from ..runtime.task_manager import get_task_manager
    mgr = get_task_manager()
    mgr.subscribe(_on_task_change)


# ---- 启动事件 ----
@app.on_event("startup")
async def on_startup():
    _setup_task_subscriber()


# ---- 健康检查 ----
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "version": "4.2.0"}


# ---- 直接运行 ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("quantlab.api.app:app", host="0.0.0.0", port=8000, reload=True)
