"""
Label Nodes — 标签节点
  FutureReturnNode / DirectionNode
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType
from .transform import apply_per_symbol


class FutureReturnNode(ResearchNode):
    """未来 N 期收益率。"""

    id = "future_return"
    category = NodeCategory.LABEL
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="future_return", type=PortType.FRAME)]
    parameters = {"horizon": 5}
    metadata = NodeMetadata(description="future N-period return", cost=1, tags=["label"])

    def __init__(self, horizon: int = 5, **kw: Any) -> None:
        super().__init__(horizon=horizon, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("FutureReturnNode needs upstream 'close'")
        col = frame.data.columns[0]
        h = self.parameters["horizon"]

        def _fn(df: pd.DataFrame) -> pd.DataFrame:
            return (df[col].shift(-h) / df[col] - 1).to_frame(name="future_return")

        result = apply_per_symbol(frame.data, _fn)
        return ResearchFrame.from_panel(result, name="future_return")


class DirectionNode(ResearchNode):
    """未来 N 期涨跌方向 (1 / 0 / -1)。"""

    id = "direction"
    category = NodeCategory.LABEL
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="direction", type=PortType.FRAME)]
    parameters = {"horizon": 5}
    metadata = NodeMetadata(description="future direction (1/0/-1)", cost=1, tags=["label"])

    def __init__(self, horizon: int = 5, **kw: Any) -> None:
        super().__init__(horizon=horizon, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("DirectionNode needs upstream 'close'")
        col = frame.data.columns[0]
        h = self.parameters["horizon"]

        def _fn(df: pd.DataFrame) -> pd.DataFrame:
            fr = df[col].shift(-h) / df[col] - 1
            return np.sign(fr).to_frame(name="direction")

        result = apply_per_symbol(frame.data, _fn)
        return ResearchFrame.from_panel(result, name="direction")
