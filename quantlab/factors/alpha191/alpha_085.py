"""
Alpha191 #85 — 量价时序排名乘积反转
========================================

公式:
    TSRANK(V / MA(V, 20), 20) * TSRANK(-DELTA(CLOSE, 7), 8)

公式解释:
    计算成交量与20日成交量均值比值的20日时间序列排名，
    乘以7日价格变化量取负后的8日时间序列排名。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean (滚动均值)
    - ts_rank (时序排名)
    - delta (差分)

背后逻辑:
    将成交量相对水平与价格短期反转信号相乘。
    当成交量处于近期高位且价格近期下跌时
    （TSRANK(-DELTA) 高），因子值较高。
    反向选择偏好因子值低的股票。

适用场景:
    量价反转策略。

变种与优化:
    - 可调整各窗口期 (20/20/7/8 → 其他)
    - 使用不同的标准化方式
    - 加入成交额替代成交量

注意事项:
    - 两个子信号的乘积可能放大噪声
    - 前 39 期返回 NaN (ts_mean 20 + ts_rank 20 - 1)
    - 需结合其他因子使用
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_mean, ts_rank

__all__ = ["alpha_085"]

DIRECTION = -1
DEFAULT_MA_PERIOD = 20
DEFAULT_VOL_RANK = 20
DEFAULT_DELTA_PERIOD = 7
DEFAULT_PRICE_RANK = 8


def alpha_085(
    ctx: FactorContext,
    ma_period: int = DEFAULT_MA_PERIOD,
    vol_rank: int = DEFAULT_VOL_RANK,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    price_rank: int = DEFAULT_PRICE_RANK,
) -> pd.DataFrame:
    """Alpha191 #85: 量价时序排名乘积反转。

    公式: TSRANK(V / MA(V, ma_period), vol_rank) * TSRANK(-DELTA(CLOSE, delta_period), price_rank)

    Args:
        ctx: 因子数据上下文
        ma_period: 成交量均值窗口期 (默认 20)
        vol_rank: 成交量排名窗口期 (默认 20)
        delta_period: 价格差分窗口期 (默认 7)
        price_rank: 价格排名窗口期 (默认 8)

    Returns:
        量价排名乘积因子面板 (date × symbol)
    """
    vol_ratio = ctx.volume / ts_mean(ctx.volume, ma_period)
    vol_term = ts_rank(vol_ratio, vol_rank)
    price_term = ts_rank(-delta(ctx.close, delta_period), price_rank)
    return vol_term * price_term
