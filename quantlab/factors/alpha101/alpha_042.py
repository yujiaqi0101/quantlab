"""
Alpha101 #42 — VWAP偏离比率 [Delay-0]
========================================

公式:
    rank(vwap - close) / rank(vwap + close)

公式解释:
    VWAP 与收盘价差的截面排名，除以 VWAP 与收盘价和的截面排名。
    衡量 VWAP 偏离的相对程度。这是 0 延迟 Alpha，需在收盘时交易。

分类:
    VWAP偏离比率 (vwap_deviation_ratio)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VWAP 成交量加权均价（日频，缺失时由 amount/volume 近似）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank (截面)

背后逻辑:
    当 VWAP > close (日内均价高于收盘价，尾盘下跌) 时，
    分子 rank 高，分母 rank 也高但变化小，比值较高 → 看多 (次日反弹)。
    反之看空。捕捉日内 VWAP 与收盘价的相对偏离。

适用场景:
    日内 VWAP 偏离反转策略，适合收盘时交易 (Delay-0)。

变种与优化:
    - 可使用对数比率替代线性比率
    - 可结合多日累积偏离
    - 可引入成交量权重

注意事项:
    - 分母 rank 可能为 0，需处理除零 (用绝对值下限)
    - 0 延迟因子需在收盘时执行，滑点风险高
    - VWAP 缺失时由 amount/volume 近似

注意事项 (补充):
    - 单标的时 rank 退化 (无截面比较)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank

__all__ = ["alpha_042"]

DIRECTION = 1


def alpha_042(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #42: VWAP偏离比率。

    公式: rank(vwap - close) / rank(vwap + close)

    Args:
        ctx: 因子数据上下文

    Returns:
        VWAP偏离比率因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    numerator = rank(vwap - ctx.close)
    denominator = rank(vwap + ctx.close)
    denominator_safe = denominator.where(denominator.abs() > 1e-12)
    return numerator / denominator_safe
