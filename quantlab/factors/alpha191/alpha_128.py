"""
Alpha191 #128 — 资金流量指标 (MFI)
========================================

公式:
    100 - (100 / (1 + SUM(上涨日TYP*V, 14) / SUM(下跌日TYP*V, 14)))

公式解释:
    计算14日内上涨日典型价格乘以成交量之和
    与下跌日之比的MFI（Money Flow Index）。

    TYP = (CLOSE + HIGH + LOW) / 3
    上涨日: TYP > DELAY(TYP, 1)
    下跌日: TYP < DELAY(TYP, 1)

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay (1日延迟)
    - sum_if (条件滚动求和)

背后逻辑:
    MFI结合了价格和成交量信息，
    类似于成交量加权的RSI。
    MFI > 80 为超买，MFI < 20 为超卖。
    正向选择偏好 MFI 高的股票。

适用场景:
    量价动量策略。

变种与优化:
    - 可调整窗口期 (14 → 10/20)
    - 结合超买超卖区间使用
    - 使用成交额替代成交量

注意事项:
    - MFI在强趋势中可能长期处于极端区域
    - 前 15 期返回 NaN (delay 1 + rolling 14)
    - 分母为 0 时返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import sum_if
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_128"]

DIRECTION = 1
DEFAULT_PERIOD = 14


def alpha_128(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #128: 资金流量指标 (MFI)。

    公式: 100 - (100 / (1 + SUM(up*TYP*V, period) / SUM(down*TYP*V, period)))

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 14)

    Returns:
        MFI因子面板 (date × symbol)
    """
    typ = (ctx.close + ctx.high + ctx.low) / 3.0
    prev_typ = delay(typ, 1)
    typ_vol = typ * ctx.volume

    # 上涨日: TYP > 前一日 TYP
    up_cond = (typ > prev_typ).astype(float)
    down_cond = (typ < prev_typ).astype(float)

    up_flow = sum_if(typ_vol, up_cond, period)
    down_flow = sum_if(typ_vol, down_cond, period)
    # 分母为 0 时返回 NaN
    safe_down = down_flow.where(down_flow > 0, np.nan)
    money_ratio = up_flow / safe_down
    return 100.0 - 100.0 / (1.0 + money_ratio)
