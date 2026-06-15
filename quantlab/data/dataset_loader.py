"""
DataLoader — 高层数据集加载器（V4.0 Application Layer）

职责：
  - dataset 字符串 → Dict[symbol, DataFrame]
  - 与 Service 层对接（BacktestService.run_backtest 不直接读 CSV）
  - 默认支持 CSVMultiSource，多文件按 symbol 组织

data_dir 默认 ./data，每个 symbol 一个 CSV

用法：
    loader = DataLoader(data_dir="data")
    data = loader.load(dataset="default", symbols=["AAPL","MSFT"])
    → {
        "AAPL": DataFrame,
        "MSFT": DataFrame,
      }
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Dict, List, Optional

import pandas as pd

from .datasource import CSVMultiSource, DataSource


logger = logging.getLogger("quantlab.dataset_loader")


class DataLoader:
    """
    数据集加载器

    概念：
      dataset    数据集名（决定子目录；空则用 data_dir 本身）
      symbols    标的列表；空 → 自动扫描目录下所有 CSV

    接口：
      load(dataset, symbols=None)        → Dict[symbol, DataFrame]
      list_datasets()                    → List[str]
      list_symbols(dataset="default")    → List[str]
    """

    def __init__(
        self,
        data_dir: str = "data",
        pattern: str = "{symbol}.csv",
    ) -> None:
        self.data_dir = data_dir
        self.pattern = pattern
        self._lock = threading.RLock()
        self._source_cache: Dict[str, DataSource] = {}

    # ---------------------------------------------------------
    # 路径
    # ---------------------------------------------------------
    def _resolve_dir(self, dataset: str) -> str:
        if not dataset or dataset == "default":
            return self.data_dir
        return os.path.join(self.data_dir, dataset)

    # ---------------------------------------------------------
    # 列表
    # ---------------------------------------------------------
    def list_datasets(self) -> List[str]:
        """
        列出 data_dir 下所有"子目录 + 自己"作为数据集候选
        """
        if not os.path.isdir(self.data_dir):
            return []
        out = ["default"]
        try:
            for name in os.listdir(self.data_dir):
                p = os.path.join(self.data_dir, name)
                if os.path.isdir(p):
                    out.append(name)
        except Exception:
            pass
        return out

    def list_symbols(self, dataset: str = "default") -> List[str]:
        d = self._resolve_dir(dataset)
        if not os.path.isdir(d):
            return []
        out: List[str] = []
        try:
            for fname in os.listdir(d):
                if fname.lower().endswith(".csv"):
                    sym = os.path.splitext(fname)[0]
                    out.append(sym)
        except Exception:
            return []
        out.sort()
        return out

    # ---------------------------------------------------------
    # 加载
    # ---------------------------------------------------------
    def load(
        self,
        dataset: str = "default",
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        加载数据集

        symbols 为空 → 自动取数据集目录下所有 CSV
        start / end   → 时间过滤（index 必须是 datetime-like）
        """
        directory = self._resolve_dir(dataset)

        if not os.path.isdir(directory):
            raise FileNotFoundError(
                f"dataset directory not found: {directory}"
            )

        if not symbols:
            symbols = self.list_symbols(dataset)
            if not symbols:
                raise FileNotFoundError(
                    f"no CSV files in dataset directory: {directory}"
                )

        with self._lock:
            cache_key = f"{directory}::{self.pattern}"
            source = self._source_cache.get(cache_key)
            if source is None:
                source = CSVMultiSource(
                    directory=directory,
                    symbols=symbols,
                    pattern=self.pattern,
                )
                self._source_cache[cache_key] = source
            else:
                # 替换 symbols（CSVMultiSource 缓存了 list）
                source.symbols = list(symbols)

        data = source.load()

        # 时间过滤
        if start or end:
            data = {
                sym: _filter_time(df, start, end)
                for sym, df in data.items()
            }

        # 丢掉空 df
        data = {sym: df for sym, df in data.items() if len(df) > 0}
        if not data:
            raise ValueError(
                f"dataset {dataset!r} has no data after filtering "
                f"(start={start}, end={end})"
            )

        return data

    # ---------------------------------------------------------
    # 元信息
    # ---------------------------------------------------------
    def info(self, dataset: str = "default") -> Dict[str, any]:
        d = self._resolve_dir(dataset)
        return {
            "dataset": dataset,
            "directory": d,
            "exists": os.path.isdir(d),
            "symbols": self.list_symbols(dataset),
        }


def _filter_time(
    df: pd.DataFrame,
    start: Optional[str],
    end: Optional[str],
) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return df
    try:
        if start:
            df = df[df.index >= pd.to_datetime(start)]
        if end:
            df = df[df.index <= pd.to_datetime(end)]
        return df
    except Exception:
        return df


# -------------------------------------------------------------
# 全局单例
# -------------------------------------------------------------
_default: Optional[DataLoader] = None
_default_lock = threading.Lock()


def get_data_loader(
    data_dir: Optional[str] = None,
) -> DataLoader:
    """获取（或创建）全局 DataLoader"""
    global _default
    with _default_lock:
        if _default is None:
            _default = DataLoader(
                data_dir=data_dir or "data"
            )
        return _default


def set_data_loader(loader: DataLoader) -> None:
    """替换全局 DataLoader（用于测试）"""
    global _default
    with _default_lock:
        _default = loader
