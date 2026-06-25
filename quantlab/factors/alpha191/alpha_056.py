"""
Alpha191 #56 — 开盘价排名与量价相关性排名比较
========================================

公式:
    RANK(OPEN - TSMIN(OPEN, 12)) < RANK(RANK(CORR(SUM((H+L)/2, 19),
                                                  SUM(MEAN(VOL,40), 19), 13))^5)

公式解释:
    比较两个排名，返回布尔值 (True=1, False=0)。
    左侧: 开盘价与12日开盘最低的差值的截面排名
    右侧: 量价相关性5次幂的截面排名

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank
    - ts_min
    - ts_sum
    - ts_mean
    - corr
    - signed_power

背后逻辑:
    开盘价相对低点的强度 与 量价相关性的极端性 比较，
    布尔信号反映两者相对强弱。

适用场景:
    量价配合选股。

变种与优化:
    - 调整窗口参数
    - 用 sign 转为方向信号

注意事项:
    - 返回值为 0/1 (布尔比较结果)
    - 前 32 期返回 NaN (相关性和累积预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_min, ts_sum, ts_mean

__all__ = ["alpha_056"]

DIRECTION = 1


def alpha_056(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #56: 开盘价排名与量价相关性排名比较。

    Args:
        ctx: 因子数据上下文

    Returns:
        布尔因子面板 (date × symbol)，值为 {0, 1}
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    vol = ctx.volume

    # 左侧: RANK(OPEN - TSMIN(OPEN, 12))
    left = rank(open_ - ts_min(open_, 12))

    # 右侧: RANK(RANK(CORR(SUM((H+L)/2, 19), SUM(MEAN(VOL,40), 19), 13))^5)
    hl_mean = (high + low) / 2.0
    vol_mean_40 = ts_mean(vol, 40)
    corr_val = corr(ts_sum(hl_mean, 19), ts_sum(vol_mean_40, 19), 13)
    right = rank(signed_power(rank(corr_val), 5))

    # NaN 保护: 任一为 NaN 时比较结果应为 NaN
    mask = left.notna() & right.notna()
    return (left < right).astype(float).where(mask)
