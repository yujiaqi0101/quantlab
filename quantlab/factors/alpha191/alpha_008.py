"""
Alpha191 #8 — 加权中间价4日动量反转
========================================

公式:
    RANK(DELTA((((HIGH+LOW)/2)*0.2) + (VWAP*0.8), 4)) * -1

公式解释:
    计算加权中间价（20%高低均价 + 80%VWAP）的4日变化量的截面排名，取负值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好短期价格回落标的）

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VWAP 成交量加权均价（日频，由分时聚合或 AMOUNT/VOLUME 近似）

算子依赖:
    - rank
    - delta

背后逻辑:
    该因子使用 VWAP 为主要权重（80%）的加权价格衡量短期动量，取负值表示
    偏好短期价格回落的股票。VWAP 比收盘价更能反映全天真实成交价格水平，
    结合高低均价后对极端值有一定平滑作用。

适用场景:
    短期反转策略，偏好近期价格回落的标的。

变种与优化:
    - 可调整加权比例（20%/80% → 30%/70%）
    - 调整变化周期（4日 → 6日/10日）
    - 使用不同的价格加权方式（如 TWAP）

注意事项:
    - VWAP 的近似计算（AMOUNT/VOLUME）可能引入误差
    - 短期动量反转策略需要较高的换手率
    - 前 4 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_008"]

DIRECTION = -1
DEFAULT_PERIOD = 4


def alpha_008(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #8: 加权中间价4日动量反转。

    公式: -1 * RANK(DELTA((HIGH+LOW)/2*0.2 + VWAP*0.8, period))

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 4)

    Returns:
        动量反转因子面板 (date × symbol)，前 period 期为 NaN
    """
    vwap = ctx.get_vwap()
    weighted_mid = (ctx.high + ctx.low) / 2 * 0.2 + vwap * 0.8
    change = delta(weighted_mid, period)
    return -1.0 * rank(change)
