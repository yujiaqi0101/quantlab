"""
Alpha191 #10 — 下跌波动率与价格排名
========================================

公式:
    RANK(MAX(((RET < 0) ? STD(RET, 20) : CLOSE)^2, 5))

公式解释:
    当收益率小于0时取20日收益率标准差的平方，
    否则取收盘价的平方，再取5日最大值后进行截面排名。

分类:
    波动率 (volatility)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - RET 日收益率（由 CLOSE 计算）

算子依赖:
    - ts_std (滚动标准差)
    - ts_max (滚动最大值)
    - rank (截面排名)

背后逻辑:
    该因子在下跌时关注波动率（风险），
    上涨时关注价格水平。
    取5日最大值捕捉极端状态，
    截面排名后作为选股信号。
    反向意味着偏好低风险低价格的股票。

适用场景:
    风险控制型策略，偏好波动可控的标的。

变种与优化:
    - 可调整条件判断逻辑和窗口期
    - 使用不同的波动率度量
    - 加入成交量确认

注意事项:
    - 条件判断导致因子值含义不一致
    - 波动率与价格量纲不同，需做标准化处理
    - 前 23 期返回 NaN (ts_std 20 + ts_max 5 - 2)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_max, ts_std

__all__ = ["alpha_010"]

DIRECTION = -1
DEFAULT_STD_PERIOD = 20
DEFAULT_MAX_PERIOD = 5


def alpha_010(
    ctx: FactorContext,
    std_period: int = DEFAULT_STD_PERIOD,
    max_period: int = DEFAULT_MAX_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #10: 下跌波动率与价格排名。

    公式: RANK(MAX(((RET < 0) ? STD(RET, std_period) : CLOSE)^2, max_period))

    Args:
        ctx: 因子数据上下文
        std_period: 标准差窗口期 (默认 20)
        max_period: 最大值窗口期 (默认 5)

    Returns:
        波动率与价格排名因子面板 (date × symbol)
    """
    ret = ctx.get_returns()
    ret_std = ts_std(ret, std_period)
    close = ctx.close
    # 条件选择: RET < 0 时取 STD(RET), 否则取 CLOSE
    selected = ret_std.where(ret < 0, close)
    squared = selected ** 2
    return rank(ts_max(squared, max_period))
