"""
Alpha191 #4 — 8日均价与2日均价条件判断
========================================

公式:
    IF((MA8+STD8 < MA2) ? -1 :
      IF((MA2 < MA8-STD8) ? 1 :
        IF((V/MA20>=1) ? 1 : -1)))

公式解释:
    复合条件判断:
    - 当 8日均价+8日标准差 < 2日均价: 返回 -1 (短期超涨反向)
    - 否则当 2日均价 < 8日均价-8日标准差: 返回 1 (短期超跌反弹)
    - 否则当 成交量/20日均量 >= 1: 返回 1 (放量看多)
    - 否则返回 -1

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_mean
    - ts_std
    - delay

背后逻辑:
    均值回复 + 量价配合：极端上涨反向，极端下跌反弹，
    未极端时按放量方向判断。

适用场景:
    短期反转与量能策略。

变种与优化:
    - 调整均价窗口 (8/2 → 20/5)
    - 使用波动率调整阈值

注意事项:
    - STD 采用样本标准差 ddof=1
    - 前 8 期数据不足时返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean, ts_std

__all__ = ["alpha_004"]

DIRECTION = 1


def alpha_004(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #4: 8日均价与2日均价条件判断。

    公式: 多层 IF 条件返回 {-1, 1}

    Args:
        ctx: 因子数据上下文

    Returns:
        条件因子面板 (date × symbol)，值为 {-1, 1} 或 NaN
    """
    close = ctx.close
    volume = ctx.volume

    ma8 = ts_mean(close, 8)
    std8 = ts_std(close, 8)
    ma2 = ts_mean(close, 2)
    ma20_vol = ts_mean(volume, 20)

    cond1 = (ma8 + std8) < ma2
    cond2 = ma2 < (ma8 - std8)
    cond3 = (volume / ma20_vol) >= 1.0

    # 三层嵌套: cond1 ? -1 : (cond2 ? 1 : (cond3 ? 1 : -1))
    result = np.where(cond3, 1.0, -1.0)
    result = np.where(cond2, 1.0, result)
    result = np.where(cond1, -1.0, result)

    out = pd.DataFrame(result, index=close.index, columns=close.columns)
    # 仅在所有数据可用时返回有效值
    mask = ma8.notna() & ma2.notna() & ma20_vol.notna()
    return out.where(mask)
