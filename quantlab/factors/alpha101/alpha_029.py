"""
Alpha101 #29 — 深层嵌套动量反转
========================================

公式:
    min(product(rank(rank(scale(log(sum(ts_min(rank(rank((-1 * rank(delta((close - 1), 5))))), 2), 1)))))), 1), 5)
    + ts_rank(delay((-1 * returns), 6), 5)

公式解释:
    极其复杂的嵌套结构：
    对收盘价变化 (close-1) 的 5 日变化排名取负、再排名、取 2 日最小值、求和、取对数、缩放、排名、排名、求积、与 5 取最小值。
    加上延迟收益率的时序排名。
    高度非线性的量价信号。

分类:
    深层嵌套-动量反转 (deep_nested_momentum_reversal)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - delta
    - rank (截面)
    - ts_min
    - ts_sum
    - scale
    - log (内置 np.log)
    - product
    - min (内置)
    - delay
    - ts_rank

背后逻辑:
    深层嵌套通过多次非线性变换提取价格的极端反转信号。
    取对数压缩量级，缩放标准化，求积放大一致性，
    与延迟收益率时序排名结合，捕捉动量反转。

适用场景:
    非线性动量反转策略。

变种与优化:
    - 可简化嵌套结构
    - 可使用机器学习方法替代手工嵌套
    - 可调整窗口 (5/2/1/5)

注意事项:
    - 前 11 期返回 NaN (delta 5 + ts_min 2 + delay 6 + ts_rank 5 - 重叠)
    - log 要求输入为正，需处理负值
    - 嵌套结构对数据质量敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank, scale
from quantlab.factors.operators.ts import delay, delta, product, ts_min, ts_rank, ts_sum

__all__ = ["alpha_029"]

DIRECTION = 1


def alpha_029(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #29: 深层嵌套动量反转。

    公式: min(product(rank(rank(scale(log(sum(ts_min(rank(rank(-rank(delta(close-1,5))), 2), 1))))), 1), 5)
          + ts_rank(delay(-returns, 6), 5)

    Args:
        ctx: 因子数据上下文

    Returns:
        深层嵌套动量反转因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    # 内层: -rank(delta(close-1, 5))
    inner = -1 * rank(delta(ctx.close - 1, 5))
    # 嵌套 rank
    r1 = rank(rank(inner))
    # ts_min(rank, 2) → 这里 ts_min 输入需为面板
    tm = ts_min(r1, 2)
    # sum(..., 1) → 即本身
    s = ts_sum(tm, 1)
    # log 要求正数，用 abs+小常数保护
    s_safe = s.where(s > 0).fillna(1e-12)
    lg = np.log(s_safe.where(s_safe > 0))
    # scale + 双 rank
    sc = scale(lg)
    r2 = rank(rank(sc))
    # product(..., 1) → 即本身
    p = product(r2, 1)
    # min(p, 5)
    part1 = p.clip(upper=5)
    part2 = ts_rank(delay(-1 * returns, 6), 5)
    return part1 + part2
