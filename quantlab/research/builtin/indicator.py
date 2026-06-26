"""
Indicator Nodes — 技术指标节点
  RSINode / SMANode / EMANode / MACDNode / ATRNode
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


class RSINode(ResearchNode):
    id = "rsi"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="rsi", type=PortType.FRAME)]
    parameters = {"window": 14}
    metadata = NodeMetadata(
        description="Relative Strength Index", cost=2, tags=["momentum", "oscillator"]
    )

    def __init__(self, window: int = 14, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("RSINode needs upstream 'close'")
        col = frame.data.columns[0]
        window = self.parameters["window"]

        def _rsi(df: pd.DataFrame) -> pd.DataFrame:
            delta = df[col].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1 / window, min_periods=window).mean()
            avg_loss = loss.ewm(alpha=1 / window, min_periods=window).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50).to_frame(name="rsi")

        result = apply_per_symbol(frame.data, _rsi)
        return ResearchFrame.from_panel(result, name="rsi")


class SMANode(ResearchNode):
    id = "sma"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="sma", type=PortType.FRAME)]
    parameters = {"window": 20}
    metadata = NodeMetadata(description="Simple Moving Average", cost=1, tags=["trend"])

    def __init__(self, window: int = 20, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("SMANode needs upstream 'close'")
        col = frame.data.columns[0]
        window = self.parameters["window"]

        def _sma(df: pd.DataFrame) -> pd.DataFrame:
            return df[col].rolling(window).mean().to_frame(name="sma")

        result = apply_per_symbol(frame.data, _sma)
        return ResearchFrame.from_panel(result, name="sma")


class EMANode(ResearchNode):
    id = "ema"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="ema", type=PortType.FRAME)]
    parameters = {"window": 12}
    metadata = NodeMetadata(
        description="Exponential Moving Average", cost=1, tags=["trend"]
    )

    def __init__(self, window: int = 12, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("EMANode needs upstream 'close'")
        col = frame.data.columns[0]
        window = self.parameters["window"]

        def _ema(df: pd.DataFrame) -> pd.DataFrame:
            return df[col].ewm(span=window, adjust=False).mean().to_frame(name="ema")

        result = apply_per_symbol(frame.data, _ema)
        return ResearchFrame.from_panel(result, name="ema")


class MACDNode(ResearchNode):
    id = "macd"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="close", type=PortType.FRAME)]
    outputs = [Port(name="macd", type=PortType.FRAME)]
    parameters = {"fast": 12, "slow": 26, "signal": 9}
    metadata = NodeMetadata(
        description="Moving Average Convergence Divergence", cost=2, tags=["trend"]
    )

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9, **kw: Any) -> None:
        super().__init__(fast=fast, slow=slow, signal=signal, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("close")
        if frame is None:
            raise ValueError("MACDNode needs upstream 'close'")
        col = frame.data.columns[0]
        fast = self.parameters["fast"]
        slow = self.parameters["slow"]

        def _macd(df: pd.DataFrame) -> pd.DataFrame:
            ema_fast = df[col].ewm(span=fast, adjust=False).mean()
            ema_slow = df[col].ewm(span=slow, adjust=False).mean()
            macd = ema_fast - ema_slow
            return macd.to_frame(name="macd")

        result = apply_per_symbol(frame.data, _macd)
        return ResearchFrame.from_panel(result, name="macd")


class ATRNode(ResearchNode):
    id = "atr"
    category = NodeCategory.INDICATOR
    inputs = [Port(name="frame", type=PortType.FRAME, description="OHLCV panel")]
    outputs = [Port(name="atr", type=PortType.FRAME)]
    parameters = {"window": 14}
    metadata = NodeMetadata(
        description="Average True Range", cost=2, tags=["volatility"]
    )

    def __init__(self, window: int = 14, **kw: Any) -> None:
        super().__init__(window=window, **kw)

    def compute(self, ctx: ExecutionContext) -> ResearchFrame:
        frame = ctx.frame_store.get("frame")
        if frame is None:
            raise ValueError("ATRNode needs upstream 'frame' (OHLCV)")
        window = self.parameters["window"]

        def _atr(df: pd.DataFrame) -> pd.DataFrame:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            prev_close = close.shift(1)
            tr = pd.concat(
                [
                    high - low,
                    (high - prev_close).abs(),
                    (low - prev_close).abs(),
                ],
                axis=1,
            ).max(axis=1)
            atr = tr.ewm(alpha=1 / window, min_periods=window).mean()
            return atr.to_frame(name="atr")

        result = apply_per_symbol(frame.data, _atr)
        return ResearchFrame.from_panel(result, name="atr")
