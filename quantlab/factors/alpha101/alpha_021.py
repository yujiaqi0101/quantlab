"""
Alpha101 #21 — 布林带-成交量
================================

公式:
    ((sum(close, 8) / 8 + stddev(close, 8)) < (sum(close, 2) / 2)) ? -1 :
      ((sum(close, 2) / 2 < (sum(close, 8) / 8 - stddev(close, 8))) ? 1 :
        ((1 < (volume / adv20)) || (volume / adv20 == 1)) ? 1 : -1)

公式解释:
    类似布林带策略：
    - 短期均价上穿长期均价 + 标准差 (上轨) 时做空 (-1)
    - 短期均价下穿长期均价 - 标准差 (下轨) 时做多 (+1)
    - 否则根据成交量是否放量 (volume/adv20 >= 1) 做多，缩量做空

分类:
    布林带-成交量 (bollinger_volume)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_sum (滚动求和)
    - ts_std (滚动标准差)
    - ts_mean (adv20)

背后逻辑:
    结合均值回归和成交量确认。
    突破上轨做空、突破下轨做多；未突破时根据成交量状态择时。

适用场景:
    适用于布林带突破策略。

变种与优化:
    - 可调整均线和标准差窗口 (8, 2)
    - 可使用指数加权移动平均替代简单均线
    - 可调整放量阈值 (1 → 1.5)

注意事项:
    - 条件分支使因子具有状态依赖性
    - 前 20 期因 adv20 预热返回 NaN
    - 返回值为二值信号 {-1, 1}
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_std, ts_sum

__all__ = ["alpha_021"]

DIRECTION = -1
DEFAULT_LONG_PERIOD = 8
DEFAULT_SHORT_PERIOD = 2
DEFAULT_ADV_PERIOD = 20


def alpha_021(
    ctx: FactorContext,
    long_period: int = DEFAULT_LONG_PERIOD,
    short_period: int = DEFAULT_SHORT_PERIOD,
    adv_period: int = DEFAULT_ADV_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #21: 布林带-成交量。

    公式:
        ((ma8 + std8) < ma2) ? -1 :
          ((ma2 < (ma8 - std8)) ? 1 :
            ((volume/adv20 >= 1) ? 1 : -1))

    Args:
        ctx: 因子数据上下文
        long_period: 长期均线窗口 (默认 8)
        short_period: 短期均线窗口 (默认 2)
        adv_period: 平均成交量窗口 (默认 20)

    Returns:
        布林带-成交量因子面板 (date × symbol)，值为 {-1, 1}
    """
    close = ctx.close
    ma_long = ts_sum(close, long_period) / long_period
    std_long = ts_std(close, long_period)
    ma_short = ts_sum(close, short_period) / short_period
    upper = ma_long + std_long
    lower = ma_long - std_long

    adv = ctx.get_adv(adv_period)
    vol_ratio = ctx.volume / adv

    # 上穿上轨 → -1; 下穿下轨 → 1; 放量 → 1; 缩量 → -1
    result = pd.DataFrame(np.nan, index=close.index, columns=close.columns, dtype=float)
    # 先按放量/缩量赋值
    breakout = vol_ratio >= 1.0
    result = result.where(~breakout, 1.0).where(breakout, -1.0)
    # 覆盖布林带突破信号
    short_above_upper = ma_short > upper
    short_below_lower = ma_short < lower
    result = result.where(~short_above_upper, -1.0)
    result = result.where(~short_below_lower, 1.0)
    # 预热期 (ma_long/std_long/adv 为 NaN) 返回 NaN
    warmup_mask = ma_long.notna() & std_long.notna() & adv.notna() & ma_short.notna()
    result = result.where(warmup_mask)
    return result
