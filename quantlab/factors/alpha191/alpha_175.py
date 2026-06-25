"""
Alpha191 #175 — 6日 ATR
========================================

公式:
    MEAN(TR, 6)

公式解释:
    计算6日真实波幅 (TR) 的均值，即6日 ATR。
    TR = MAX(H-L, |H-prevC|, |L-prevC|)。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - tr (真实波幅)
    - ts_mean

背后逻辑:
    与 Alpha161 类似但使用6日窗口期。
    更短的窗口期使 ATR 更敏感于近期波动变化。

适用场景:
    短期波动率策略，捕捉近期波动率变化。

变种与优化:
    - 可调整窗口期 (6 → 其他)
    - 使用 EMA 替代 SMA
    - 与价格标准化 (ATR/CLOSE)

注意事项:
    - 短期 ATR 噪声较大
    - 前 7 期返回 NaN (TR 预热 1 + ts_mean 6)
    - 需使用后复权价格
"""
from __future__ import annotations

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import tr
from quantlab.factors.operators.ts import delay, ts_mean

__all__ = ["alpha_175"]

DIRECTION = 1


def alpha_175(ctx: FactorContext, period: int = 6) -> pd.DataFrame:
    """Alpha191 #175: 6日 ATR。

    公式: MEAN(TR, period)

    Args:
        ctx: 因子数据上下文
        period: ATR 窗口期 (默认 6)

    Returns:
        ATR 因子面板 (date × symbol)
    """
    close = ctx.close
    true_range = tr(ctx.high, ctx.low, delay(close, 1))
    return ts_mean(true_range, period)
