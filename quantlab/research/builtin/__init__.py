"""
Builtin Nodes — 内置节点库

9 类节点：
  DATA       : Open/High/Low/Close/Volume/VWAP
  TRANSFORM  : Return/Diff/Log/ZScore/Normalize
  INDICATOR  : RSI/SMA/EMA/MACD/ATR
  AGGREGATION: RollingMean/Std/Max/Min
  RANKING    : CrossSectionRank/Percentile
  LABEL      : FutureReturn/Direction
"""
from .aggregation import (
    RollingMaxNode,
    RollingMeanNode,
    RollingMinNode,
    RollingStdNode,
)
from .alpha import Alpha014Node, AlphaNode
from .custom import CustomNode, LambdaNode
from .data import CloseNode, HighNode, LowNode, OpenNode, VolumeNode, VWAPNode
from .indicator import ATRNode, EMANode, MACDNode, RSINode, SMANode
from .label import DirectionNode, FutureReturnNode
from .ranking import CrossSectionRankNode, PercentileNode
from .selection import LiquidityFilterNode, UniverseFilterNode
from .transform import (
    DiffNode,
    LogNode,
    NormalizeNode,
    ReturnNode,
    ZScoreNode,
)

__all__ = [
    # DATA
    "OpenNode",
    "HighNode",
    "LowNode",
    "CloseNode",
    "VolumeNode",
    "VWAPNode",
    # TRANSFORM
    "ReturnNode",
    "DiffNode",
    "LogNode",
    "ZScoreNode",
    "NormalizeNode",
    # INDICATOR
    "RSINode",
    "SMANode",
    "EMANode",
    "MACDNode",
    "ATRNode",
    # AGGREGATION
    "RollingMeanNode",
    "RollingStdNode",
    "RollingMaxNode",
    "RollingMinNode",
    # RANKING
    "CrossSectionRankNode",
    "PercentileNode",
    # LABEL
    "FutureReturnNode",
    "DirectionNode",
    # ALPHA
    "AlphaNode",
    "Alpha014Node",
    # SELECTION
    "UniverseFilterNode",
    "LiquidityFilterNode",
    # CUSTOM
    "CustomNode",
    "LambdaNode",
]
