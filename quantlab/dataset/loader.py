"""
V4.3 Dataset Registry — Loader

数据加载器抽象层。
前端不需要知道数据是 CSV 还是 Parquet 还是 DuckDB，
只要调 loader.load() 就行。

当前实现：
  - CSVLoader
  - ParquetLoader

未来扩展：
  - DuckDBLoader
  - ClickHouseLoader
  - PostgresLoader
  - APILoader（Wind / Tushare / JoinQuant）
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd


class BaseLoader(ABC):
    """
    数据加载器基类

    子类只需实现 load() 方法。
    """

    @abstractmethod
    def load(
        self,
        path: str,
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        加载数据

        返回 Dict[symbol, DataFrame]

        参数：
          path     数据路径（文件或目录）
          symbols  标的列表（None=全部）
          start    开始时间
          end      结束时间
        """
        ...

    @abstractmethod
    def list_symbols(self, path: str) -> List[str]:
        """列出路径下所有可用标的"""
        ...

    @abstractmethod
    def detect_schema(self, path: str) -> Dict[str, Any]:
        """探测数据 schema（列名、类型等）"""
        ...


class CSVLoader(BaseLoader):
    """
    CSV 加载器

    支持两种模式：
      1. 单文件：path 指向一个 CSV（单标的）
      2. 多文件：path 指向目录，每个 CSV 是一个标的
    """

    def load(
        self,
        path: str,
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        if os.path.isfile(path):
            # 单文件模式
            symbol = os.path.splitext(os.path.basename(path))[0]
            df = pd.read_csv(path, parse_dates=True, index_col=0)
            df = self._filter_time(df, start, end)
            return {symbol: df}

        # 目录模式
        result = {}
        available = self.list_symbols(path)
        target = symbols if symbols else available

        for sym in target:
            if sym not in available:
                continue
            fpath = os.path.join(path, f"{sym}.csv")
            if os.path.isfile(fpath):
                df = pd.read_csv(fpath, parse_dates=True, index_col=0)
                df = self._filter_time(df, start, end)
                result[sym] = df

        return result

    def list_symbols(self, path: str) -> List[str]:
        if os.path.isfile(path):
            symbol = os.path.splitext(os.path.basename(path))[0]
            return [symbol]

        if not os.path.isdir(path):
            return []

        return [
            os.path.splitext(f)[0]
            for f in os.listdir(path)
            if f.endswith(".csv")
        ]

    def detect_schema(self, path: str) -> Dict[str, Any]:
        sample_path = path
        if os.path.isdir(path):
            csvs = [f for f in os.listdir(path) if f.endswith(".csv")]
            if not csvs:
                return {"columns": []}
            sample_path = os.path.join(path, csvs[0])

        df = pd.read_csv(sample_path, nrows=5)
        return {
            "columns": list(df.columns),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        }

    @staticmethod
    def _filter_time(
        df: pd.DataFrame,
        start: Optional[str],
        end: Optional[str],
    ) -> pd.DataFrame:
        if start:
            df = df[df.index >= pd.Timestamp(start)]
        if end:
            df = df[df.index <= pd.Timestamp(end)]
        return df


class ParquetLoader(BaseLoader):
    """
    Parquet 加载器

    推荐格式：比 CSV 快 5-10x，体积小 3-5x。
    Tick / 多资产 / 多因子场景必须用 Parquet。
    """

    def load(
        self,
        path: str,
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        if os.path.isfile(path):
            # 单文件（可能含多标的）
            df = pd.read_parquet(path)
            return self._split_by_symbol(df, symbols, start, end)

        # 目录模式：每个 parquet 是一个标的
        result = {}
        available = self.list_symbols(path)
        target = symbols if symbols else available

        for sym in target:
            if sym not in available:
                continue
            fpath = os.path.join(path, f"{sym}.parquet")
            if os.path.isfile(fpath):
                df = pd.read_parquet(fpath)
                df = self._ensure_datetime_index(df)
                df = CSVLoader._filter_time(df, start, end)
                result[sym] = df

        return result

    def list_symbols(self, path: str) -> List[str]:
        if os.path.isfile(path):
            return ["__multi__"]

        if not os.path.isdir(path):
            return []

        return [
            os.path.splitext(f)[0]
            for f in os.listdir(path)
            if f.endswith(".parquet")
        ]

    def detect_schema(self, path: str) -> Dict[str, Any]:
        sample_path = path
        if os.path.isdir(path):
            pqs = [f for f in os.listdir(path) if f.endswith(".parquet")]
            if not pqs:
                return {"columns": []}
            sample_path = os.path.join(path, pqs[0])

        df = pd.read_parquet(sample_path)
        return {
            "columns": list(df.columns),
            "dtypes": {col: str(dt) for col, dt in df.dtypes.items()},
        }

    @staticmethod
    def _split_by_symbol(
        df: pd.DataFrame,
        symbols: Optional[List[str]],
        start: Optional[str],
        end: Optional[str],
    ) -> Dict[str, pd.DataFrame]:
        """如果 parquet 含 symbol 列，按 symbol 拆分"""
        if "symbol" in df.columns:
            result = {}
            for sym, group in df.groupby("symbol"):
                if symbols and sym not in symbols:
                    continue
                group = group.drop(columns=["symbol"])
                group = ParquetLoader._ensure_datetime_index(group)
                group = CSVLoader._filter_time(group, start, end)
                result[sym] = group
            return result
        else:
            df = ParquetLoader._ensure_datetime_index(df)
            df = CSVLoader._filter_time(df, start, end)
            return {"__default__": df}

    @staticmethod
    def _ensure_datetime_index(df: pd.DataFrame) -> pd.DataFrame:
        """确保 index 是 DatetimeIndex"""
        if not isinstance(df.index, pd.DatetimeIndex):
            # 尝试把第一列当时间
            time_cols = [
                c for c in df.columns
                if "time" in c.lower() or "date" in c.lower()
            ]
            if time_cols:
                df[time_cols[0]] = pd.to_datetime(df[time_cols[0]])
                df = df.set_index(time_cols[0])
        return df


# ---- Loader 工厂 ----

_LOADERS: Dict[str, BaseLoader] = {
    "csv": CSVLoader(),
    "parquet": ParquetLoader(),
}


def get_loader(format: str) -> BaseLoader:
    """按格式获取 loader"""
    loader = _LOADERS.get(format)
    if loader is None:
        raise ValueError(
            f"Unknown storage format '{format}', "
            f"available: {list(_LOADERS.keys())}"
        )
    return loader
