"""
Alpha101 #36 — 加权多因子 (adv20+vwap+长窗口)
========================================

公式:
    (2.21 * rank(correlation((close - open), delay(volume, 1), 15)))
    + (0.7 * rank((open - close)))
    + (0.73 * rank(Ts_Rank(delay((-1 * returns), 6), 5)))
    + rank(abs(correlation(vwap, adv20, 6)))
    + (0.6 * rank(((sum(close, 200) / 200 - open) * (close - open))))

公式解释:
    五个子因子的加权和：
    1. 日内涨跌幅与延迟成交量的相关性 (2.21 倍)；
    2. 开盘收盘差 (0.7 倍)；
    3. 延迟收益率的时序排名 (0.73 倍)；
    4. VWAP 与均量相关性的绝对值；
    5. 200 日均线偏离与日内涨跌幅的乘积 (0.6 倍)。
    精心设计的多因子组合。

分类:
    加权多因子 (weighted_multi_factor)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - ADV20 20 日平均成交量（由 volume 派生）
    - VWAP 成交量加权均价（日频）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - corr
    - delay
    - ts_rank
    - ts_sum
    - rank (截面)
    - abs (内置)
    - ctx.get_adv

背后逻辑:
    五个子因子覆盖日内量价、日内涨跌、收益率动量、量价相关、长期均线偏离，
    加权组合形成稳健的多因子信号。
    权重 (2.21/0.7/0.73/1.0/0.6) 反映各因子的预期贡献。

适用场景:
    多因子加权选股策略。

变种与优化:
    - 可使用 PCA 确定最优权重
    - 可引入机器学习方法
    - 可调整相关性窗口 (15/6)

注意事项:
    - 前 214 期返回 NaN (adv20 20 + corr 15 - 重叠 + sum 200)
    - 200 日长窗口需足够历史数据
    - 权重为经验值，需定期校准
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_rank, ts_sum

__all__ = ["alpha_036"]

DIRECTION = 1


def alpha_036(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #36: 加权多因子 (adv20+vwap+长窗口)。

    公式: 2.21*rank(corr(close-open, delay(volume,1), 15))
          + 0.7*rank(open-close)
          + 0.73*rank(ts_rank(delay(-returns,6), 5))
          + rank(abs(corr(vwap, adv20, 6)))
          + 0.6*rank((sum(close,200)/200 - open)*(close-open))

    Args:
        ctx: 因子数据上下文

    Returns:
        加权多因子因子面板 (date × symbol)
    """
    close = ctx.close
    returns = ctx.get_returns()
    adv20 = ctx.get_adv(20)
    vwap = ctx.get_vwap()

    part1 = 2.21 * rank(corr(close - ctx.open, delay(ctx.volume, 1), 15))
    part2 = 0.7 * rank(ctx.open - close)
    part3 = 0.73 * rank(ts_rank(delay(-1 * returns, 6), 5))
    part4 = rank(abs(corr(vwap, adv20, 6)))
    part5 = 0.6 * rank((ts_sum(close, 200) / 200 - ctx.open) * (close - ctx.open))
    return part1 + part2 + part3 + part4 + part5
