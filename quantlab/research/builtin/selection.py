"""
Selection Nodes — 标的筛选节点
  UniverseFilterNode / LiquidityFilterNode
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType


class UniverseFilterNode(ResearchNode):
    """按 volume 阈值筛选标的行。"""

    id = "universe_filter"
    category = NodeCategory.SELECTION
    inputs = [Port(name="frame", type=PortType.FRAME, description="OHLCV panel")]
    outputs = [Port(name="filtered", type=PortType.FRAME)]
    parameters = {"min_volume": 100.0}
    metadata = NodeMetadata(description="universe filter by volume", cost=1, tags=["filter"])

    def __init__(self, min_volume: float = 100.0, **kw: Any) -> None:
        super().__init__(min_volume=min_volume, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError("UniverseFilterNode needs upstream 'frame'")
        if "volume" not in frame.data.columns:
            raise ValueError("frame must have 'volume' column")
        min_vol = self.parameters["min_volume"]
        mask = frame.data["volume"] >= min_vol
        return ResearchFrame.from_panel(frame.data[mask], name="filtered")


class LiquidityFilterNode(ResearchNode):
    """按 rolling volume 均值筛选流动性不足的标的。"""

    id = "liquidity_filter"
    category = NodeCategory.SELECTION
    inputs = [Port(name="frame", type=PortType.FRAME, description="OHLCV panel")]
    outputs = [Port(name="liquid", type=PortType.FRAME)]
    parameters = {"window": 20, "min_avg_volume": 100.0}
    metadata = NodeMetadata(description="liquidity filter", cost=2, tags=["filter"])

    def __init__(self, window: int = 20, min_avg_volume: float = 100.0, **kw: Any) -> None:
        super().__init__(window=window, min_avg_volume=min_avg_volume, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError("LiquidityFilterNode needs upstream 'frame'")
        if "volume" not in frame.data.columns:
            raise ValueError("frame must have 'volume' column")
        w = self.parameters["window"]
        min_avg = self.parameters["min_avg_volume"]
        # 按 symbol 计算 rolling volume 均值
        vol = frame.data["volume"]
        rolling_avg = vol.groupby(level="symbol").transform(
            lambda s: s.rolling(w).mean()
        )
        mask = rolling_avg >= min_avg
        return ResearchFrame.from_panel(frame.data[mask], name="liquid")
