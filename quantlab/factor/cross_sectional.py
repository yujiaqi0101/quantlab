"""
Cross-Sectional Factors — V4.6 横截面因子

职责：
  - 跨 symbol 的因子操作
  - rank / zscore / quantile / demean
  - 输入: DataFrame(index=时间, columns=symbols)
  - 输出: DataFrame(同结构)

注意：横截面因子不在 Factor ABC 里实现（Factor.compute 是 per-symbol 的），
而是在 FactorEngine 层面做跨 symbol 操作。
这里提供的是可注册的横截面因子包装。
"""

from __future__ import annotations

import pandas as pd

from .base import Factor
from . import operators as ops


class CrossSectionalRankFactor(Factor):
    """
    横截面排名因子

    对某个基础因子做横截面 rank
    注意：compute(df) 只能做单 symbol 的时序 rank，
    真正的横截面 rank 需要在 FactorEngine.compute_all 后用 ops.rank()
    """

    def __init__(self, base_factor_name: str = "MOM20"):
        self.base_factor_name = base_factor_name

    @property
    def name(self) -> str:
        return f"CS_RANK_{self.base_factor_name}"

    @property
    def category(self) -> str:
        return "cross_sectional"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        # 单 symbol fallback: 时序 rank
        # 真正的横截面 rank 用 ops.rank() 在 DataFrame 上做
        raise NotImplementedError(
            f"横截面因子 {self.name} 不能在单 symbol 上 compute。"
            "请用 FactorEngine.compute_all() + ops.rank() 代替。"
        )


class CrossSectionalZScoreFactor(Factor):
    def __init__(self, base_factor_name: str = "MOM20"):
        self.base_factor_name = base_factor_name

    @property
    def name(self) -> str:
        return f"CS_ZSCORE_{self.base_factor_name}"

    @property
    def category(self) -> str:
        return "cross_sectional"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        raise NotImplementedError(
            f"横截面因子 {self.name} 不能在单 symbol 上 compute。"
            "请用 FactorEngine.compute_all() + ops.zscore() 代替。"
        )
