"""
Signal ABC — V4.6 Signal 层基类

三级模型：Factor → Signal → Strategy

Signal 的职责：
  把因子值（连续值）转换为信号（离散值 ∈ {-1, 0, 1}）

  -1 = 做空
   0 = 空仓
   1 = 做多

与旧 signals/ 的关系：
  - signals/ 是 SignalStrategy (ABC)，直接输出 DataFrame
  - signal/ 是 Signal (ABC)，接收因子值输出 Series
  - 两者共存，新代码推荐用 signal/
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

import pandas as pd


class Signal(ABC):
    """
    信号基类

    子类必须实现：
      - name: 信号唯一标识
      - transform(series): 因子值 → 信号值

    输入: pd.Series (因子值，连续)
    输出: pd.Series (信号值，∈ {-1, 0, 1})
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def description(self) -> str:
        return ""

    @abstractmethod
    def transform(self, series: pd.Series) -> pd.Series:
        """
        因子值 → 信号值

        输入: 因子值 Series (连续值)
        输出: 信号值 Series (∈ {-1, 0, 1})
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"


class MultiFactorSignal(Signal):
    """
    多因子信号：组合多个因子值生成信号

    用法:
        sig = MultiFactorSignal(
            "combo",
            lambda factors: (factors["RSI14"] < 30).astype(int)
                            - (factors["RSI14"] > 70).astype(int),
            dependencies=["RSI14"],
        )
    """

    def __init__(
        self,
        signal_name: str,
        fn,                              # Callable[Dict[str, Series]] -> Series
        dependencies: Optional[List[str]] = None,
        description: str = "",
    ) -> None:
        self._name = signal_name
        self._fn = fn
        self._dependencies = dependencies or []
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def dependencies(self) -> List[str]:
        return self._dependencies

    def transform(self, series: pd.Series) -> pd.Series:
        raise NotImplementedError(
            "MultiFactorSignal.transform(series) 不可直接调用。"
            "请使用 SignalEngine.transform_multi()。"
        )

    def transform_multi(self, factor_values: Dict[str, pd.Series]) -> pd.Series:
        deps = {k: v for k, v in factor_values.items() if k in self._dependencies}
        return self._fn(deps)
