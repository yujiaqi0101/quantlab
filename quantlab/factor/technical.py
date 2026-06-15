"""
Technical Factors — V4.6 技术因子库

内置因子:
  - MA(period)       移动均线
  - RSI(period)      相对强弱指标
  - MOM(period)      动量
  - ATR(period)      平均真实波幅
  - BOLL(period, k)  布林带（上/中/下）
  - VOL(period)      成交量均值
"""

from __future__ import annotations

import pandas as pd
import numpy as np

from .base import Factor


# ==================================================================
# MA
# ==================================================================
class MAFactor(Factor):
    """移动均线因子"""

    def __init__(self, period: int = 20):
        self.period = int(period)

    @property
    def name(self) -> str:
        return f"MA{self.period}"

    @property
    def category(self) -> str:
        return "trend"

    @property
    def description(self) -> str:
        return f"Simple Moving Average (period={self.period})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"].rolling(self.period).mean()


# ==================================================================
# RSI
# ==================================================================
class RSIFactor(Factor):
    """相对强弱指标"""

    def __init__(self, period: int = 14):
        self.period = int(period)

    @property
    def name(self) -> str:
        return f"RSI{self.period}"

    @property
    def category(self) -> str:
        return "momentum"

    @property
    def description(self) -> str:
        return f"Relative Strength Index (period={self.period})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        close = df["close"]
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(self.period).mean()
        loss = (-delta).clip(lower=0).rolling(self.period).mean()
        rs = gain / loss.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))


# ==================================================================
# Momentum
# ==================================================================
class MomentumFactor(Factor):
    """动量因子"""

    def __init__(self, period: int = 20):
        self.period = int(period)

    @property
    def name(self) -> str:
        return f"MOM{self.period}"

    @property
    def category(self) -> str:
        return "momentum"

    @property
    def description(self) -> str:
        return f"Momentum (period={self.period}): close/close.shift({self.period}) - 1"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["close"] / df["close"].shift(self.period) - 1


# ==================================================================
# ATR
# ==================================================================
class ATRFactor(Factor):
    """平均真实波幅"""

    def __init__(self, period: int = 14):
        self.period = int(period)

    @property
    def name(self) -> str:
        return f"ATR{self.period}"

    @property
    def category(self) -> str:
        return "volatility"

    @property
    def description(self) -> str:
        return f"Average True Range (period={self.period})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rolling(self.period).mean()


# ==================================================================
# Bollinger Band
# ==================================================================
class BOLLUpperFactor(Factor):
    def __init__(self, period: int = 20, k: float = 2.0):
        self.period = int(period)
        self.k = float(k)

    @property
    def name(self) -> str:
        return f"BOLL_U{self.period}"

    @property
    def category(self) -> str:
        return "volatility"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(self.period).mean()
        s = df["close"].rolling(self.period).std()
        return m + self.k * s


class BOLLLowerFactor(Factor):
    def __init__(self, period: int = 20, k: float = 2.0):
        self.period = int(period)
        self.k = float(k)

    @property
    def name(self) -> str:
        return f"BOLL_L{self.period}"

    @property
    def category(self) -> str:
        return "volatility"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        m = df["close"].rolling(self.period).mean()
        s = df["close"].rolling(self.period).std()
        return m - self.k * s


# ==================================================================
# Volume
# ==================================================================
class VOLFactor(Factor):
    """成交量均值"""

    def __init__(self, period: int = 20):
        self.period = int(period)

    @property
    def name(self) -> str:
        return f"VOL{self.period}"

    @property
    def category(self) -> str:
        return "volume"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        return df["volume"].rolling(self.period).mean()


# ==================================================================
# 便捷：注册所有内置技术因子
# ==================================================================
def register_all_technical(registry) -> int:
    """注册所有内置技术因子，返回注册数量"""
    count = 0
    for period in [5, 10, 20, 60]:
        registry.register(lambda p=period: MAFactor(p))
        count += 1
    for period in [6, 14, 28]:
        registry.register(lambda p=period: RSIFactor(p))
        count += 1
    for period in [5, 10, 20, 60]:
        registry.register(lambda p=period: MomentumFactor(p))
        count += 1
    for period in [14, 28]:
        registry.register(lambda p=period: ATRFactor(p))
        count += 1
    for period in [20]:
        registry.register(lambda p=period: BOLLUpperFactor(p))
        registry.register(lambda p=period: BOLLLowerFactor(p))
        count += 2
    for period in [5, 20]:
        registry.register(lambda p=period: VOLFactor(p))
        count += 1
    return count
