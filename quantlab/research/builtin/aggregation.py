"""
Aggregation Nodes — 滚动聚合节点
  RollingMeanNode / RollingStdNode / RollingMaxNode / RollingMinNode
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType
from .transform import apply_per_symbol


class _RollingAgg(ResearchNode):
    """滚动聚合基类：输入单列 frame，按 symbol 分组滚动聚合。"""

    category: NodeCategory = NodeCategory.AGGREGATION
    inputs = [Port(name="close", type=PortType.FRAME)]
    output_name: str = "agg"
    parameters = {"window": 20}
    metadata = NodeMetadata(description="rolling aggregation", cost=1)

    def __init__(self, window: int = 20, **kw: Any) -> None:
        super().__init__(window=window, **kw)
        self.outputs = [Port(name=self.output_name, type=PortType.FRAME)]

    def agg(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError(f"{self.id} needs upstream 'close'")
        col = frame.data.columns[0]
        w = self.parameters["window"]

        def _fn(df: pd.DataFrame) -> pd.DataFrame:
            return self.agg(df[col]).to_frame(name=self.output_name)

        result = apply_per_symbol(frame.data, _fn)
        return ResearchFrame.from_panel(result, name=self.output_name)


class RollingMeanNode(_RollingAgg):
    id = "rolling_mean"
    output_name = "rolling_mean"
    metadata = NodeMetadata(description="rolling mean", cost=1, tags=["agg"])

    def agg(self, series: pd.Series) -> pd.Series:
        return series.rolling(self.parameters["window"]).mean()


class RollingStdNode(_RollingAgg):
    id = "rolling_std"
    output_name = "rolling_std"
    metadata = NodeMetadata(description="rolling std", cost=1, tags=["agg"])

    def agg(self, series: pd.Series) -> pd.Series:
        return series.rolling(self.parameters["window"]).std()


class RollingMaxNode(_RollingAgg):
    id = "rolling_max"
    output_name = "rolling_max"
    metadata = NodeMetadata(description="rolling max", cost=1, tags=["agg"])

    def agg(self, series: pd.Series) -> pd.Series:
        return series.rolling(self.parameters["window"]).max()


class RollingMinNode(_RollingAgg):
    id = "rolling_min"
    output_name = "rolling_min"
    metadata = NodeMetadata(description="rolling min", cost=1, tags=["agg"])

    def agg(self, series: pd.Series) -> pd.Series:
        return series.rolling(self.parameters["window"]).min()
