"""
Alpha101 #25 — 多因子乘积 (adv20)
========================================

公式:
    rank(((((-1 * returns) * adv20) * vwap) * (high - close)))

公式解释:
    负收益率、20 日均量、VWAP、最高价与收盘价差四者的乘积，截面排名。
    综合多个量价维度。

分类:
    多因子乘积 (multi_factor_product)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - RETURNS 日收益率（由 close 派生）
    - ADV20 20 日平均成交量（由 volume 派生）
    - VWAP 成交量加权均价（日频）
    - HIGH 最高价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank (截面)
    - ctx.get_adv

背后逻辑:
    负收益率反映下跌，
    adv20 反映成交活跃度，
    vwap 反映日内均价，
    (high-close) 反映上影线长度。
    四者乘积捕捉"下跌+放量+上影线"组合，
    可能预示反转机会。

适用场景:
    多维量价组合反转策略。

变种与优化:
    - 可用 log 变换稳定量级
    - 可调整 adv 窗口 (20 → 10/50)
    - 可分项排名后求和

注意事项:
    - 前 21 期返回 NaN (adv20 需 20 期 + returns 1 期)
    - 乘积结构对极端值敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank

__all__ = ["alpha_025"]

DIRECTION = 1


def alpha_025(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #25: 多因子乘积 (adv20)。

    公式: rank((-returns)*adv20*vwap*(high-close))

    Args:
        ctx: 因子数据上下文

    Returns:
        多因子乘积因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    adv20 = ctx.get_adv(20)
    vwap = ctx.get_vwap()
    return rank((-1 * returns) * adv20 * vwap * (ctx.high - ctx.close))
