"""
Alpha191 #57 — KDJ K值(单次平滑)
========================================

公式:
    SMA(RSV, 3, 1)

    其中 RSV = (CLOSE - LLV(LOW,9)) / (HHV(HIGH,9) - LLV(LOW,9)) * 100

公式解释:
    计算 RSV（未成熟随机值）的3日SMA，即 KDJ 指标中的 K 值
    （未完全平滑版本，相比 Alpha28 缺少二次平滑）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - ts_max (HHV)
    - ts_min (LLV)
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    与 Alpha28 类似但未进行二次平滑，响应速度更快。
    K 值反映价格在近期高低区间中的相对位置，正向选择偏好强势股。

适用场景:
    快速响应的动量策略。

变种与优化:
    - 可调整 RSV 和 SMA 窗口期
    - 结合 D 值和 J 值使用
    - 进行二次平滑降噪 (Alpha28)

注意事项:
    - 文档未明确 RSV 窗口期，此处采用 KDJ 标准 9 日
    - 未平滑的 K 值噪声较大
    - 前 9 期数据不足时返回 NaN (RSV 预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import ts_max, ts_min

__all__ = ["alpha_057"]

DIRECTION = 1
DEFAULT_RSV_PERIOD = 9
DEFAULT_SMA_N = 3
DEFAULT_SMA_M = 1


def alpha_057(
    ctx: FactorContext,
    rsv_period: int = DEFAULT_RSV_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #57: KDJ K值(单次平滑)。

    公式: SMA(RSV, sma_n, sma_m)
          RSV = (CLOSE-LLV(LOW,rsv_period))/(HHV(HIGH,rsv_period)-LLV(LOW,rsv_period))*100

    Args:
        ctx: 因子数据上下文
        rsv_period: RSV 高低点窗口期 (默认 9)
        sma_n: SMA 分母参数 (默认 3)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        KDJ K 值(单次平滑)因子面板 (date × symbol)
    """
    close = ctx.close
    llv = ts_min(ctx.low, rsv_period)
    hhv = ts_max(ctx.high, rsv_period)
    rng = (hhv - llv).replace(0, pd.NA)
    rsv = (close - llv) / rng * 100
    return sma(rsv, sma_n, sma_m)
