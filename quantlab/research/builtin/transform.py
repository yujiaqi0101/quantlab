"""
Transform Nodes — 数据变换节点
  ReturnNode / DiffNode / LogNode / ZScoreNode / NormalizeNode
"""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd

from ..context import ExecutionContext
from ..frame import ResearchFrame
from ..node.base import ResearchNode
from ..node.manifest import NodeCategory, NodeMetadata
from ..node.ports import Port, PortType


def apply_per_symbol(
    df: pd.DataFrame, func: Callable[[pd.DataFrame], Any]
) -> pd.DataFrame:
    """对 MultiIndex(datetime, symbol) DataFrame 按 symbol 分组应用时序函数。

    func 接收单标的 DataFrame (DatetimeIndex)，返回 DataFrame 或 Series。
    """
    parts = []
    for sym, sub in df.groupby(level="symbol"):
        single = sub.droplevel("symbol")
        out = func(single)
        if isinstance(out, pd.Series):
            out = out.to_frame(name=out.name or "value")
        out = out.copy()
        out["symbol"] = sym
        out.set_index("symbol", append=True, inplace=True)
        parts.append(out)
    return pd.concat(parts).reorder_levels(["datetime", "symbol"])


class _SingleColumnTransform(ResearchNode):
    """单列时序变换基类：输入单列 frame，按 symbol 分组应用变换。"""

    category: NodeCategory = NodeCategory.TRANSFORM
    inputs = [Port(name="close", type=PortType.FRAME)]
    output_name: str = "transform"

    def __init__(self, **params: Any) -> None:
        super().__init__(**params)
        self.outputs = [Port(name=self.output_name, type=PortType.FRAME)]

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError(f"{self.id} needs upstream 'close' in frame_store")
        col = frame.data.columns[0]

        def _fn(df: pd.DataFrame) -> pd.DataFrame:
            out = self.transform(df[col])
            return out.to_frame(name=self.output_name)

        result = apply_per_symbol(frame.data, _fn)
        return ResearchFrame.from_panel(result, name=self.output_name)


class ReturnNode(_SingleColumnTransform):
    id = "return"
    output_name = "return"
    parameters = {"period": 1}
    metadata = NodeMetadata(description="pct_change return", cost=1, tags=["return"])

    def __init__(self, period: int = 1, **kw: Any) -> None:
        super().__init__(period=period, **kw)

    def transform(self, series: pd.Series) -> pd.Series:
        return series.pct_change(self.parameters["period"])


class DiffNode(_SingleColumnTransform):
    id = "diff"
    output_name = "diff"
    parameters = {"period": 1}
    metadata = NodeMetadata(description="diff", cost=1)

    def __init__(self, period: int = 1, **kw: Any) -> None:
        super().__init__(period=period, **kw)

    def transform(self, series: pd.Series) -> pd.Series:
        return series.diff(self.parameters["period"])


class LogNode(_SingleColumnTransform):
    id = "log"
    output_name = "log"
    metadata = NodeMetadata(description="log price", cost=1)

    def transform(self, series: pd.Series) -> pd.Series:
        return np.log(series)


class ZScoreNode(_SingleColumnTransform):
    id = "zscore"
    output_name = "zscore"
    parameters = {"window": 20}
    metadata = NodeMetadata(description="rolling z-score", cost=2, tags=["normalize"])

    def __init__(self, window: int = 20, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def transform(self, series: pd.Series) -> pd.Series:
        w = self.parameters["window"]
        mean = series.rolling(w).mean()
        std = series.rolling(w).std()
        return (series - mean) / std.replace(0, np.nan)


class NormalizeNode(_SingleColumnTransform):
    id = "normalize"
    output_name = "normalize"
    parameters = {"window": 20}
    metadata = NodeMetadata(description="min-max normalize", cost=2, tags=["normalize"])

    def __init__(self, window: int = 20, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def transform(self, series: pd.Series) -> pd.Series:
        w = self.parameters["window"]
        mn = series.rolling(w).min()
        mx = series.rolling(w).max()
        return (series - mn) / (mx - mn).replace(0, np.nan)
