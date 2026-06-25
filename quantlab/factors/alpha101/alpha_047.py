"""
Alpha101 #47 — 复合量价因子 (adv20+vwap)
========================================

公式:
    (((rank(1 / close) * volume) / adv20)
     * ((high * rank(high - close)) / (sum(high, 5) / 5)))
    - rank(vwap - delay(vwap, 5))

公式解释:
    第一部分：收盘价倒数排名乘以相对成交量 (volume/adv20)，
    再乘以最高价偏离均值的程度 (high*rank(high-close)/(sum(high,5)/5))；
    第二部分减去 VWAP 的 5 日变化排名。
    综合价格水平、成交量和 VWAP 动量。

分类:
    复合量价因子 (composite_volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）
    - ADV20 20 日平均成交量（由 volume 派生）
    - VWAP 成交量加权均价（日频）

算子依赖:
    - rank (截面)
    - ts_sum
    - delay
    - ctx.get_adv

背后逻辑:
    低价 (1/close 大) + 放量 (volume/adv20 大) + 上影线 (high-close 大)
    叠加 VWAP 下降，
    捕捉"低价放量上影"的反转机会。

适用场景:
    低价放量反转策略。

变种与优化:
    - 可引入成交量比率 (vwap/open)
    - 可用 amount 替代 volume
    - 可调整窗口 (5/20)

注意事项:
    - 前 24 期返回 NaN (adv20 20 + delay 5 - 重叠)
    - 乘积结构对极端值敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_047"]

DIRECTION = 1


def alpha_047(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #47: 复合量价因子 (adv20+vwap)。

    公式: (rank(1/close)*volume/adv20)*(high*rank(high-close)/(sum(high,5)/5))
          - rank(vwap-delay(vwap,5))

    Args:
        ctx: 因子数据上下文

    Returns:
        复合量价因子面板 (date × symbol)
    """
    close = ctx.close
    adv20 = ctx.get_adv(20)
    vwap = ctx.get_vwap()
    part1 = (rank(1 / close) * ctx.volume) / adv20
    part2 = (ctx.high * rank(ctx.high - close)) / (ts_sum(ctx.high, 5) / 5)
    part3 = rank(vwap - delay(vwap, 5))
    return part1 * part2 - part3
