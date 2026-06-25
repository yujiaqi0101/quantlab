"""
Alpha101 #46 — 价格加速度因子
========================================

公式:
    (0.25 < ((delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10))
    ? -1
    : ((((delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10) < 0)
       ? 1
       : -1 * (close - delay(close,1)))

公式解释:
    计算价格的二阶差分 (加速度):
        accel = (delay(close,20) - delay(close,10))/10 - (delay(close,10) - close)/10
    加速度 > 0.25 时做空 (-1)；
    加速度 < 0 时做多 (+1)；
    否则做短期反转 (-1 * delta(close,1))。

分类:
    价格加速度 (price_acceleration)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    价格加速度反映趋势的变化率。
    加速度高 (>0.25) 表示趋势加速上涨，看空 (反转)；
    加速度低 (<0) 表示趋势加速下跌，看多 (反转)；
    加速度适中时做短期反转。
    核心是趋势拐点判断。

适用场景:
    趋势拐点判断策略，适应不同趋势状态。

变种与优化:
    - 可调整阈值 (0.25 → 动态分位数)
    - 可使用更高阶差分
    - 可引入成交量加速度确认

注意事项:
    - 阈值 0.25 是经验值，需根据品种调整
    - 前 20 期返回 NaN (delay 20)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_046"]

DIRECTION = 1


def alpha_046(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #46: 价格加速度因子。

    公式:
        accel = (delay(close,20)-delay(close,10))/10 - (delay(close,10)-close)/10
        if accel > 0.25: -1
        elif accel < 0: 1
        else: -1 * (close - delay(close,1))

    Args:
        ctx: 因子数据上下文

    Returns:
        价格加速度因子面板 (date × symbol)
    """
    close = ctx.close
    dc10 = delay(close, 10)
    dc20 = delay(close, 20)
    accel = (dc20 - dc10) / 10 - (dc10 - close) / 10
    d1 = close - delay(close, 1)

    result = pd.DataFrame(
        -1.0, index=close.index, columns=close.columns
    )  # 默认 accel > 0.25: -1
    result = result.where(accel > 0.25, 1.0)          # accel < 0: +1
    result = result.where(accel < 0, -1.0 * d1)        # 0 <= accel <= 0.25: -d1
    return result
