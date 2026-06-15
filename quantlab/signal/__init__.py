"""
quantlab.signal — V4.6 Signal 层

三级模型：Factor → Signal → Strategy

Signal: 因子值(连续) → 信号值(离散 ∈ {-1, 0, 1})

与旧 quantlab.signals 的关系：
  - signals/ 是 SignalStrategy (ABC)，直接输出 DataFrame
  - signal/ 是 Signal (ABC)，接收因子值输出 Series
  - 两者共存，新代码推荐用 signal/
"""

from .base import Signal, MultiFactorSignal
from .signal_engine import SignalEngine
from .threshold import ThresholdSignal, BandSignal
from .crossover import CrossoverSignal, ZeroCrossoverSignal
from .composite import AndSignal, OrSignal, NotSignal, MajoritySignal
from .filters import HoldFilter, ConfirmFilter, CooldownFilter, StatefulSignal


__all__ = [
    "Signal",
    "MultiFactorSignal",
    "SignalEngine",
    "ThresholdSignal",
    "BandSignal",
    "CrossoverSignal",
    "ZeroCrossoverSignal",
    # composite
    "AndSignal",
    "OrSignal",
    "NotSignal",
    "MajoritySignal",
    # filters
    "HoldFilter",
    "ConfirmFilter",
    "CooldownFilter",
    "StatefulSignal",
]
