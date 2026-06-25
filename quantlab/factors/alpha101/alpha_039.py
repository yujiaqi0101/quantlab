"""
Alpha101 #39 — 价格动量-成交量衰减 (adv20+长窗口)
========================================

公式:
    ((-1 * rank((delta(close, 7) * (1 - rank(decay_linear((volume / adv20), 9))))))
     * (1 + rank(sum(returns, 250))))

公式解释:
    7 日价格变化乘以 (1-相对成交量的 9 日衰减加权排名)，
    排名取负，再乘以 (1+250 日累计收益率排名)。
    结合价格动量、成交量趋势和长期收益。

分类:
    价格动量-成交量衰减 (price_momentum_volume_decay)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - ADV20 20 日平均成交量（由 volume 派生）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - delta
    - rank (截面)
    - decay_linear
    - ts_sum
    - ctx.get_adv

背后逻辑:
    价格动量 (delta 7) 反映短期趋势，
    成交量衰减排名反映量能持续性，
    250 日累计收益反映长期表现。
    短期反转叠加长期动量确认。

适用场景:
    短期反转 + 长期动量组合策略。

变种与优化:
    - 可调整窗口 (7/9/250)
    - 可用 decay_linear 替代 ts_sum
    - 可引入波动率调整

注意事项:
    - 前 270 期返回 NaN (adv20 20 + decay 9 + sum 250 - 重叠)
    - 250 日长窗口需足够历史数据
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.ts import delta, ts_sum

__all__ = ["alpha_039"]

DIRECTION = 1


def alpha_039(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #39: 价格动量-成交量衰减 (adv20+长窗口)。

    公式: -rank(delta(close,7)*(1-rank(decay_linear(volume/adv20,9))))*(1+rank(sum(returns,250)))

    Args:
        ctx: 因子数据上下文

    Returns:
        价格动量-成交量衰减因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    adv20 = ctx.get_adv(20)
    vol_decay = decay_linear(ctx.volume / adv20, 9)
    momentum = delta(ctx.close, 7) * (1 - rank(vol_decay))
    return (-1 * rank(momentum)) * (1 + rank(ts_sum(returns, 250)))
