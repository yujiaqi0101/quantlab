"""
Alpha191 #76 — 成交量效率变异系数
========================================

公式:
    STD(|RET|/V, 20) / MEAN(|RET|/V, 20)

公式解释:
    计算20日内 |收益率/成交量| 的标准差除以其均值，
    即"单位成交量驱动的收益率"的变异系数 (CV)。

分类:
    波动率 (volatility)

信号方向:
    反向 (-1) — 因子值越大越看空

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - RET 日收益率（由 close 派生）

算子依赖:
    - ts_std
    - ts_mean
    - abs

背后逻辑:
    该因子衡量单位成交量驱动的收益率波动。
    变异系数高表示收益率效率不稳定，
    反向选择偏好效率稳定的股票。

适用场景:
    价格效率分析策略，筛选成交量-价格关系稳定的标的。

变种与优化:
    - 可调整窗口期 (20 → 10/40)
    - 使用成交额 (AMOUNT) 替代成交量
    - 加入波动率归一化

注意事项:
    - 成交量极小时可能导致因子值异常，需做下限处理
    - 前 20 期返回 NaN (ts_std/ts_mean 预热)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean, ts_std

__all__ = ["alpha_076"]

DIRECTION = -1


def alpha_076(ctx: FactorContext, period: int = 20) -> pd.DataFrame:
    """Alpha191 #76: 成交量效率变异系数。

    公式: STD(|RET|/V, period) / MEAN(|RET|/V, period)

    Args:
        ctx: 因子数据上下文
        period: 窗口期 (默认 20)

    Returns:
        成交量效率变异系数面板 (date × symbol)
    """
    returns = ctx.get_returns()
    vol = ctx.volume
    # 避免除零: 成交量为 0 时设为 NaN
    ratio = np.abs(returns) / vol.replace(0, np.nan)
    std = ts_std(ratio, period)
    mean = ts_mean(ratio, period)
    return std / mean
