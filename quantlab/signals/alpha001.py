"""
Alpha101 #001 策略 —— 横截面均值回归

公式（WorldQuant Alpha101 #001 原文）:
    alpha = rank(MA(close, period)) - rank(close)

含义（每根 bar 上对所有 symbol 做横截面 rank）:
    - rank(MA) 高, rank(close) 低  →  close 短期低于自身均线
                                    →  相对其他标的出现超跌
                                    →  alpha 偏正  →  做多候选
    - rank(MA) 低, rank(close) 高  →  close 短期高于自身均线
                                    →  相对其他标的出现超涨
                                    →  alpha 偏负  →  不做多（可做空）

实现要点:
    - 走 quantlab.signals.base.SignalStrategy 契约
    - signal(ctx) 返回**连续 score**（不是离散 {0, 1}）
      BarEngine 会 signal.iloc[i-1].to_dict() 喂给 PortfolioConstructor
      TopN(n) 选 score>0 中前 N 个
    - 横截面 rank 走 pandas DataFrame.rank(axis=1)
    - 不在 factors 库另开文件：
        alpha001 天然是 multi-symbol cross-sectional 因子
        现有 factors/* 都是 per-symbol，与本策略 API 不匹配
        直接在策略内部计算，避免 cache key 跨 symbol 污染
    - NaN（warm-up 前 period-1 根）由 TopN 的 >0 检查自动排除

参数:
    period : int
        MA 窗口，默认 10（WorldQuant 原版）
"""

from __future__ import annotations

import pandas as pd

from quantlab.signals.base import SignalStrategy


class Alpha001Strategy(SignalStrategy):
    """
    Alpha101 #001: rank(MA(close, period)) - rank(close)

    Parameters
    ----------
    period : int
        MA 计算窗口，默认 10（WorldQuant 原版）
    """

    def __init__(self, period: int = 10):
        self.period = int(period)
        if self.period < 2:
            raise ValueError(
                f"period must be >= 2, got {period}"
            )

    def signal(self, ctx) -> pd.DataFrame:
        # 1) 收集每个 symbol 的 close
        #    严格保持 ctx.data.keys() 顺序
        symbols = list(ctx.data.keys())
        if not symbols:
            return pd.DataFrame()

        close_df = pd.DataFrame(
            {sym: ctx.data[sym]["close"] for sym in symbols}
        )

        # 2) MA（per-symbol rolling）
        #    前 period-1 根是 NaN，符合"warm-up 不做决策"语义
        ma_df = close_df.rolling(self.period).mean()

        # 3) 横截面 rank（每根 bar 在 symbols 上排名）
        #    method='average' 避免并列时跳号；ascending=True 默认
        rank_close = close_df.rank(axis=1, ascending=True)
        rank_ma = ma_df.rank(axis=1, ascending=True)

        # 4) alpha001 = rank(MA) - rank(close)
        #    越大 → 越该做多
        #    直接返回连续 score，让 TopN 选最大的前 N 个
        alpha = rank_ma - rank_close

        return alpha


# ---------------------------------------------------------------------- #
# 工厂方法
# ---------------------------------------------------------------------- #
def make_alpha001(period: int = 10) -> Alpha001Strategy:
    """显式工厂，避免依赖默认参数顺序"""
    return Alpha001Strategy(period=period)


# ---------------------------------------------------------------------- #
# 典型参数网格
# ---------------------------------------------------------------------- #
ALPHA001_PARAM_SPACE: dict = {
    # period 10 是 WorldQuant 原版；
    # 上下小幅扫描以检验稳定性
    "period": [5, 10, 15, 20],
}
