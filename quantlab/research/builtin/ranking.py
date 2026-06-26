"""
Ranking Nodes — 截面排名节点
  CrossSectionRankNode / PercentileNode
"""
from __future__ import annotations

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType


class CrossSectionRankNode(ResearchNode):
    """按 datetime 横截面排名 (pct=True, 0~1)。"""

    id = "cs_rank"
    category = NodeCategory.RANKING
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="cs_rank", type=PortType.FRAME)]
    metadata = NodeMetadata(description="cross-section rank (pct)", cost=2, tags=["rank"])

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("CrossSectionRankNode needs upstream 'close'")
        col = frame.data.columns[0]
        ranked = frame.data.groupby(level="datetime")[col].rank(pct=True)
        return ResearchFrame.from_panel(ranked.to_frame(name="cs_rank"), name="cs_rank")


class PercentileNode(ResearchNode):
    """按 datetime 横截面百分位 (0~1)。"""

    id = "percentile"
    category = NodeCategory.RANKING
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="percentile", type=PortType.FRAME)]
    metadata = NodeMetadata(description="cross-section percentile", cost=2, tags=["rank"])

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("PercentileNode needs upstream 'close'")
        col = frame.data.columns[0]
        pct = frame.data.groupby(level="datetime")[col].rank(pct=True)
        return ResearchFrame.from_panel(pct.to_frame(name="percentile"), name="percentile")
