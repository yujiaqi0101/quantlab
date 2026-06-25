"""
Alpha191 #104 — 量价相关变化与波动率复合反转
========================================

公式:
    -1 * DELTA(CORR(HIGH, VOLUME, 5), 5) * RANK(STD(CLOSE, 20))

公式解释:
    计算最高价与成交量5日相关系数的5日变化量，乘以收盘价20日标准差的
    截面排名，取负值。

分类:
    相关性 (correlation)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价、CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - corr
    - delta
    - ts_std
    - rank (截面)

背后逻辑:
    该因子将量价相关性的变化与价格波动率相结合。当相关性增强且波动率高
    时，因子值较低（取负后较高）。反向选择偏好因子值低的股票。

适用场景:
    量价波动率综合策略。

变种与优化:
    - 可调整各窗口期 (5/5/20)
    - 使用不同的波动率度量
    - 加权组合两个子信号

注意事项:
    - 相关系数变化量可能不稳定，需做平滑处理
    - 前 8 期数据不足时返回 NaN (5日相关 + 5日变化)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_std

__all__ = ["alpha_104"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 5
DEFAULT_DELTA_PERIOD = 5
DEFAULT_STD_PERIOD = 20


def alpha_104(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    std_period: int = DEFAULT_STD_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #104: 量价相关变化与波动率复合反转。

    公式: -1 * DELTA(CORR(HIGH, VOLUME, corr_period), delta_period)
          * RANK(STD(CLOSE, std_period))

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口期 (默认 5)
        delta_period: 相关变化窗口期 (默认 5)
        std_period: 标准差窗口期 (默认 20)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    vp_corr = corr(ctx.high, ctx.volume, corr_period)
    corr_change = delta(vp_corr, delta_period)
    vol = rank(ts_std(ctx.close, std_period))
    return -1.0 * corr_change * vol
