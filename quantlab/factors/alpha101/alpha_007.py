"""
Alpha101 #7 — 成交量异常-价格动量
====================================

公式:
    (adv20 < volume) ? ((-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7))) : -1

公式解释:
    当成交量突破 20 日均量 (adv20) 时，根据 7 日价格变化的方向和幅度进行排名交易；否则固定做空。

分类:
    成交量异常-价格动量 (volume_anomaly_price_momentum)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean (adv20)
    - delta (时序差分)
    - ts_rank (时序排名)
    - sign (符号)

背后逻辑:
    放量时结合价格动量方向判断：放量上涨 (sign>0) 且动量排名低时看多；放量下跌时看空。
    条件分支使因子具有状态依赖性；放量时因子更敏感。

适用场景:
    适用于放量突破/跌破的择时场景。

变种与优化:
    - 可调整 adv20 窗口和 delta 窗口
    - 可使用其他成交量基准

注意事项:
    - 条件分支使因子具有状态依赖性
    - 前 26 期因 adv20(19) + delta(7) 预热返回 NaN
    - 缩量时固定返回 -1
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_rank

__all__ = ["alpha_007"]

DIRECTION = -1
DEFAULT_ADV_PERIOD = 20
DEFAULT_DELTA_PERIOD = 7
DEFAULT_RANK_PERIOD = 60


def alpha_007(
    ctx: FactorContext,
    adv_period: int = DEFAULT_ADV_PERIOD,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    rank_period: int = DEFAULT_RANK_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #7: 成交量异常-价格动量。

    公式: (adv20 < volume) ? (-1 * ts_rank(abs(delta(close, delta_period)), rank_period) * sign(delta(close, delta_period))) : -1

    Args:
        ctx: 因子数据上下文
        adv_period: 平均成交量窗口 (默认 20)
        delta_period: 价格差分窗口 (默认 7)
        rank_period: 时序排名窗口 (默认 60)

    Returns:
        成交量异常-价格动量因子面板 (date × symbol)
    """
    adv = ctx.get_adv(adv_period)
    price_delta = delta(ctx.close, delta_period)
    # 放量条件 (预热期 adv 为 NaN → 条件为 False)
    vol_breakout = ctx.volume > adv
    # 放量时的动量排名信号
    momentum = -1.0 * ts_rank(price_delta.abs(), rank_period) * np.sign(price_delta)
    # 缩量时固定 -1
    result = momentum.where(vol_breakout, -1.0)
    # 预热期 (adv/price_delta 为 NaN) 返回 NaN
    result = result.where(adv.notna() & price_delta.notna())
    return result
