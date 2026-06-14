"""
Alpha101 per-symbol 因子（#9 / #40 / #49）

公式来源: Kakushadze, "101 Formulaic Alphas", 2016

约定:
  - 本文件内函数都是 **per-symbol 时序因子**（基于单标的 OHLCV 计算）
  - 横截面 rank 由 strategy 层负责（factors 不依赖 ctx.data 多 symbol）
  - 每个函数内部自带 factor_cache（key 含 symbol + 所有数值参数）

辅助算子（在内部定义，不导出）:
  ts_min(x, d)         = x.rolling(d).min()
  ts_max(x, d)         = x.rolling(d).max()
  ts_rank(x, d)        = x.rolling(d).rank(pct=True)   # 当前 bar 在过去 d 根的分位
  delta(x, d)          = x - x.shift(d)
  delay(x, d)          = x.shift(d)
  sum(x, d)            = x.rolling(d).sum()
  correlation(x, y, d) = x.rolling(d).corr(y)
  adv(d)               = volume.rolling(d).mean()
  sign(x)              = np.sign(x)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------- #
# 内部算子（不导出）
# ---------------------------------------------------------------------- #
def _ts_min(x: pd.Series, d: int) -> pd.Series:
    return x.rolling(d).min()


def _ts_rank(x: pd.Series, d: int) -> pd.Series:
    # 当前 bar 在过去 d 根的分位（含自身）
    # pct=True 让结果 ∈ (0, 1]
    return x.rolling(d).rank(pct=True)


def _delta(x: pd.Series, d: int) -> pd.Series:
    return x - x.shift(d)


def _delay(x: pd.Series, d: int) -> pd.Series:
    return x.shift(d)


def _sum(x: pd.Series, d: int) -> pd.Series:
    return x.rolling(d).sum()


def _correlation(x: pd.Series, y: pd.Series, d: int) -> pd.Series:
    return x.rolling(d).corr(y)


def _adv(volume: pd.Series, d: int = 20) -> pd.Series:
    return volume.rolling(d).mean()


def _sign(x: pd.Series) -> pd.Series:
    return np.sign(x)


# ---------------------------------------------------------------------- #
# Alpha #9
#   alpha009 = ts_min(close, 5)
#            - correlation( sum(close, 5), sum(close, 20), 5 )
#
#   含义（Kakushadze 2016 原版）:
#     ts_min(close, 5)  越小  →  短期越超跌
#     correlation       越大  →  5 日 close 与 20 日 close 走势同步
#     alpha009 越小     →  短期超跌 + 长期趋势 → 反弹候选
#     alpha009 越大     →  短期不跌 + 长期不同步 → 横盘
#
#   WorldQuant 方向约定: alpha 越大越被低估，越该买入
# ---------------------------------------------------------------------- #
def alpha009(ctx, symbol: str) -> pd.Series:
    key = f"alpha009_{symbol}"
    cached = ctx.cache.get(key)
    if cached is not None:
        return cached

    df = ctx.data[symbol]
    close = df["close"]
    volume = df["volume"]

    a = _ts_min(close, 5)
    b = _correlation(_sum(close, 5), _sum(close, 20), 5)
    val = a - b

    ctx.cache.set(key, val)
    return val


# ---------------------------------------------------------------------- #
# Alpha #40
#   alpha040 = - ts_rank(high, 10) * sign(delta(close, 1))
#
#   含义:
#     ts_rank(high, 10)  越大  →  当前 high 接近 10 日新高
#     sign(delta(close)) +1 / -1  →  今日 close 涨 / 跌
#     ts_rank 高 & close 涨  →  创新高 + 阳线 → 突破/超买 → 负 alpha（不买入）
#     ts_rank 高 & close 跌  →  创新高 + 阴线 → 0   （中性）
#     ts_rank 低 & close 涨  →  低位 + 阳线 → 0   （中性）
#     ts_rank 低 & close 跌  →  低位 + 阴线 → 正 alpha（可能超跌，候选买入）
# ---------------------------------------------------------------------- #
def alpha040(ctx, symbol: str) -> pd.Series:
    key = f"alpha040_{symbol}"
    cached = ctx.cache.get(key)
    if cached is not None:
        return cached

    df = ctx.data[symbol]
    high = df["high"]
    close = df["close"]

    val = -_ts_rank(high, 10) * _sign(_delta(close, 1))

    ctx.cache.set(key, val)
    return val


# ---------------------------------------------------------------------- #
# Alpha #49
#   alpha049 = - ts_rank( delay(close, 10), 10 ) * sign(delta(close, 1))
#             + sign( delta( volume / adv20, 5 ) )
#
#   含义:
#     ts_rank(delay(close,10), 10)
#         = 10 天前的 close 在「10 天前 ~ 今天」窗口里的分位
#     第一项: 旧价位在后来窗口的相对位置
#     第二项: 成交量 / 均量 5 日变化方向
# ---------------------------------------------------------------------- #
def alpha049(ctx, symbol: str) -> pd.Series:
    key = f"alpha049_{symbol}"
    cached = ctx.cache.get(key)
    if cached is not None:
        return cached

    df = ctx.data[symbol]
    close = df["close"]
    volume = df["volume"]

    term1 = -_ts_rank(_delay(close, 10), 10) * _sign(_delta(close, 1))
    term2 = _sign(_delta(volume / _adv(volume, 20), 5))
    val = term1 + term2

    ctx.cache.set(key, val)
    return val
