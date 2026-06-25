"""
Alpha191 #101 — 多层排名相关性比较
========================================

公式:
    (RANK(CORR(CLOSE, SUM(MEAN(VOL,30), 37), 15))
     < RANK(CORR(RANK((HIGH*0.1+VWAP*0.9)), RANK(VOL), 11))) * -1

公式解释:
    比较两个相关性的截面排名，左侧用收盘价与累积量的相关性，
    右侧用(HIGH+VWAP)与成交量的排名相关性。结果乘 -1。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/HIGH/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - ts_mean
    - ts_sum
    - corr

背后逻辑:
    两层量价相关性的相对强弱，取负向选择右侧相关性更强的标的。

适用场景:
    量价背离选股。

变种与优化:
    - 调整权重 0.1/0.9 → 0.3/0.7
    - 调整窗口期

注意事项:
    - 返回值为 0 或 -1
    - 前约 51 期返回 NaN (corr 累积预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean, ts_sum

__all__ = ["alpha_101"]

DIRECTION = -1


def alpha_101(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #101: 多层排名相关性比较。

    Args:
        ctx: 因子数据上下文

    Returns:
        布尔因子面板 (date × symbol)，值为 {0, -1}
    """
    close = ctx.close
    high = ctx.high
    vol = ctx.volume
    vwap = ctx.get_vwap()

    # 左: RANK(CORR(CLOSE, SUM(MEAN(VOL,30), 37), 15))
    mean_vol_30 = ts_mean(vol, 30)
    sum_mean_vol_37 = ts_sum(mean_vol_30, 37)
    left = rank(corr(close, sum_mean_vol_37, 15))

    # 右: RANK(CORR(RANK(HIGH*0.1+VWAP*0.9), RANK(VOL), 11))
    hybrid = high * 0.1 + vwap * 0.9
    right = rank(corr(rank(hybrid), rank(vol), 11))

    # NaN 保护: 任一为 NaN 时比较结果应为 NaN
    mask = left.notna() & right.notna()
    return ((left < right).astype(float) * -1.0).where(mask)
