"""
信号策略基类 (SignalStrategy)
============================

策略只产出信号 DataFrame(date × symbol)，不关心:
    - 仓位怎么算
    - 订单怎么下
    - 用 Bar/Tick/VectorBT 哪个引擎
    - 滑点 / 佣金多少

约束 (遵循 STRATEGY_DEV_GUIDE):
    - 必须继承本基类并实现 signal()
    - __init__ 参数必须可被 int/str 序列化 (支持子进程并行)
    - signal() 应为纯函数，依赖 ctx 数据，不修改外部状态

信号约定:
    - 返回 pd.DataFrame (index=date, columns=symbol)
    - 连续因子值: 由 PortfolioConstructor 截面排名择股
    - 二值信号 (0/1): 直接表示多空
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["SignalStrategy"]


class SignalStrategy(ABC):
    """信号策略抽象基类。

    子类必须实现 `signal(ctx) -> pd.DataFrame`。
    """

    @abstractmethod
    def signal(self, ctx: FactorContext) -> pd.DataFrame:
        """产出信号面板。

        Args:
            ctx: 因子数据上下文 (OHLCV/VWAP/AMOUNT 等)

        Returns:
            信号 DataFrame (index=date, columns=symbol)
        """
        ...

    # ------------------------------------------------------------------
    # 便于序列化与注册
    # ------------------------------------------------------------------
    def params(self) -> dict:
        """返回可序列化的参数字典 (用于并行/注册)。

        默认读取 __init__ 的关键字参数；子类可覆盖。
        """
        return {
            k: v for k, v in vars(self).items()
            if isinstance(v, (int, float, bool, str, list, dict, tuple, type(None)))
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.params()})"
