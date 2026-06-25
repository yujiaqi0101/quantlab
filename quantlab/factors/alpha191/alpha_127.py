"""
Alpha191 #127 — 12日回撤均方根
========================================

公式:
    sqrt( mean( (100 * (CLOSE - ts_max(CLOSE, 12)) / ts_max(CLOSE, 12))^2 ) )

公式解释:
    计算 12 日内从最高点的回撤百分比，平方后取均值，再开方，得到回撤均方根 (RMS)。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_max
    - ts_mean

背后逻辑:
    衡量近期回撤的剧烈程度。RMS 比简单平均更敏感于极端回撤。
    正向偏好回撤大的股票，可能反映超卖后的反弹机会。

适用场景:
    回撤分析策略，捕捉超卖反弹机会。

变种与优化:
    - 可调整窗口期 (12 → 20/60)
    - 可使用对数回撤替代百分比回撤
    - 可结合波动率做标准化

注意事项:
    - ts_max(CLOSE,12) 为 0 时分母为 0，需确保价格 > 0
    - 回撤百分比始终 <= 0，平方后为正
    - 前 12 期数据不足返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_max, ts_mean

__all__ = ["alpha_127"]

DIRECTION = 1
DEFAULT_PERIOD = 12


def alpha_127(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #127: 12日回撤均方根。

    公式: sqrt( mean( (100 * (CLOSE - ts_max(CLOSE, period)) / ts_max(CLOSE, period))^2 ) )

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 12)

    Returns:
        回撤 RMS 面板 (date × symbol)
    """
    close = ctx.close
    high_max = ts_max(close, period)
    # 分母为 0 时返回 NaN (价格应 > 0, 此处防御性处理)
    high_max_safe = high_max.where(high_max.abs() > 1e-12, np.nan)
    drawdown_pct = 100.0 * (close - high_max_safe) / high_max_safe
    # 注意: 公式 mean 是对 (drawdown_pct)^2 在窗口内求均值
    # 原文档未明确 mean 窗口, 这里取与 max 相同的 period 保持一致
    squared = drawdown_pct ** 2
    return np.sqrt(ts_mean(squared, period))
