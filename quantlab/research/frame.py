"""
ResearchFrame — 统一数据契约

Panel 为默认，(datetime, symbol) MultiIndex。可退化为单标的时序 / 单日横截面。

所有 ResearchNode 的输入输出均为 ResearchFrame，确保 Node 间数据契约一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class ResearchFrame:
    """
    统一数据标准 — Node 间唯一数据契约

    Attributes:
        data:       DataFrame, MultiIndex (datetime, symbol)
        columns_meta: 每列的元信息 (role/dtype/unit)
        name:       可选名称 (如 "close", "rsi14")
    """
    data: pd.DataFrame
    name: str = ""
    columns_meta: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError(f"ResearchFrame.data must be DataFrame, got {type(self.data)}")
        self._ensure_multiindex()

    # ------------------------------------------------------------------ #
    # 构造工厂
    # ------------------------------------------------------------------ #
    @classmethod
    def from_ohlcv(cls, df: pd.DataFrame, name: str = "ohlcv") -> "ResearchFrame":
        """从 OHLCV DataFrame 构造。

        支持两种输入:
          1) 已是 (datetime, symbol) MultiIndex
          2) 单级 DatetimeIndex (自动补 symbol='default')
        """
        if isinstance(df.index, pd.MultiIndex):
            data = df.copy()
        elif isinstance(df.index, pd.DatetimeIndex):
            data = df.copy()
            data.index.name = "datetime"
            data.insert(0, "symbol", "default")
            data.set_index("symbol", append=True, inplace=True)
            data = data.reorder_levels(["datetime", "symbol"])
        else:
            raise ValueError(
                "from_ohlcv expects DatetimeIndex or (datetime, symbol) MultiIndex, "
                f"got {type(df.index)}"
            )
        data.index.names = ["datetime", "symbol"]
        return cls(data=data, name=name)

    @classmethod
    def from_single_symbol(
        cls, df: pd.DataFrame, symbol: str, name: str = ""
    ) -> "ResearchFrame":
        """从单标的时序 DataFrame 构造 (DatetimeIndex → 补 symbol 列)。"""
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("from_single_symbol expects DatetimeIndex")
        data = df.copy()
        data.index.name = "datetime"
        data.insert(0, "symbol", symbol)
        data.set_index("symbol", append=True, inplace=True)
        data = data.reorder_levels(["datetime", "symbol"])
        data.index.names = ["datetime", "symbol"]
        return cls(data=data, name=name)

    @classmethod
    def from_panel(
        cls, df: pd.DataFrame, name: str = ""
    ) -> "ResearchFrame":
        """从已具备 (datetime, symbol) MultiIndex 的 DataFrame 构造。"""
        if not isinstance(df.index, pd.MultiIndex):
            raise ValueError("from_panel expects (datetime, symbol) MultiIndex")
        data = df.copy()
        data.index.names = ["datetime", "symbol"]
        return cls(data=data, name=name)

    # ------------------------------------------------------------------ #
    # 退化模式
    # ------------------------------------------------------------------ #
    def as_time_series(self, symbol: str) -> pd.DataFrame:
        """退化为单标的时序 (DatetimeIndex → DataFrame)。"""
        try:
            sub = self.data.xs(symbol, level="symbol")
        except KeyError:
            raise KeyError(f"symbol '{symbol}' not in frame")
        return sub

    def as_cross_section(self, dt) -> pd.DataFrame:
        """退化为单日横截面 (symbol → DataFrame)。"""
        try:
            sub = self.data.xs(dt, level="datetime")
        except KeyError:
            raise KeyError(f"datetime '{dt}' not in frame")
        return sub

    # ------------------------------------------------------------------ #
    # 元信息
    # ------------------------------------------------------------------ #
    @property
    def symbols(self) -> List[str]:
        idx = self.data.index.get_level_values("symbol")
        return list(idx.unique())

    @property
    def datetimes(self) -> pd.DatetimeIndex:
        return self.data.index.get_level_values("datetime").unique()

    @property
    def columns(self) -> List[str]:
        return list(self.data.columns)

    @property
    def shape(self):
        return self.data.shape

    def __len__(self) -> int:
        return len(self.data)

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    def _ensure_multiindex(self) -> None:
        idx = self.data.index
        if not isinstance(idx, pd.MultiIndex):
            raise ValueError(
                "ResearchFrame requires (datetime, symbol) MultiIndex, "
                f"got {type(idx)}. Use from_ohlcv / from_single_symbol / from_panel."
            )
        names = list(idx.names)
        if len(names) != 2:
            raise ValueError(f"MultiIndex must have 2 levels, got {len(names)}: {names}")
        # 标准化 level 名
        if names[0] != "datetime" or names[1] != "symbol":
            # 容错：若只有一层名为 datetime/symbol 的，补齐
            self.data.index.names = ["datetime", "symbol"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "shape": list(self.shape),
            "symbols": self.symbols,
            "columns": self.columns,
            "columns_meta": self.columns_meta,
        }

    def __repr__(self) -> str:
        return (
            f"ResearchFrame(name={self.name!r}, shape={self.shape}, "
            f"symbols={len(self.symbols)}, cols={self.columns})"
        )
