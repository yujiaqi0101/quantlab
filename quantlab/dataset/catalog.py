"""
V4.3 Dataset Registry — Catalog

数据目录：自动扫描 data/ 目录，将 CSV/Parquet 注册到 DatasetRegistry。

推荐数据目录结构：
  data/
    crypto/
      btcusdt/
        1m/
          2025.parquet
    equity/
      us/
        aapl.csv
        msft.csv

当前实现：
  - 扫描 data/ 下所有 CSV 文件
  - 自动推导 dataset_id / symbol / schema
  - 注册到 DatasetRegistry
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import pandas as pd

from .metadata import DatasetMetadata, DatasetSchema, DatasetVersion
from .registry import DatasetRegistry, get_dataset_registry
from .loader import CSVLoader, ParquetLoader


class DataCatalog:
    """
    数据目录

    自动扫描 data/ 目录，注册所有数据集。

    用法：
        catalog = DataCatalog(data_dir="data")
        catalog.scan()  # 扫描并注册
    """

    def __init__(
        self,
        data_dir: str = "data",
        registry: Optional[DatasetRegistry] = None,
    ) -> None:
        self.data_dir = data_dir
        self._registry = registry or get_dataset_registry()
        self._csv_loader = CSVLoader()
        self._parquet_loader = ParquetLoader()

    @property
    def registry(self) -> DatasetRegistry:
        return self._registry

    def scan(self) -> List[DatasetMetadata]:
        """
        扫描 data_dir，注册所有数据集

        返回新注册的数据集列表
        """
        registered = []

        if not os.path.isdir(self.data_dir):
            return registered

        # 1. 扫描顶层 CSV 文件（旧格式：data/AAPL.csv）
        registered.extend(self._scan_top_level_csv())

        # 2. 扫描子目录中的 CSV（data/crypto/btcusdt/1m/*.csv）
        registered.extend(self._scan_nested_csv())

        # 3. 扫描 Parquet 文件
        registered.extend(self._scan_parquet())

        return registered

    def _scan_top_level_csv(self) -> List[DatasetMetadata]:
        """扫描 data/ 顶层的 CSV 文件"""
        registered = []

        for f in os.listdir(self.data_dir):
            if not f.endswith(".csv"):
                continue

            fpath = os.path.join(self.data_dir, f)
            symbol = os.path.splitext(f)[0]

            # 推导元信息
            meta = self._build_metadata_from_csv(
                path=fpath,
                dataset_id=f"default_{symbol.lower()}",
                symbol=symbol,
                name=f"{symbol} Daily",
                frequency="1d",
                asset_type="equity",
                tags=["equity"],
            )

            if meta is not None:
                self._registry.register(meta)
                registered.append(meta)

        return registered

    def _scan_nested_csv(self) -> List[DatasetMetadata]:
        """扫描子目录中的 CSV"""
        registered = []

        for root, dirs, files in os.walk(self.data_dir):
            csvs = [f for f in files if f.endswith(".csv")]
            if not csvs:
                continue

            # 跳过顶层（已由 _scan_top_level_csv 处理）
            if root == self.data_dir:
                continue

            # 从路径推导 dataset_id
            # data/crypto/btcusdt/1m/ → dataset_id = "crypto_btcusdt_1m"
            rel = os.path.relpath(root, self.data_dir)
            parts = rel.replace("\\", "/").split("/")

            # 如果目录下有多个 CSV（多标的）
            if len(csvs) > 1:
                dataset_id = "_".join(parts).lower()
                symbols = [os.path.splitext(f)[0] for f in csvs]
                name = " / ".join(parts) + f" ({len(csvs)} symbols)"

                meta = self._build_metadata_from_dir(
                    directory=root,
                    dataset_id=dataset_id,
                    symbol=",".join(symbols),
                    name=name,
                    frequency=self._guess_frequency(parts),
                    asset_type=self._guess_asset_type(parts),
                    tags=self._guess_tags(parts),
                )

                if meta is not None:
                    self._registry.register(meta)
                    registered.append(meta)
            else:
                # 单文件
                fpath = os.path.join(root, csvs[0])
                symbol = os.path.splitext(csvs[0])[0]
                dataset_id = "_".join(parts + [symbol.lower()]).lower()

                meta = self._build_metadata_from_csv(
                    path=fpath,
                    dataset_id=dataset_id,
                    symbol=symbol,
                    name=f"{' / '.join(parts)} / {symbol}",
                    frequency=self._guess_frequency(parts),
                    asset_type=self._guess_asset_type(parts),
                    tags=self._guess_tags(parts),
                )

                if meta is not None:
                    self._registry.register(meta)
                    registered.append(meta)

        return registered

    def _scan_parquet(self) -> List[DatasetMetadata]:
        """扫描 Parquet 文件"""
        registered = []

        for root, dirs, files in os.walk(self.data_dir):
            pqs = [f for f in files if f.endswith(".parquet")]
            if not pqs:
                continue

            rel = os.path.relpath(root, self.data_dir)
            parts = rel.replace("\\", "/").split("/")

            for pq in pqs:
                fpath = os.path.join(root, pq)
                symbol = os.path.splitext(pq)[0]

                if root == self.data_dir:
                    dataset_id = f"pq_{symbol.lower()}"
                else:
                    dataset_id = "_".join(parts + [symbol.lower()]).lower()

                meta = self._build_metadata_from_parquet(
                    path=fpath,
                    dataset_id=dataset_id,
                    symbol=symbol,
                    name=f"{' / '.join(parts)} / {symbol}" if parts != ["."] else symbol,
                    frequency=self._guess_frequency(parts),
                    asset_type=self._guess_asset_type(parts),
                    tags=self._guess_tags(parts),
                )

                if meta is not None:
                    self._registry.register(meta)
                    registered.append(meta)

        return registered

    # ---------------------------------------------------------
    # 元信息构建
    # ---------------------------------------------------------
    def _build_metadata_from_csv(
        self,
        path: str,
        dataset_id: str,
        symbol: str,
        name: str,
        frequency: str,
        asset_type: str,
        tags: List[str],
    ) -> Optional[DatasetMetadata]:
        """从 CSV 文件构建 DatasetMetadata"""
        try:
            df = pd.read_csv(path, nrows=100)
            schema = DatasetSchema.from_dataframe(df)

            # 完整读取获取行数和时间范围
            full_df = pd.read_csv(path, parse_dates=True, index_col=0)
            rows = len(full_df)
            start_time = str(full_df.index.min()) if len(full_df) > 0 else None
            end_time = str(full_df.index.max()) if len(full_df) > 0 else None

            return DatasetMetadata(
                dataset_id=dataset_id,
                name=name,
                symbol=symbol,
                frequency=frequency,
                asset_type=asset_type,
                start_time=start_time,
                end_time=end_time,
                rows=rows,
                storage_path=path,
                storage_format="csv",
                schema=schema,
                tags=tags,
            )
        except Exception as exc:
            import logging
            logging.getLogger("quantlab.dataset.catalog").warning(
                f"Failed to scan CSV '{path}': {exc}"
            )
            return None

    def _build_metadata_from_dir(
        self,
        directory: str,
        dataset_id: str,
        symbol: str,
        name: str,
        frequency: str,
        asset_type: str,
        tags: List[str],
    ) -> Optional[DatasetMetadata]:
        """从目录构建 DatasetMetadata（多标的）"""
        try:
            csvs = [f for f in os.listdir(directory) if f.endswith(".csv")]
            if not csvs:
                return None

            # 取第一个文件推导 schema
            first_path = os.path.join(directory, csvs[0])
            df = pd.read_csv(first_path, nrows=5)
            schema = DatasetSchema.from_dataframe(df)

            # 统计行数
            total_rows = 0
            start_time = None
            end_time = None
            for f in csvs:
                fpath = os.path.join(directory, f)
                fdf = pd.read_csv(fpath, parse_dates=True, index_col=0)
                total_rows += len(fdf)
                if isinstance(fdf.index, pd.DatetimeIndex) and len(fdf) > 0:
                    s = str(fdf.index.min())
                    e = str(fdf.index.max())
                    if start_time is None or s < start_time:
                        start_time = s
                    if end_time is None or e > end_time:
                        end_time = e

            return DatasetMetadata(
                dataset_id=dataset_id,
                name=name,
                symbol=symbol,
                frequency=frequency,
                asset_type=asset_type,
                start_time=start_time,
                end_time=end_time,
                rows=total_rows,
                storage_path=directory,
                storage_format="csv",
                schema=schema,
                tags=tags,
            )
        except Exception as exc:
            import logging
            logging.getLogger("quantlab.dataset.catalog").warning(
                f"Failed to scan directory '{directory}': {exc}"
            )
            return None

    def _build_metadata_from_parquet(
        self,
        path: str,
        dataset_id: str,
        symbol: str,
        name: str,
        frequency: str,
        asset_type: str,
        tags: List[str],
    ) -> Optional[DatasetMetadata]:
        """从 Parquet 文件构建 DatasetMetadata"""
        try:
            df = pd.read_parquet(path)
            schema = DatasetSchema.from_dataframe(df)
            rows = len(df)

            start_time = None
            end_time = None
            if isinstance(df.index, pd.DatetimeIndex) and rows > 0:
                start_time = str(df.index.min())
                end_time = str(df.index.max())

            return DatasetMetadata(
                dataset_id=dataset_id,
                name=name,
                symbol=symbol,
                frequency=frequency,
                asset_type=asset_type,
                start_time=start_time,
                end_time=end_time,
                rows=rows,
                storage_path=path,
                storage_format="parquet",
                schema=schema,
                tags=tags,
            )
        except Exception as exc:
            import logging
            logging.getLogger("quantlab.dataset.catalog").warning(
                f"Failed to scan Parquet '{path}': {exc}"
            )
            return None

    # ---------------------------------------------------------
    # 路径推导辅助
    # ---------------------------------------------------------
    @staticmethod
    def _guess_frequency(parts: List[str]) -> str:
        """从路径推导频率"""
        freq_map = {
            "tick": "tick",
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h",
            "1d": "1d", "daily": "1d",
            "1w": "1w", "weekly": "1w",
        }
        for p in parts:
            if p.lower() in freq_map:
                return freq_map[p.lower()]
        return "1d"

    @staticmethod
    def _guess_asset_type(parts: List[str]) -> str:
        """从路径推导资产类型"""
        type_map = {
            "crypto": "crypto",
            "equity": "stock",
            "stock": "stock",
            "us": "stock",
            "cn": "stock",
            "future": "future",
            "futures": "future",
            "etf": "etf",
            "index": "index",
            "factor": "factor",
            "forex": "forex",
        }
        for p in parts:
            if p.lower() in type_map:
                return type_map[p.lower()]
        return "other"

    @staticmethod
    def _guess_tags(parts: List[str]) -> List[str]:
        """从路径推导标签"""
        tag_map = {
            "crypto": "crypto",
            "equity": "equity",
            "stock": "equity",
            "future": "future",
            "futures": "future",
            "factor": "factor",
            "fundamental": "fundamental",
            "etf": "etf",
            "index": "index",
            "forex": "forex",
        }
        tags = []
        for p in parts:
            if p.lower() in tag_map:
                tags.append(tag_map[p.lower()])
        return tags if tags else ["other"]
