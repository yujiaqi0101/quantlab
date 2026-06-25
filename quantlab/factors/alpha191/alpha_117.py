"""
Alpha191 #117 — 底部放量反转
========================================

公式:
    TSRANK(V, 32) * (1 - TSRANK(CLOSE + HIGH - LOW, 16)) * (1 - TSRANK(RET, 32))

公式解释:
    计算成交量32日时间序列排名，
    乘以1减中间价16日时间序列排名，
    再乘以1减收益率32日时间序列排名。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - ts_rank (时序排名)

背后逻辑:
    偏好成交量排名高（放量）、中间价排名低
    （价格处于相对低位）、收益率排名低
    （近期表现差）的股票。
    这种组合捕捉了底部放量的反转信号。

适用场景:
    底部放量反转策略。

变种与优化:
    - 可调整各窗口期 (32/16/32 → 其他)
    - 使用不同的价格基准
    - 加入成交额替代成交量

注意事项:
    - 三个子信号的乘积可能过于保守
    - 前 31 期返回 NaN (ts_rank 32)
    - 需结合趋势判断
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_rank

__all__ = ["alpha_117"]

DIRECTION = 1
DEFAULT_VOL_RANK = 32
DEFAULT_PRICE_RANK = 16
DEFAULT_RET_RANK = 32


def alpha_117(
    ctx: FactorContext,
    vol_rank: int = DEFAULT_VOL_RANK,
    price_rank: int = DEFAULT_PRICE_RANK,
    ret_rank: int = DEFAULT_RET_RANK,
) -> pd.DataFrame:
    """Alpha191 #117: 底部放量反转。

    公式: TSRANK(V, vol_rank) * (1 - TSRANK(C+H-L, price_rank)) * (1 - TSRANK(RET, ret_rank))

    Args:
        ctx: 因子数据上下文
        vol_rank: 成交量排名窗口期 (默认 32)
        price_rank: 价格排名窗口期 (默认 16)
        ret_rank: 收益率排名窗口期 (默认 32)

    Returns:
        底部放量反转因子面板 (date × symbol)
    """
    vol_term = ts_rank(ctx.volume, vol_rank)
    price_term = 1.0 - ts_rank(ctx.close + ctx.high - ctx.low, price_rank)
    ret = ctx.get_returns()
    ret_term = 1.0 - ts_rank(ret, ret_rank)
    return vol_term * price_term * ret_term
