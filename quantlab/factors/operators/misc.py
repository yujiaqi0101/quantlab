"""
工具算子 (misc operators)
=========================

Alpha191/Alpha101 中的辅助算子。

算子清单:
    signed_power(x, n) — 带符号幂: sign(x) * |x|^n
    sum_if(x, cond, n) — 条件滚动求和: 窗口内 cond 为真时 x 的和
    cumsum(x)          — 累积求和 (沿时间轴)
    highday(x, n)      — n 期最大值出现距今天数 (0=今天)
    lowday(x, n)       — n 期最小值出现距今天数 (0=今天)
    sequence(n)        — 生成序列 [1, 2, ..., n]
    tr(high, low, prev_close) — 真实波幅 True Range
    sumac(x, n)        — 滚动窗口内的累积和 (Alpha191 SUMAC)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "signed_power",
    "sum_if",
    "cumsum",
    "highday",
    "lowday",
    "sequence",
    "tr",
    "sumac",
]


def signed_power(x: pd.DataFrame, n: float) -> pd.DataFrame:
    """带符号幂: sign(x) * |x|^n。

    对应 Alpha191 的 SIGNED_POWER。
    负数次幂在 |x|=0 处返回 NaN。

    Args:
        x: 输入面板
        n: 指数

    Returns:
        带符号幂面板
    """
    return np.sign(x) * (np.abs(x) ** n)


def sum_if(
    x: pd.DataFrame, cond: pd.DataFrame, n: int
) -> pd.DataFrame:
    """条件滚动求和: 窗口 n 内 cond 为真 (cond>0) 时 x 的求和。

    对应 Alpha191 的 SUMIF / Alpha101 的 sum_if。

    Args:
        x: 输入面板
        cond: 条件面板 (cond>0 视为真，与 x 对齐)
        n: 滚动窗口

    Returns:
        条件求和面板
    """
    cond = cond.reindex_like(x)
    masked = x.where(cond > 0, 0.0)
    return masked.rolling(n).sum()


def cumsum(x: pd.DataFrame) -> pd.DataFrame:
    """沿时间轴累积求和。

    对应 Alpha191 的 CUMSUM / Alpha101 的 ts_cumsum。

    Args:
        x: 输入面板

    Returns:
        累积和面板
    """
    return x.cumsum()


def highday(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期最大值出现距今天数 (0=今天, n-1=最远)。

    对应 Alpha191 的 HIGHDAY。
    窗口内最大值出现在最近第 k 期 (0 基), 返回 k。

    Args:
        x: 输入面板
        n: 滚动窗口

    Returns:
        距今天数面板
    """
    return x.rolling(n).apply(lambda s: n - 1 - np.argmax(s), raw=True)


def lowday(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期最小值出现距今天数 (0=今天, n-1=最远)。

    对应 Alpha191 的 LOWDAY。

    Args:
        x: 输入面板
        n: 滚动窗口

    Returns:
        距今天数面板
    """
    return x.rolling(n).apply(lambda s: n - 1 - np.argmin(s), raw=True)


def sequence(n: int) -> np.ndarray:
    """生成序列 [1, 2, ..., n]。

    对应 Alpha191 的 SEQUENCE(n)。
    用于因子公式中构造权重或下标序列。

    Args:
        n: 序列长度

    Returns:
        1 到 n 的一维数组
    """
    if n <= 0:
        raise ValueError(f"n 必须 > 0, 实际: {n}")
    return np.arange(1, n + 1, dtype=float)


def tr(
    high: pd.DataFrame,
    low: pd.DataFrame,
    prev_close: pd.DataFrame,
) -> pd.DataFrame:
    """真实波幅 (True Range)。

    定义: TR = MAX(H-L, |H-prevC|, |L-prevC|)
    其中 prevC 为前一日收盘价。

    用于 Alpha191 #137/#161/#175 等 ATR 类因子。

    Args:
        high: 当日最高价面板
        low: 当日最低价面板
        prev_close: 前一日收盘价面板 (通常为 delay(close, 1))

    Returns:
        真实波幅面板，首期为 NaN (无前一日收盘价)
    """
    high = high.reindex_like(low)
    prev_close = prev_close.reindex_like(low)
    hl = (high - low).abs()
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    # 逐元素取最大值 (NaN 传播: 任一为 NaN 则结果为 NaN)
    stacked = np.maximum.reduce([hl.values, hc.values, lc.values])
    return pd.DataFrame(stacked, index=low.index, columns=low.columns)


def sumac(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """滚动窗口内累积和 (Alpha191 SUMAC)。

    定义: 在窗口 n 内，逐日累积求和。
    实现: 等价于 cumsum 在 n 期窗口内的滚动视图，
    但 Alpha191 文档中 SUMAC 通常指"滚动累积和"，
    即 rolling(n) 内 cumsum 的最后值。

    本实现: 返回窗口 n 内的累积和序列 (最后一期值)，
    与 cumsum(x) 在 n 期窗口末值一致:
        sumac(x, n)[t] = sum(x[t-n+1..t])

    注意: 这与 ts_sum(x, n) 等价。
    Alpha191 中 SUMAC 用于累积偏离，等价于窗口内求和。

    Args:
        x: 输入面板
        n: 窗口

    Returns:
        累积和面板
    """
    return x.rolling(n).sum()
