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

from .fidelity import router as fidelity_router
from .alpha_aware import router as alpha_aware_router
from .production import router as production_router
from .observe import router as observe_router
from .live import router as live_router
from .ml import router as ml_router
from .experiments import router as experiments_router
from .datasets import router as datasets_router
from .strategies import router as strategies_router


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
app.include_router(fidelity_router)
app.include_router(alpha_aware_router)
app.include_router(production_router)
app.include_router(observe_router)
app.include_router(live_router)
app.include_router(ml_router)
app.include_router(experiments_router)
app.include_router(datasets_router)
app.include_router(strategies_router)


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


# ---- 启动事件 ----
@app.on_event("startup")
async def on_startup():
    # 初始化统一 DatasetManager（自动从 DB 恢复 + 种子化示例数据）
    try:
        from ..ml.dataset import get_dataset_manager
        get_dataset_manager()
    except Exception as exc:  # 启动失败不阻塞服务
        import logging
        logging.getLogger("quantlab.api.app").warning("dataset manager init failed on startup: %s", exc)


# ---- 健康检查 ----
@app.get("/api/v1/health")
async def health_check():
    """简单存活检查"""
    return {"status": "ok", "version": "4.2.0"}


@app.get("/api/v1/system/status")
async def system_status():
    """系统详细状态：Database / Artifact Store / Task Queue / Event Bus / Config / Logging"""
    from ..infra.health import get_health_checker
    checker = get_health_checker()
    return checker.check_all()


@app.get("/api/v1/system/metrics")
async def system_metrics():
    """系统指标 Dashboard 数据"""
    from ..infra.metrics import get_system_metrics
    return get_system_metrics().dashboard()


@app.get("/api/v1/system/logs")
async def system_logs(filename: str = "app.log", lines: int = 100):
    """读取日志文件"""
    from ..infra.logging import read_log, list_log_files
    return {
        "files": list_log_files(),
        "content": read_log(filename, lines),
    }


# ---- 直接运行 ----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("quantlab.api.app:app", host="0.0.0.0", port=8000, reload=True)
