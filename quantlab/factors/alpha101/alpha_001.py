"""
Alpha101 #1 — 波动率-价格混合
================================

公式:
    rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5

公式解释:
    当收益率小于 0 时使用 20 日收益率标准差替代收盘价，对其做带符号平方 (SignedPower(x, 2))，
    再取 5 日内最大值出现的位置 (Ts_ArgMax)，截面排名后中心化 (减 0.5)。

分类:
    波动率-价格混合 (volatility_price_mixed)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - RETURNS 日收益率（由 close.pct_change 推导）

算子依赖:
    - ts_std (stddev)
    - signed_power (SignedPower)
    - ts_argmax (Ts_ArgMax)
    - rank (截面)

背后逻辑:
    区分下跌和上涨状态：下跌时用波动率，上涨时用价格水平。
    SignedPower(x, 2) = sign(x) * |x|^2 放大极端值；Ts_ArgMax 捕捉最大值出现位置，
    反映近期趋势强度。排名中心化后，正值为看多信号。

适用场景:
    适用于区分牛熊状态的短期择时，尤其在市场转折点附近效果较好。

变种与优化:
    - 可调整波动率窗口 (20 → 10/40)
    - 可调整 Ts_ArgMax 窗口 (5 → 3/10)
    - 可调整 SignedPower 指数 (2 → 1.5/3)

注意事项:
    - 条件分支 (returns < 0) 使因子具有非线性特征
    - 前 20 期因 ts_std 预热不足返回 NaN
    - 截面标的数 < 2 时 rank 退化
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.ts import ts_argmax, ts_std

__all__ = ["alpha_001"]

DIRECTION = 1
DEFAULT_STD_PERIOD = 20
DEFAULT_ARGMAX_PERIOD = 5
DEFAULT_POWER = 2.0


def alpha_001(
    ctx: FactorContext,
    std_period: int = DEFAULT_STD_PERIOD,
    argmax_period: int = DEFAULT_ARGMAX_PERIOD,
    power: float = DEFAULT_POWER,
) -> pd.DataFrame:
    """Alpha101 #1: 波动率-价格混合。

    公式: rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, std_period) : close), power), argmax_period)) - 0.5

    Args:
        ctx: 因子数据上下文
        std_period: 收益率标准差窗口 (默认 20)
        argmax_period: 最大值位置窗口 (默认 5)
        power: SignedPower 指数 (默认 2.0)

    Returns:
        波动率-价格混合因子面板 (date × symbol)
    """
    ret = ctx.get_returns()
    ret_std = ts_std(ret, std_period)
    close = ctx.close
    # 条件选择: RET < 0 时取 STD(RET), 否则取 CLOSE
    selected = ret_std.where(ret < 0, close)
    powered = signed_power(selected, power)
    argmax = ts_argmax(powered, argmax_period)
    return rank(argmax) - 0.5
