"""
Alpha191 #48 — 3日符号和与量比复合反转
========================================

公式:
    -1 * RANK(SUM(SIGN(RET), 3)) * SUM(V, 5) / SUM(V, 20)

公式解释:
    计算3日收益率符号之和的截面排名的负值，乘以5日成交量与
    20日成交量的比值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay
    - ts_sum
    - rank (截面)
    - numpy.sign

背后逻辑:
    3日 SIGN 和衡量短期价格方向一致性（连续上涨或下跌），
    成交量比值衡量近期放量程度。两者乘积综合了方向和量能信息，
    反向设计偏好方向一致但量能温和的标的。

适用场景:
    动量反转策略。

变种与优化:
    - 可调整 SIGN 和窗口期 (3 → 5)
    - 调整量比窗口期 (5/20 → 10/60)
    - 使用成交额替代成交量

注意事项:
    - SIGN 函数丢失幅度信息
    - 成交量比值可能受异常值影响，需做极值处理
    - 前 19 期数据不足时返回 NaN (受20日量比约束)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_048"]

DIRECTION = -1
DEFAULT_SIGN_PERIOD = 3
DEFAULT_SHORT_VOL = 5
DEFAULT_LONG_VOL = 20


def alpha_048(
    ctx: FactorContext,
    sign_period: int = DEFAULT_SIGN_PERIOD,
    short_vol: int = DEFAULT_SHORT_VOL,
    long_vol: int = DEFAULT_LONG_VOL,
) -> pd.DataFrame:
    """Alpha191 #48: 3日符号和与量比复合反转。

    公式: -1 * RANK(SUM(SIGN(RET), sign_period)) * SUM(V,short_vol)/SUM(V,long_vol)

    Args:
        ctx: 因子数据上下文
        sign_period: 符号求和窗口期 (默认 3)
        short_vol: 短期量窗口期 (默认 5)
        long_vol: 长期量窗口期 (默认 20)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    ret = ctx.close / delay(ctx.close, 1) - 1.0
    sign_sum = ts_sum(np.sign(ret), sign_period)
    vol_ratio = ts_sum(ctx.volume, short_vol) / ts_sum(ctx.volume, long_vol)
    return -1.0 * rank(sign_sum) * vol_ratio
