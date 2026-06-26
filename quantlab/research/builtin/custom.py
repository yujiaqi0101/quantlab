"""
Custom Node — 用户自定义节点基类
"""
from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType


class CustomNode(ResearchNode):
    """用户自定义节点基类。

    用法：
        class MyNode(CustomNode):
            id = "my_node"
            def compute_func(self, frame, ctx):
                ...  # 返回 DataFrame
    """

    id = "custom"
    category = NodeCategory.CUSTOM
    inputs = [Port(name="frame", type=PortType.FRAME)]
    outputs = [Port(name="custom", type=PortType.FRAME)]
    metadata = NodeMetadata(description="custom node", cost=2, tags=["custom"])

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError(f"{self.id} needs upstream 'frame'")
        result = self.compute_func(frame, ctx)
        if isinstance(result, pd.DataFrame):
            return ResearchFrame.from_panel(result, name=self.id)
        return result

    def compute_func(self, frame: ResearchFrame, ctx: ExecutionContext) -> pd.DataFrame:
        raise NotImplementedError("CustomNode subclass must implement compute_func")


class LambdaNode(CustomNode):
    """快速自定义节点：传入一个 callable。"""

    id = "lambda"

    def __init__(self, func: Callable[[ResearchFrame, ExecutionContext], pd.DataFrame], **kw: Any) -> None:
        super().__init__(**kw)
        self._func = func

    def compute_func(self, frame: ResearchFrame, ctx: ExecutionContext) -> pd.DataFrame:
        return self._func(frame, ctx)
