"""
ExecutionContext & FrameStore — 节点执行上下文

阶段2最小版本：FrameStore 提供端口名 → ResearchFrame 存储。
阶段3 Executor 会扩展 ExecutionContext 加入缓存/增量支持。
"""
from __future__ import annotations

from typing import Any, Dict, Iterator, Optional

from .frame import ResearchFrame


class FrameStore:
    """端口名 → ResearchFrame 的内存存储。"""

    def __init__(self) -> None:
        self._frames: Dict[str, ResearchFrame] = {}

    def set(self, name: str, frame: ResearchFrame) -> None:
        self._frames[name] = frame

    def get(self, name: str) -> Optional[ResearchFrame]:
        return self._frames.get(name)

    def has(self, name: str) -> bool:
        return name in self._frames

    def names(self) -> Iterator[str]:
        return iter(self._frames)

    def __repr__(self) -> str:
        return f"FrameStore({list(self._frames)})"


class ExecutionContext:
    """节点计算上下文。阶段3 Executor 会扩展加入 cache/incremental 支持。"""

    def __init__(
        self,
        frame_store: Optional[FrameStore] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._frame_store = frame_store or FrameStore()
        self._params = params or {}

    @property
    def frame_store(self) -> FrameStore:
        return self._frame_store

    def get(self, name: str) -> Optional[ResearchFrame]:
        return self._frame_store.get(name)

    def set(self, name: str, frame: ResearchFrame) -> None:
        self._frame_store.set(name, frame)

    @property
    def params(self) -> Dict[str, Any]:
        return self._params
