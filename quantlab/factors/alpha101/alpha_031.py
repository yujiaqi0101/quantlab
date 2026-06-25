"""
Alpha101 #31 — 多因子组合 (adv20)
========================================

公式:
    (rank(rank(rank(decay_linear((-1 * rank(rank(delta(close, 10)))), 10))))
     + rank((-1 * delta(close, 3))))
    + sign(scale(correlation(adv20, low, 12)))

公式解释:
    三部分之和：
    1. 多层排名和衰减加权的 10 日价格变化；
    2. 3 日价格变化排名；
    3. 均量与最低价相关性的符号。
    结合价格动量反转和量价关系。

分类:
    多因子组合 (multi_factor_combo)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - ADV20 20 日平均成交量（由 volume 派生）
    - LOW 最低价（日频，后复权）

算子依赖:
    - delta
    - rank (截面)
    - decay_linear
    - corr
    - scale
    - sign (内置)
    - ctx.get_adv

背后逻辑:
    多层排名衰减动量捕捉价格反转，
    3 日变化排名补充短期反转，
    量价相关性符号提供方向确认。
    三者结合形成稳健的多因子信号。

适用场景:
    多因子动量反转 + 量价关系组合策略。

变种与优化:
    - 可使用 PCA 确定权重
    - 可引入机器学习方法
    - 可调整窗口 (10/3/12)

注意事项:
    - 前 31 期返回 NaN (adv20 20 + corr 12 - 重叠 + decay 10)
    - 多层 rank 使分布均匀但丢失幅度
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank, scale
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_031"]

DIRECTION = 1


def alpha_031(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #31: 多因子组合 (adv20)。

    公式: rank(rank(rank(decay_linear(-rank(rank(delta(close,10))),10))))
          + rank(-delta(close,3)) + sign(scale(corr(adv20,low,12)))

    Args:
        ctx: 因子数据上下文

    Returns:
        多因子组合因子面板 (date × symbol)
    """
    close = ctx.close
    adv20 = ctx.get_adv(20)
    part1 = rank(rank(rank(decay_linear(-1 * rank(rank(delta(close, 10))), 10))))
    part2 = rank(-1 * delta(close, 3))
    part3 = np.sign(scale(corr(adv20, ctx.low, 12)))
    return part1 + part2 + part3
