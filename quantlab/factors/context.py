"""
因子数据上下文 (FactorContext)
============================

封装因子计算所需的全部市场数据，避免因子函数的长参数列表。
所有因子函数签名统一为:

    def alpha_XXX(ctx: FactorContext) -> pd.DataFrame

数据字段约定:
    open / high / low / close / volume / vwap / amount : pd.DataFrame
        index = 日期 (DatetimeIndex)
        columns = 标的代码 (symbol)
        所有字段形状一致、索引对齐

构造方式:
    1. 从 Dict[symbol, DataFrame] 构造 (推荐，兼容回测引擎数据格式)
    2. 直接传入已对齐的 DataFrame 字典

约束:
    - 市场数据必须是干净的、可信任的 (遵循项目规则)
    - 使用后复权价格
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

import pandas as pd

__all__ = ["FactorContext"]


@dataclass
class FactorContext:
    """因子计算数据上下文。

    封装 OHLCV / VWAP / AMOUNT 等日频面板数据，供因子函数读取。

    Attributes:
        open: 开盘价面板 (date × symbol)
        high: 最高价面板
        low: 最低价面板
        close: 收盘价面板
        volume: 成交量面板
        vwap: 成交量加权均价面板 (可选，缺失时由 amount/volume 近似)
        amount: 成交额面板 (可选)
        benchmark_close: 基准指数收盘价 (Series, 可选)
        benchmark_open: 基准指数开盘价 (Series, 可选)
    """

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame
    vwap: Optional[pd.DataFrame] = None
    amount: Optional[pd.DataFrame] = None
    benchmark_close: Optional[pd.Series] = None
    benchmark_open: Optional[pd.Series] = None

    # ------------------------------------------------------------------
    # 构造方法
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(
        cls,
        data: Dict[str, pd.DataFrame],
        vwap_col: str = "vwap",
        amount_col: str = "amount",
        benchmark_close: Optional[pd.Series] = None,
        benchmark_open: Optional[pd.Series] = None,
    ) -> "FactorContext":
        """从 {symbol: DataFrame(date × OHLCV)} 字典构造对齐的面板数据。

        Args:
            data: {symbol: df}，df 至少包含 open/high/low/close/volume 列
            vwap_col: df 中 vwap 列名 (可选)
            amount_col: df 中 amount 列名 (可选)
            benchmark_close: 基准指数收盘价序列 (可选)
            benchmark_open: 基准指数开盘价序列 (可选)

        Returns:
            FactorContext 实例
        """
        if not data:
            raise ValueError("data 字典不能为空")

        # 校验并提取每个标的的字段
        required = ["open", "high", "low", "close", "volume"]
        panels: Dict[str, Dict[str, pd.Series]] = {
            col: {} for col in required
        }
        vwap_panels: Dict[str, pd.Series] = {}
        amount_panels: Dict[str, pd.Series] = {}

        for sym, df in data.items():
            for col in required:
                if col not in df.columns:
                    raise KeyError(
                        f"标的 {sym} 缺少必需列: {col}，"
                        f"现有列: {list(df.columns)}"
                    )
                panels[col][sym] = df[col]
            if vwap_col in df.columns:
                vwap_panels[sym] = df[vwap_col]
            if amount_col in df.columns:
                amount_panels[sym] = df[amount_col]

        # 构造对齐的面板 DataFrame
        def _to_frame(d: Dict[str, pd.Series]) -> pd.DataFrame:
            return pd.DataFrame(d)

        ctx = cls(
            open=_to_frame(panels["open"]),
            high=_to_frame(panels["high"]),
            low=_to_frame(panels["low"]),
            close=_to_frame(panels["close"]),
            volume=_to_frame(panels["volume"]),
            vwap=_to_frame(vwap_panels) if vwap_panels else None,
            amount=_to_frame(amount_panels) if amount_panels else None,
            benchmark_close=benchmark_close,
            benchmark_open=benchmark_open,
        )
        ctx._align()
        return ctx

    # ------------------------------------------------------------------
    # 对齐与校验
    # ------------------------------------------------------------------
    def _align(self) -> None:
        """确保所有面板的 index / columns 对齐。"""
        ref = self.close
        for name in ["open", "high", "low", "volume"]:
            frame = getattr(self, name)
            setattr(self, name, frame.reindex_like(ref))
        if self.vwap is not None:
            self.vwap = self.vwap.reindex_like(ref)
        if self.amount is not None:
            self.amount = self.amount.reindex_like(ref)

    # ------------------------------------------------------------------
    # 派生数据
    # ------------------------------------------------------------------
    @property
    def symbols(self) -> list:
        """标的代码列表。"""
        return list(self.close.columns)

    @property
    def dates(self) -> pd.DatetimeIndex:
        """日期索引。"""
        return self.close.index

    def get_vwap(self) -> pd.DataFrame:
        """获取 VWAP 面板，缺失时用 amount/volume 近似。

        Returns:
            VWAP 面板 (date × symbol)
        """
        if self.vwap is not None:
            return self.vwap
        if self.amount is not None:
            # amount / volume 近似 VWAP，volume=0 处理为 NaN
            vol = self.volume.where(self.volume > 0)
            return self.amount / vol
        # 都缺失时用收盘价近似 (精度低，仅兜底)
        return self.close.copy()

    def get_amount(self) -> pd.DataFrame:
        """获取成交额面板，缺失时用 vwap*volume 近似。

        Returns:
            成交额面板 (date × symbol)
        """
        if self.amount is not None:
            return self.amount
        if self.vwap is not None:
            return self.vwap * self.volume
        return self.close * self.volume

    def get_returns(self) -> pd.DataFrame:
        """获取日收益率面板。

        定义: returns = close / delay(close, 1) - 1 (即 pct_change)。

        Returns:
            日收益率面板 (date × symbol)，首期为 NaN
        """
        return self.close.pct_change()

    def get_adv(self, n: int = 20) -> pd.DataFrame:
        """获取 N 日平均成交量面板 (Average Daily Volume)。

        定义: adv_n = ts_mean(volume, n)。
        用于 Alpha101 中 adv20 等成交量均线依赖。

        Args:
            n: 平均窗口期 (默认 20)

        Returns:
            N 日平均成交量面板 (date × symbol)，前 n-1 期为 NaN
        """
        return self.volume.rolling(n, min_periods=n).mean()

    def __repr__(self) -> str:
        n_sym = len(self.symbols)
        n_dates = len(self.dates)
        extra = []
        if self.vwap is not None:
            extra.append("vwap")
        if self.amount is not None:
            extra.append("amount")
        if self.benchmark_close is not None:
            extra.append("benchmark")
        extra_str = f", extra=[{','.join(extra)}]" if extra else ""
        return (
            f"FactorContext(symbols={n_sym}, dates={n_dates}{extra_str})"
        )
