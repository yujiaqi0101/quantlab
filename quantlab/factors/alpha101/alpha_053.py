"""
Alpha101 #53 — K线形态变化 [Delay-0]
========================================

公式:
    -1 * delta((close - high) / (high - low), 9)

公式解释:
    收盘价在日内高低价范围中位置的 9 日变化量，取负。
    衡量 K 线实体位置的变化趋势。0 延迟 Alpha。

分类:
    K线形态变化 (candlestick_position_change)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - delta

背后逻辑:
    (close-high)/(high-low) 衡量收盘价在日内范围的位置：
    - 接近 0: 收盘价接近最高价 (强势收盘)
    - 接近 -1: 收盘价接近最低价 (弱势收盘)
    delta 取 9 日变化，反映位置变化趋势。
    位置上升 (趋强) 时 delta > 0，取负看空 (反转)。

适用场景:
    K 线形态反转策略，适合收盘时交易 (Delay-0)。

变种与优化:
    - 可引入成交量维度
    - 可使用其他 K 线形态特征
    - 可调整窗口 (9 → 5/20)

注意事项:
    - high-low 为 0 时需处理除零 (一字板)
    - 0 延迟因子需在收盘时执行
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_053"]

DIRECTION = -1


def alpha_053(ctx: FactorContext, period: int = 9) -> pd.DataFrame:
    """Alpha101 #53: K线形态变化。

    公式: -1 * delta((close - high) / (high - low), period)

    Args:
        ctx: 因子数据上下文
        period: 变化窗口 (默认 9)

    Returns:
        K线形态变化因子面板 (date × symbol)
    """
    hl_range = ctx.high - ctx.low
    hl_range_safe = hl_range.where(hl_range.abs() > 1e-12)
    position = (ctx.close - ctx.high) / hl_range_safe
    return -1 * delta(position, period)
