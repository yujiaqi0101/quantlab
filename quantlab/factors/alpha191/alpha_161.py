"""
Alpha191 #161 — 12日 ATR
========================================

公式:
    MEAN(TR, 12)

公式解释:
    计算12日真实波幅 (TR) 的均值，即12日 ATR (Average True Range)。
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
    ATR 是最经典的波动率指标之一，衡量价格波动的平均幅度。
    高 ATR 表示价格波动剧烈。

适用场景:
    波动率选股策略，跨标的波动率比较。

变种与优化:
    - 可调整窗口期 (12 → 其他)
    - 使用 EMA 替代 SMA
    - 与价格标准化 (ATR/CLOSE)

注意事项:
    - ATR 受价格水平影响，不同价格的股票间需标准化
    - 前 13 期返回 NaN (TR 预热 1 + ts_mean 12)
    - 需使用后复权价格
"""
from __future__ import annotations

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import tr
from quantlab.factors.operators.ts import delay, ts_mean

__all__ = ["alpha_161"]

DIRECTION = 1


def alpha_161(ctx: FactorContext, period: int = 12) -> pd.DataFrame:
    """Alpha191 #161: 12日 ATR。

    公式: MEAN(TR, period)

    Args:
        ctx: 因子数据上下文
        period: ATR 窗口期 (默认 12)

    Returns:
        ATR 因子面板 (date × symbol)
    """
    close = ctx.close
    true_range = tr(ctx.high, ctx.low, delay(close, 1))
    return ts_mean(true_range, period)
