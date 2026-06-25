"""
Alpha191 #191 — 量价相关性+价格位置
========================================

公式:
    CORR(MA(V, 20), LOW, 5) + ((HIGH + LOW) / 2 - CLOSE)

公式解释:
    计算20日成交量均值与最低价5日相关系数，
    加上中间价减去收盘价。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_mean (滚动均值)
    - corr (滚动相关系数)

背后逻辑:
    将量价相关性信号与价格位置信号相加。
    相关性项衡量成交量与低价的关联，
    价格位置项衡量收盘价在当日振幅中的位置。

适用场景:
    量价综合策略。

变种与优化:
    - 可调整各窗口期 (20/5 → 其他)
    - 使用不同的组合方式
    - 加入成交额加权

注意事项:
    - 两个子信号的量纲不同，需做标准化
    - 前 23 期返回 NaN (ts_mean 20 + corr 5 - 2)
    - 相关性项与价格位置项的权重需平衡
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_191"]

DIRECTION = 1
DEFAULT_MA_PERIOD = 20
DEFAULT_CORR_PERIOD = 5


def alpha_191(
    ctx: FactorContext,
    ma_period: int = DEFAULT_MA_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #191: 量价相关性+价格位置。

    公式: CORR(MA(V, ma_period), LOW, corr_period) + ((HIGH + LOW) / 2 - CLOSE)

    Args:
        ctx: 因子数据上下文
        ma_period: 成交量均值窗口期 (默认 20)
        corr_period: 相关系数窗口期 (默认 5)

    Returns:
        量价综合因子面板 (date × symbol)
    """
    vol_ma = ts_mean(ctx.volume, ma_period)
    corr_term = corr(vol_ma, ctx.low, corr_period)
    price_term = (ctx.high + ctx.low) / 2.0 - ctx.close
    return corr_term + price_term
