"""
Factor ABC — V4.6 Factor Platform 基类

三级模型：Factor → Signal → Strategy

Factor.compute(df) → pd.Series  (per-symbol 时序因子值)
Signal.transform(factor_values) → pd.Series  (值域 {-1, 0, 1})
Strategy 组合多个 Signal → 最终交易决策

与旧 factors/ 的关系：
  - factors/ 是函数式接口: fn(ctx, symbol, **params) → Series
  - factor/ 是类式接口: Factor.compute(df) → Series
  - 两者共存，新代码推荐用 factor/
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd


class Factor(ABC):
    """
    因子基类

    子类必须实现：
      - name: 因子唯一标识
      - compute(df): 计算因子值

    df 约定：单 symbol 的 OHLCV DataFrame
    返回约定：pd.Series, index 与 df 相同
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """因子唯一名称，如 'RSI14' / 'MOM20' / 'MA20'"""
        pass

    @property
    def category(self) -> str:
        """因子分类: 'technical' / 'momentum' / 'volatility' / 'cross_sectional' / 'fundamental'"""
        return "technical"

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """
        计算因子值

        参数:
            df: 单 symbol 的 OHLCV DataFrame (columns: open/high/low/close/volume)

        返回:
            pd.Series, index 与 df 相同
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class CompositeFactor(Factor):
    """
    组合因子：由算子组合多个因子

    例如: RSI14 - MOM20, MA5 / MA20, rank(RSI14) + zscore(MOM20)

    用法:
        f = CompositeFactor("RSI_MOM", lambda dfs: dfs["RSI14"] - dfs["MOM20"],
                             dependencies=["RSI14", "MOM20"])
    """

    def __init__(
        self,
        factor_name: str,
        fn,                           # Callable[Dict[str, Series]] -> Series
        dependencies: Optional[List[str]] = None,
        category: str = "composite",
        description: str = "",
    ) -> None:
        self._name = factor_name
        self._fn = fn
        self._dependencies = dependencies or []
        self._category = category
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    @property
    def description(self) -> str:
        return self._description

    @property
    def dependencies(self) -> List[str]:
        return self._dependencies

    def compute(self, df: pd.DataFrame) -> pd.Series:
        # CompositeFactor 不直接 compute(df)
        # 需要通过 FactorEngine 先算 dependencies 再组合
        raise NotImplementedError(
            "CompositeFactor.compute(df) 不可直接调用。"
            "请使用 FactorEngine.compute() 或手动传入依赖因子值。"
        )

    def combine(self, factor_values: Dict[str, pd.Series]) -> pd.Series:
        """组合依赖因子的值"""
        deps = {k: v for k, v in factor_values.items() if k in self._dependencies}
        return self._fn(deps)
