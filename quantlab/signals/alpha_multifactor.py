"""
Alpha101 多因子策略 —— Alpha#9 + Alpha#40 + Alpha#49

公式（Kakushadze, 2016）:
    alpha#9  = ts_min(close, 5) - correlation(sum(close, 5), sum(close, 20), 5)
    alpha#40 = - ts_rank(high, 10) * sign(delta(close, 1))
    alpha#49 = - ts_rank(delay(close, 10), 10) * sign(delta(close, 1))
             + sign(delta(volume / adv20, 5))

融合方式（标准 WorldQuant 风格）:
    对每个 alpha 在多标的上做 **横截面 rank**（每根 bar 上排名）
    score = w9 * rank(alpha9) + w40 * rank(alpha40) + w49 * rank(alpha49)

    三个 alpha 各自量纲不同（无 rank 不可加）
    排序在 [1, N]，加权和仍 ∈ (1, N)

为什么不在 factors 层做 rank:
    alpha009/040/049 都是 per-symbol 时序因子（多 symbol 各算各的）
    cross-section rank 必须看到所有 symbol 才能计算
    所以 rank 在 strategy 层做，factors 层只管 per-symbol

参数:
    w9, w40, w49 : float
        三个 alpha 的横截面 rank 融合权重
        默认等权 (1/3, 1/3, 1/3)
"""

from __future__ import annotations

import pandas as pd

from quantlab.factors.alpha101 import (
    alpha009,
    alpha040,
    alpha049,
)
from quantlab.signals.base import SignalStrategy


class AlphaMultiFactorStrategy(SignalStrategy):
    """
    Alpha101 多因子融合: rank(a9)*w9 + rank(a40)*w40 + rank(a49)*w49

    Parameters
    ----------
    w9 : float
        alpha009 的横截面 rank 权重，默认 1/3
    w40 : float
        alpha040 的横截面 rank 权重，默认 1/3
    w49 : float
        alpha049 的横截面 rank 权重，默认 1/3
    """

    def __init__(
        self,
        w9: float = 1.0 / 3,
        w40: float = 1.0 / 3,
        w49: float = 1.0 / 3,
    ):
        self.w9 = float(w9)
        self.w40 = float(w40)
        self.w49 = float(w49)

        # 权重校验
        if min(self.w9, self.w40, self.w49) < 0:
            raise ValueError(
                f"weights must be >= 0, got "
                f"w9={w9}, w40={w40}, w49={w49}"
            )
        total = self.w9 + self.w40 + self.w49
        if total <= 0:
            raise ValueError(
                f"sum of weights must be > 0, got {total}"
            )

    def signal(self, ctx) -> pd.DataFrame:
        symbols = list(ctx.data.keys())
        if not symbols:
            return pd.DataFrame()

        # 1) 每个 symbol 算三个 alpha
        a9 = {sym: alpha009(ctx, sym) for sym in symbols}
        a40 = {sym: alpha040(ctx, sym) for sym in symbols}
        a49 = {sym: alpha049(ctx, sym) for sym in symbols}

        df9 = pd.DataFrame(a9)
        df40 = pd.DataFrame(a40)
        df49 = pd.DataFrame(a49)

        # 2) 横截面 rank（per-bar）
        #    method='average' 处理并列，ascending=True（默认）
        #    结果 ∈ [1, N_symbols]
        r9 = df9.rank(axis=1, ascending=True)
        r40 = df40.rank(axis=1, ascending=True)
        r49 = df49.rank(axis=1, ascending=True)

        # 3) 加权融合
        #    NaN（任一 alpha 缺失）会被传播，TopN 不会选
        score = (
            self.w9 * r9
            + self.w40 * r40
            + self.w49 * r49
        )

        return score


# ---------------------------------------------------------------------- #
# 工厂方法
# ---------------------------------------------------------------------- #
def make_alpha_multifactor(
    w9: float = 1.0 / 3,
    w40: float = 1.0 / 3,
    w49: float = 1.0 / 3,
) -> AlphaMultiFactorStrategy:
    """显式工厂"""
    return AlphaMultiFactorStrategy(w9=w9, w40=w40, w49=w49)


# ---------------------------------------------------------------------- #
# 典型参数网格
#   等权是默认
#   网格让 Optimizer 看看：
#     - 是否某个 alpha 单独更有效（把另外两个权重置 0）
#     - 等权 vs 偏权重的差异
# ---------------------------------------------------------------------- #
ALPHA_MULTIFACTOR_PARAM_SPACE: dict = {
    "w9":  [0.0, 1.0 / 3, 1.0],
    "w40": [0.0, 1.0 / 3, 1.0],
    "w49": [0.0, 1.0 / 3, 1.0],
}
