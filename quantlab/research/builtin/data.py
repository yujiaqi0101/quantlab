"""
Data Nodes — 原始数据节点

从上游 OHLCV 面板提取单列，输出单列 ResearchFrame。
  CloseNode / HighNode / LowNode / OpenNode / VolumeNode / VWAPNode
"""
from __future__ import annotations

from typing import Any

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType


class ColumnDataNode(ResearchNode):
    """提取面板中指定列的节点基类。"""

    column: str = ""
    category: NodeCategory = NodeCategory.DATA
    inputs = [Port(name="frame", type=PortType.FRAME, description="OHLCV panel")]
    metadata = NodeMetadata(description="column extractor", cost=1)

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        col = self.column or self.id
        self.outputs = [Port(name=col, type=PortType.FRAME)]

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError(
                f"ColumnDataNode '{self.id}' needs upstream 'frame' in frame_store"
            )
        col = self.column
        if col not in frame.data.columns:
            raise ValueError(
                f"column '{col}' not in frame columns: {list(frame.data.columns)}"
            )
        data = frame.data[[col]].copy()
        return ResearchFrame.from_panel(data, name=col)


class OpenNode(ColumnDataNode):
    id = "open"
    column = "open"
    metadata = NodeMetadata(description="open price", cost=1, tags=["price"])


class HighNode(ColumnDataNode):
    id = "high"
    column = "high"
    metadata = NodeMetadata(description="high price", cost=1, tags=["price"])


class LowNode(ColumnDataNode):
    id = "low"
    column = "low"
    metadata = NodeMetadata(description="low price", cost=1, tags=["price"])


class CloseNode(ColumnDataNode):
    id = "close"
    column = "close"
    metadata = NodeMetadata(description="close price", cost=1, tags=["price"])


class VolumeNode(ColumnDataNode):
    id = "volume"
    column = "volume"
    metadata = NodeMetadata(description="trading volume", cost=1, tags=["volume"])


class VWAPNode(ColumnDataNode):
    """VWAP：若面板已有 vwap 列则直接提取；否则用 (high+low+close)/3 近似。"""

    id = "vwap"
    column = "vwap"
    metadata = NodeMetadata(description="VWAP", cost=1, tags=["price"])

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError("VWAPNode needs upstream 'frame'")
        if "vwap" in frame.data.columns:
            data = frame.data[["vwap"]].copy()
        else:
            approx = (
                frame.data["high"] + frame.data["low"] + frame.data["close"]
            ) / 3.0
            data = approx.to_frame(name="vwap")
        return ResearchFrame.from_panel(data, name="vwap")
