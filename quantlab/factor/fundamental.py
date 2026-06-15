"""
Fundamental Factors — V4.6 基本面因子 (stub)

当前只有 stub 实现。
未来接入财务数据后，可扩展 PE / PB / ROE / EPS 等因子。
"""

from __future__ import annotations

import pandas as pd

from .base import Factor


class PEFactor(Factor):
    """市盈率 (stub)"""

    @property
    def name(self) -> str:
        return "PE"

    @property
    def category(self) -> str:
        return "fundamental"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "pe" in df.columns:
            return df["pe"]
        # stub: 返回 NaN
        return pd.Series(float("nan"), index=df.index)


class PBFactor(Factor):
    """市净率 (stub)"""

    @property
    def name(self) -> str:
        return "PB"

    @property
    def category(self) -> str:
        return "fundamental"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "pb" in df.columns:
            return df["pb"]
        return pd.Series(float("nan"), index=df.index)


class MarketCapFactor(Factor):
    """市值 (stub)"""

    @property
    def name(self) -> str:
        return "MKT_CAP"

    @property
    def category(self) -> str:
        return "fundamental"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "market_cap" in df.columns:
            return df["market_cap"]
        # fallback: close * volume (不精确，仅做 stub)
        return df["close"] * df["volume"]
