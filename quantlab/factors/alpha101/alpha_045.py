"""
Alpha101 #45 — 三因子乘积
========================================

公式:
    -1 * ((rank(sum(delay(close,5),20)/20) * correlation(close, volume, 2))
           * rank(correlation(sum(close,5), sum(close,20), 2)))

公式解释:
    三部分相乘取负：
    1. 延迟 5 日收盘价的 20 日均值排名；
    2. 收盘价与成交量的 2 日相关性；
    3. 5 日与 20 日收盘价均值的 2 日相关性排名。

分类:
    三因子乘积 (three_factor_product)

信号方向:
    反向 (-1) — 因子值越大越看空

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay
    - ts_sum
    - corr
    - rank (截面)

背后逻辑:
    延迟收盘价均值排名反映历史价格水平，
    量价相关性反映短期量价关系，
    均线相关性反映趋势一致性。
    三者乘积取负，捕捉"高价+量价正相关+趋势一致"的反转机会。

适用场景:
    多维度量价组合反转策略。

变种与优化:
    - 可使用不同窗口 (5/20/2)
    - 可用 decay_linear 替代简单均值
    - 可引入横截面标准化

注意事项:
    - 前 24 期返回 NaN (delay 5 + ts_sum 20 + corr 2)
    - 乘积结构对符号敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_045"]

DIRECTION = -1


def alpha_045(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #45: 三因子乘积。

    公式: -1 * (rank(sum(delay(close,5),20)/20) * corr(close,volume,2)
           * rank(corr(sum(close,5), sum(close,20), 2)))

    Args:
        ctx: 因子数据上下文

    Returns:
        三因子乘积因子面板 (date × symbol)
    """
    close = ctx.close
    part1 = rank(ts_sum(delay(close, 5), 20) / 20)
    part2 = corr(close, ctx.volume, 2)
    part3 = rank(corr(ts_sum(close, 5), ts_sum(close, 20), 2))
    return -1 * (part1 * part2 * part3)
