"""
内置技术指标因子
================
所有因子签名统一: fn(ctx: FactorContext, **params) -> pd.DataFrame
返回 date × symbol 面板。
"""
from __future__ import annotations

from typing import Dict

import numpy as np
import pandas as pd

from ..factors.context import FactorContext
from .registry import get_registry


# ---------- 指标实现 ----------

def ma_factor(ctx: FactorContext, window: int = 5) -> pd.DataFrame:
    """简单移动均线 (SMA): ts_mean(close, window)"""
    return ctx.close.rolling(window, min_periods=window).mean()


def ema_factor(ctx: FactorContext, window: int = 12) -> pd.DataFrame:
    """指数移动均线 (EMA)"""
    return ctx.close.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi_factor(ctx: FactorContext, window: int = 14) -> pd.DataFrame:
    """RSI 相对强弱指标"""
    delta = ctx.close.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    roll_up = up.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    roll_down = down.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = roll_up / roll_down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd_factor(ctx: FactorContext, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD 差值 (DIF - DEA)"""
    ema_fast = ctx.close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = ctx.close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return dif - dea


def bollinger_width(ctx: FactorContext, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    """布林带宽度 (Upper-Lower)/Middle，衡量波动率"""
    ma = ctx.close.rolling(window, min_periods=window).mean()
    std = ctx.close.rolling(window, min_periods=window).std()
    return (2 * k * std) / ma.replace(0, np.nan)


def volume_factor(ctx: FactorContext, window: int = 5) -> pd.DataFrame:
    """成交量比: volume / ts_mean(volume, window)"""
    vol_ma = ctx.volume.rolling(window, min_periods=window).mean()
    return ctx.volume / vol_ma.replace(0, np.nan)


def volatility_factor(ctx: FactorContext, window: int = 20) -> pd.DataFrame:
    """已实现波动率: ts_std(returns, window) * sqrt(252)"""
    ret = ctx.close.pct_change()
    return ret.rolling(window, min_periods=window).std() * np.sqrt(252)


def momentum_factor(ctx: FactorContext, window: int = 20) -> pd.DataFrame:
    """动量: close / delay(close, window) - 1"""
    return ctx.close / ctx.close.shift(window) - 1


def amplitude_factor(ctx: FactorContext, window: int = 20) -> pd.DataFrame:
    """振幅因子: (high - low) / close 的 window 日均值"""
    amp = (ctx.high - ctx.low) / ctx.close.replace(0, np.nan)
    return amp.rolling(window, min_periods=window).mean()


def turnover_factor(ctx: FactorContext, window: int = 5) -> pd.DataFrame:
    """成交量 Z-Score (滚动标准化)"""
    mean = ctx.volume.rolling(window, min_periods=window).mean()
    std = ctx.volume.rolling(window, min_periods=window).std()
    return (ctx.volume - mean) / std.replace(0, np.nan)


# ---------- 注册 ----------

TECHNICAL_FACTORS: Dict[str, dict] = {
    "ma_5":    {"category": "trend",        "description": "5日均线 SMA",       "fn": ma_factor,        "direction": 0, "params": {"window": 5}},
    "ma_10":   {"category": "trend",        "description": "10日均线 SMA",      "fn": ma_factor,        "direction": 0, "params": {"window": 10}},
    "ma_20":   {"category": "trend",        "description": "20日均线 SMA",      "fn": ma_factor,        "direction": 0, "params": {"window": 20}},
    "ma_60":   {"category": "trend",        "description": "60日均线 SMA",      "fn": ma_factor,        "direction": 0, "params": {"window": 60}},
    "ema_12":  {"category": "trend",        "description": "12日指数均线 EMA",  "fn": ema_factor,       "direction": 0, "params": {"window": 12}},
    "ema_26":  {"category": "trend",        "description": "26日指数均线 EMA",  "fn": ema_factor,       "direction": 0, "params": {"window": 26}},
    "rsi_14":  {"category": "momentum",     "description": "14日RSI相对强弱指标","fn": rsi_factor,       "direction": -1, "params": {"window": 14}},
    "macd":    {"category": "trend",        "description": "MACD 动量差值",     "fn": macd_factor,      "direction": 1, "params": {"fast": 12, "slow": 26, "signal": 9}},
    "boll_20": {"category": "volatility",   "description": "20日布林带宽度",    "fn": bollinger_width,  "direction": -1, "params": {"window": 20}},
    "vol_ratio_5": {"category": "volume",   "description": "5日成交量比率",     "fn": volume_factor,    "direction": -1, "params": {"window": 5}},
    "volatility_20": {"category": "volatility", "description": "20日年化波动率", "fn": volatility_factor, "direction": -1, "params": {"window": 20}},
    "mom_20":  {"category": "momentum",     "description": "20日价格动量",      "fn": momentum_factor,  "direction": 1, "params": {"window": 20}},
    "mom_5":   {"category": "momentum",     "description": "5日价格动量",       "fn": momentum_factor,  "direction": 1, "params": {"window": 5}},
    "amplitude_20": {"category": "volatility", "description": "20日平均振幅",  "fn": amplitude_factor, "direction": -1, "params": {"window": 20}},
    "volume_zscore_20": {"category": "volume", "description": "20日成交量Z-Score", "fn": turnover_factor, "direction": 0, "params": {"window": 20}},
}


def _register() -> None:
    reg = get_registry()
    for name, info in TECHNICAL_FACTORS.items():
        if name in reg:
            continue
        reg.register(
            name=name,
            category=info["category"],
            description=info["description"],
            fn=info["fn"],
            direction=info.get("direction", 0),
            source="technical",
            params=info.get("params", {}),
        )


_register()
