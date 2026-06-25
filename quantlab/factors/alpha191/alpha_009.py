"""
Alpha191 #9 — 7日价格效率SMA
========================================

公式:
    SMA(((HIGH+LOW)/2 - (DELAY(HIGH,1)+DELAY(LOW,1))/2) * (HIGH-LOW) / VOLUME, 7, 2)

公式解释:
    计算中间价的日变化量乘以当日振幅再除以成交量，然后进行7日SMA平滑
    （alpha=2/7）。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    该因子衡量的是单位成交量驱动的价格变化幅度。中间价变化代表价格方向，
    振幅代表价格活跃度，除以成交量得到标准化后的价格效率。SMA 平滑减少噪声。
    正向选择偏好单位成交量能驱动更大价格变化的标的。

适用场景:
    价格效率选股策略，偏好放量驱动的价格变动。

变种与优化:
    - 可调整 SMA 窗口期与参数 (7,2 → 10,2 / 14,1)
    - 使用不同的价格基准 (收盘价 / 典型价格)
    - 加入成交额替代成交量

注意事项:
    - 成交量极小 (VOLUME=0 停牌) 时因子值需置 NaN，避免异常放大
    - 对成交量做下限保护 max(VOLUME, 1) 后再相除
    - 前 7 期数据不足时返回 NaN (SMA 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_009"]

DIRECTION = 1
DEFAULT_PERIOD = 7
DEFAULT_M = 2


def alpha_009(
    ctx: FactorContext,
    period: int = DEFAULT_PERIOD,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #9: 7日价格效率SMA。

    公式: SMA((mid - delay(mid,1)) * (HIGH-LOW) / VOLUME, period, m)
        其中 mid = (HIGH+LOW)/2

    Args:
        ctx: 因子数据上下文
        period: SMA 窗口期 (默认 7)
        m: SMA 分子参数 (默认 2)

    Returns:
        价格效率因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    mid = (high + low) / 2.0
    prev_mid = (delay(high, 1) + delay(low, 1)) / 2.0
    mid_change = mid - prev_mid
    amplitude = high - low
    # 成交量下限保护：VOLUME<=0 时置 NaN，避免除零
    safe_vol = ctx.volume.where(ctx.volume > 0, np.nan)
    raw = mid_change * amplitude / safe_vol
    return sma(raw, period, m)
