"""
Alpha101 #49 — 价格加速度阈值因子
========================================

公式:
    (((delay(close,20) - delay(close,10))/10 - (delay(close,10) - close)/10) < -0.1)
    ? 1
    : -1 * (close - delay(close, 1))

公式解释:
    与 Alpha#46 类似但阈值不同 (-0.1)。
    价格加速度 accel = (dc20-dc10)/10 - (dc10-close)/10
    加速度 < -0.1 时做多 (+1)；否则做短期反转 (-delta(close,1))。

分类:
    价格加速度阈值 (price_acceleration_threshold)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    价格加速度反映趋势变化率。加速度 < -0.1 表示趋势加速下跌，看多 (反转)。
    否则做短期反转 (-delta(close,1))：下跌时看多，上涨时看空。
    与 #46 互补，#46 用 +0.25 阈值判断加速上涨，#49 用 -0.1 判断加速下跌。

适用场景:
    趋势拐点判断策略，侧重下跌加速时的反转机会。

变种与优化:
    - 可使用自适应阈值 (基于波动率)
    - 可结合 #46 形成双向阈值策略
    - 可引入成交量加速度确认

注意事项:
    - 阈值 -0.1 是经验值，需根据品种调整
    - 前 20 期返回 NaN (delay 20)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_049"]

DIRECTION = 1


def alpha_049(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #49: 价格加速度阈值因子。

    公式:
        accel = (delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10
        if accel < -0.1: 1
        else: -1 * (close - delay(close,1))

    Args:
        ctx: 因子数据上下文

    Returns:
        价格加速度阈值因子面板 (date × symbol)
    """
    close = ctx.close
    dc10 = delay(close, 10)
    dc20 = delay(close, 20)
    accel = (dc20 - dc10) / 10 - (dc10 - close) / 10
    d1 = close - delay(close, 1)
    # accel < -0.1 → 1.0；accel >= -0.1 → -d1
    result = (-d1).where(accel >= -0.1, 1.0)
    # accel 为 NaN (预热期) 时保持 NaN
    return result.where(accel.notna())
