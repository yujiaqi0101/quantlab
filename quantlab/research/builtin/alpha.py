"""
Alpha Nodes — Alpha 因子节点

  AlphaNode     — Alpha 因子基类 (接收 OHLCV panel)
  Alpha014Node  — WorldQuant Alpha#14 示例
"""
from __future__ import annotations

import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType
from .transform import apply_per_symbol


class AlphaNode(ResearchNode):
    """Alpha 因子基类：接收 OHLCV panel，子类实现 alpha()。"""

    category: NodeCategory = NodeCategory.ALPHA
    inputs = [Port(name="frame", type=PortType.FRAME, description="OHLCV panel")]
    metadata = NodeMetadata(description="alpha factor", cost=3, tags=["alpha"])

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError(f"{self.id} needs upstream 'frame' (OHLCV)")
        result = self.alpha(frame.data)
        return ResearchFrame.from_panel(result, name=self.id)

    def alpha(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError


class Alpha014Node(AlphaNode):
    """WorldQuant Alpha#14:
    ((CLOSE - DELAY(CLOSE,5)) * DELAY(CORR(VWAP, MEAN(VOLUME,20), 5), 5)) * -1
    """

    id = "alpha014"
    outputs = [Port(name="alpha014", type=PortType.FRAME)]
    metadata = NodeMetadata(
        description="WQ Alpha#14", cost=3, tags=["alpha", "worldquant"]
    )

    def alpha(self, df: pd.DataFrame) -> pd.DataFrame:
        def _alpha(d: pd.DataFrame) -> pd.DataFrame:
            close = d["close"]
            volume = d["volume"]
            vwap = (d["high"] + d["low"] + d["close"]) / 3.0
            vol_mean = volume.rolling(20).mean()
            corr = vwap.rolling(5).corr(vol_mean)
            corr_delayed = corr.shift(5)
            close_diff = close - close.shift(5)
            result = (close_diff * corr_delayed) * -1
            return result.to_frame(name="alpha014")

        return apply_per_symbol(df, _alpha)
