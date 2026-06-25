"""
Alpha191 #69 — 20日DTM/DBM动量差
========================================

公式:
    IF(SUM(DTM,20)>SUM(DBM,20):
        (SUM(DTM,20)-SUM(DBM,20))/SUM(DTM,20),
       IF(SUM(DTM,20)=SUM(DBM,20):
           0,
           (SUM(DTM,20)-SUM(DBM,20))/SUM(DBM,20)))

公式解释:
    DTM: IF(OPEN<=DELAY(OPEN,1), 0, MAX(HIGH-OPEN, OPEN-DELAY(OPEN,1)))
    DBM: IF(OPEN>=DELAY(OPEN,1), 0, MAX(OPEN-LOW, OPEN-DELAY(OPEN,1)))
    根据 DTM 与 DBM 的大小关系选择不同分母的动量比值。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW（日频，后复权）

算子依赖:
    - delay
    - ts_sum

背后逻辑:
    DTM/DBM 衡量开盘跳空与日内极值的强度，比值反映多空力量对比。

适用场景:
    开盘跳空动量策略。

变种与优化:
    - 调整窗口 (20 → 10/40)
    - 使用绝对差而非比值

注意事项:
    - 分母为 0 时返回 0
    - 前 21 期返回 NaN (delay 1 + ts_sum 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_069"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_069(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #69: 20日DTM/DBM动量差。

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        DTM/DBM 动量差因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low

    prev_open = delay(open_, 1)

    # DTM: IF(OPEN<=prevOPEN, 0, MAX(HIGH-OPEN, OPEN-prevOPEN))
    dtm_val1 = np.maximum(high - open_, open_ - prev_open)
    dtm = np.where(open_ <= prev_open, 0.0, dtm_val1)
    dtm = pd.DataFrame(dtm, index=open_.index, columns=open_.columns)

    # DBM: IF(OPEN>=prevOPEN, 0, MAX(OPEN-LOW, OPEN-prevOPEN))
    dbm_val1 = np.maximum(open_ - low, open_ - prev_open)
    dbm = np.where(open_ >= prev_open, 0.0, dbm_val1)
    dbm = pd.DataFrame(dbm, index=open_.index, columns=open_.columns)

    sum_dtm = ts_sum(dtm, period)
    sum_dbm = ts_sum(dbm, period)

    diff = sum_dtm - sum_dbm

    # IF cond1: sum_dtm > sum_dbm → diff / sum_dtm
    # ELIF cond2: sum_dtm == sum_dbm → 0
    # ELSE: diff / sum_dbm
    safe_dtm = sum_dtm.where(sum_dtm.abs() > 0, np.nan)
    safe_dbm = sum_dbm.where(sum_dbm.abs() > 0, np.nan)

    result = diff / safe_dbm  # 默认 ELSE 分支
    result = result.where(sum_dtm != sum_dbm, 0.0)  # cond2 相等
    result = result.where(~(sum_dtm > sum_dbm), diff / safe_dtm)  # cond1

    return result
