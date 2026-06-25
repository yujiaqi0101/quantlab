"""
Alpha101 #54 — K线形态-价格加权
====================================

公式:
    -1 * ((low - close) * (open^5)) / ((low - high) * (close^5))

公式解释:
    复杂的 K 线形态因子：结合最低价、收盘价、开盘价和最高价，使用 5 次幂加权。0 延迟 Alpha。

分类:
    K线形态-价格加权 (candlestick_price_weighted)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - 幂运算 (open^5, close^5)
    - 除法

背后逻辑:
    5 次幂使因子对价格水平非常敏感。
    结合 K 线各价位关系，捕捉价格形态信号。

适用场景:
    适用于收盘前的 K 线形态交易 (0 延迟)。

变种与优化:
    - 可调整幂次 (5 → 2/3)
    - 可使用对数变换

注意事项:
    - 5 次幂使因子对价格水平非常敏感
    - high == low (涨停/跌停) 或 close == 0 时除零返回 NaN
    - 0 延迟 Alpha，适合收盘前交易
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_054"]

DIRECTION = -1
DEFAULT_POWER = 5


def alpha_054(ctx: FactorContext, power: float = DEFAULT_POWER) -> pd.DataFrame:
    """Alpha101 #54: K线形态-价格加权。

    公式: -1 * ((low - close) * (open^power)) / ((low - high) * (close^power))

    Args:
        ctx: 因子数据上下文
        power: 幂次 (默认 5)

    Returns:
        K线形态-价格加权因子面板 (date × symbol)
    """
    open_p = ctx.open ** power
    close_p = ctx.close ** power
    numerator = (ctx.low - ctx.close) * open_p
    denominator = (ctx.low - ctx.high) * close_p
    # 避免除零 (high==low 或 close==0)
    safe_den = denominator.where(denominator.abs() > 0, np.nan)
    result = -1.0 * numerator / safe_den
    return result.replace([np.inf, -np.inf], np.nan)
