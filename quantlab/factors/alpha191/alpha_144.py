"""
Alpha191 #144 — 下跌日价格效率
========================================

公式:
    SUM(下跌日 |RET|, 20) / MEAN(AMOUNT, 20)

公式解释:
    计算20日内下跌日的绝对收益率之和，
    除以20日成交额均值。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - AMOUNT 成交额（日频）

算子依赖:
    - sum_if (条件滚动求和)
    - ts_mean (滚动均值)

背后逻辑:
    衡量下跌日的价格效率——
    单位成交额驱动的下跌幅度。
    高值表示下跌日价格效率高，卖方力量集中。

适用场景:
    下跌效率分析策略。

变种与优化:
    - 可调整窗口期 (20 → 10/30)
    - 使用成交量替代成交额
    - 结合上涨日效率对比

注意事项:
    - 成交额极小时因子值异常
    - 需做下限处理
    - 前 19 期返回 NaN (ts_mean 20)
    - 分母为 0 时返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import sum_if
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_144"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_144(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #144: 下跌日价格效率。

    公式: SUM(下跌日 |RET|, period) / MEAN(AMOUNT, period)

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 20)

    Returns:
        下跌日价格效率因子面板 (date × symbol)
    """
    ret = ctx.get_returns()
    abs_ret = ret.abs()
    # 下跌日条件: RET < 0
    down_cond = (ret < 0).astype(float)
    down_abs_sum = sum_if(abs_ret, down_cond, period)
    amount = ctx.get_amount()
    mean_amount = ts_mean(amount, period)
    # 分母为 0 时返回 NaN
    safe_amount = mean_amount.where(mean_amount > 0, np.nan)
    return down_abs_sum / safe_amount
