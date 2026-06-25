"""
Alpha101 #17 — 价格动量-成交量比率
======================================

公式:
    ((-1 * rank(ts_rank(close, 10))) * rank(delta(delta(close, 1), 1))) * rank(ts_rank(volume / adv20, 5))

公式解释:
    三因子乘积：收盘价 10 日时序排名取负、价格加速度 (二阶差分) 排名、相对成交量 5 日时序排名。

分类:
    价格动量-成交量比率 (price_momentum_volume_ratio)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_rank (时序排名)
    - delta (时序差分，二阶)
    - rank (截面)
    - ts_mean (adv20)

背后逻辑:
    结合价格动量反转、价格加速度和成交量异常。
    三因子乘积创造了复杂的非线性交互效应。

适用场景:
    适用于多维度的量价综合择时。

变种与优化:
    - 可调整各窗口参数 (10, 1, 1, 5)
    - 可改为加权求和替代乘积
    - 可引入更多因子维度

注意事项:
    - 三因子乘积创造复杂非线性交互效应
    - 前 24 期因 adv20(19) + ts_rank(5) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_rank

__all__ = ["alpha_017"]

DIRECTION = -1
DEFAULT_PRICE_RANK = 10
DEFAULT_ACC_DELTA = 1
DEFAULT_VOL_RANK = 5
DEFAULT_ADV_PERIOD = 20


def alpha_017(
    ctx: FactorContext,
    price_rank: int = DEFAULT_PRICE_RANK,
    acc_delta: int = DEFAULT_ACC_DELTA,
    vol_rank: int = DEFAULT_VOL_RANK,
    adv_period: int = DEFAULT_ADV_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #17: 价格动量-成交量比率。

    公式: ((-1 * rank(ts_rank(close, price_rank))) * rank(delta(delta(close, acc_delta), acc_delta))) * rank(ts_rank(volume / adv20, vol_rank))

    Args:
        ctx: 因子数据上下文
        price_rank: 价格时序排名窗口 (默认 10)
        acc_delta: 价格加速度差分窗口 (默认 1)
        vol_rank: 成交量时序排名窗口 (默认 5)
        adv_period: 平均成交量窗口 (默认 20)

    Returns:
        价格动量-成交量比率因子面板 (date × symbol)
    """
    price_term = -1.0 * rank(ts_rank(ctx.close, price_rank))
    accel = delta(delta(ctx.close, acc_delta), acc_delta)
    accel_term = rank(accel)
    adv = ctx.get_adv(adv_period)
    vol_ratio = ctx.volume / adv
    vol_term = rank(ts_rank(vol_ratio, vol_rank))
    return price_term * accel_term * vol_term
