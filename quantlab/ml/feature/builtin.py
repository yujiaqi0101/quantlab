"""
Builtin Features — 内置特征库

ML Lab 第二部分：内置特征

  RSI14 / RSI21
  MACD
  ATR
  Momentum20
  VolumeZScore
  BollingerBands
  EMACross
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Feature


# ==================================================================
# RSI
# ==================================================================

class RSI(Feature):
    """RSI 相对强弱指标"""
    name: str = "RSI"
    description: str = "Relative Strength Index"
    category: str = "mean_reversion"
    tags: list = ["momentum", "oscillator"]
    required_columns: list = ["close"]

    def __init__(self, period: int = 14) -> None:
        self.params = {"period": period}
        self.feature_id = f"rsi{period}"
        self.name = f"RSI{period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).rename(self.feature_id)


# ==================================================================
# MACD
# ==================================================================

class MACD(Feature):
    """MACD 移动平均收敛发散"""
    name: str = "MACD"
    description: str = "Moving Average Convergence Divergence"
    category: str = "trend"
    tags: list = ["momentum", "trend"]
    required_columns: list = ["close"]

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        self.params = {"fast": fast, "slow": slow, "signal": signal}
        self.feature_id = f"macd_{fast}_{slow}_{signal}"
        self.name = f"MACD({fast},{slow},{signal})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params["fast"]
        slow = self.params["slow"]
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        return macd.rename(self.feature_id)


# ==================================================================
# ATR
# ==================================================================

class ATR(Feature):
    """ATR 平均真实波幅"""
    name: str = "ATR"
    description: str = "Average True Range"
    category: str = "volatility"
    tags: list = ["volatility"]
    required_columns: list = ["high", "low", "close"]

    def __init__(self, period: int = 14) -> None:
        self.params = {"period": period}
        self.feature_id = f"atr{period}"
        self.name = f"ATR{period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        high = df["high"]
        low = df["low"]
        close = df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
        return atr.rename(self.feature_id)


# ==================================================================
# Momentum
# ==================================================================

class Momentum(Feature):
    """动量：过去 N 期收益率"""
    name: str = "Momentum"
    description: str = "Past N-period return"
    category: str = "momentum"
    tags: list = ["momentum", "return"]
    required_columns: list = ["close"]

    def __init__(self, period: int = 20) -> None:
        self.params = {"period": period}
        self.feature_id = f"momentum{period}"
        self.name = f"Momentum{period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        mom = df["close"].pct_change(period)
        return mom.rename(self.feature_id)


# ==================================================================
# VolumeZScore
# ==================================================================

class VolumeZScore(Feature):
    """成交量 Z-Score"""
    name: str = "VolumeZScore"
    description: str = "Volume Z-Score over rolling window"
    category: str = "volume"
    tags: list = ["volume", "normalization"]
    required_columns: list = ["volume"]

    def __init__(self, period: int = 20) -> None:
        self.params = {"period": period}
        self.feature_id = f"vol_zscore{period}"
        self.name = f"VolumeZScore{period}"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        vol = df["volume"]
        mean = vol.rolling(period).mean()
        std = vol.rolling(period).std()
        zscore = (vol - mean) / std.replace(0, np.nan)
        return zscore.fillna(0).rename(self.feature_id)


# ==================================================================
# BollingerBands
# ==================================================================

class BollingerBands(Feature):
    """布林带 %B（价格在带中的位置）"""
    name: str = "BollingerBands"
    description: str = "Bollinger Bands %B"
    category: str = "mean_reversion"
    tags: list = ["mean_reversion", "volatility"]
    required_columns: list = ["close"]

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        self.params = {"period": period, "num_std": num_std}
        self.feature_id = f"bb_pct_b_{period}_{num_std}"
        self.name = f"BB%b({period},{num_std})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        num_std = self.params["num_std"]
        ma = df["close"].rolling(period).mean()
        std = df["close"].rolling(period).std()
        upper = ma + num_std * std
        lower = ma - num_std * std
        pct_b = (df["close"] - lower) / (upper - lower).replace(0, np.nan)
        return pct_b.fillna(0.5).rename(self.feature_id)


# ==================================================================
# EMACross
# ==================================================================

class EMACross(Feature):
    """EMA 交叉信号（快线 - 慢线 的标准化差值）"""
    name: str = "EMACross"
    description: str = "EMA crossover signal (normalized)"
    category: str = "trend"
    tags: list = ["trend", "ema"]
    required_columns: list = ["close"]

    def __init__(self, fast: int = 12, slow: int = 26) -> None:
        self.params = {"fast": fast, "slow": slow}
        self.feature_id = f"ema_cross_{fast}_{slow}"
        self.name = f"EMACross({fast},{slow})"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        fast = self.params["fast"]
        slow = self.params["slow"]
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        signal = (ema_fast - ema_slow) / ema_slow.replace(0, np.nan)
        return signal.fillna(0).rename(self.feature_id)


# ==================================================================
# 注册所有内置特征
# ==================================================================

def register_all_builtin(registry) -> int:
    """注册所有内置特征"""
    builtins = [
        RSI(14),
        RSI(21),
        MACD(12, 26, 9),
        ATR(14),
        Momentum(10),
        Momentum(20),
        Momentum(60),
        VolumeZScore(20),
        BollingerBands(20, 2.0),
        EMACross(12, 26),
    ]
    for f in builtins:
        registry.register(f)
    return len(builtins)
