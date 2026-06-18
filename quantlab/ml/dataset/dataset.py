"""
Dataset — 数据集对象

ML Lab 第一部分：训练数据管理

  Dataset
    - dataset_id
    - name
    - symbols
    - start_date / end_date
    - frequency

  DatasetManager
    - 创建 / 查询 / 加载
    - 统计：样本量 / 缺失值 / 字段
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.dataset")


@dataclass
class DatasetStats:
    """数据集统计信息"""
    n_rows: int = 0
    n_cols: int = 0
    n_symbols: int = 0
    n_missing: int = 0
    missing_pct: float = 0.0
    columns: List[str] = field(default_factory=list)
    dtypes: Dict[str, str] = field(default_factory=dict)
    date_range: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "n_symbols": self.n_symbols,
            "n_missing": self.n_missing,
            "missing_pct": round(self.missing_pct, 4),
            "columns": self.columns,
            "dtypes": self.dtypes,
            "date_range": self.date_range,
        }


@dataclass
class Dataset:
    """
    数据集

    用法：
        ds = Dataset(
            name="Crypto_1H",
            symbols=["BTC", "ETH", "SOL"],
            start_date="2020-01-01",
            end_date="2025-01-01",
            frequency="1h",
        )
        ds.set_data(df)
        stats = ds.get_stats()
    """
    dataset_id: str = field(default_factory=lambda: f"DS-{uuid.uuid4().hex[:8]}")
    name: str = ""
    symbols: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    frequency: str = "1d"          # 1m / 5m / 15m / 1h / 4h / 1d
    description: str = ""
    tags: List[str] = field(default_factory=list)
    _data: Optional[pd.DataFrame] = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()

    def set_data(self, df: pd.DataFrame) -> None:
        """设置数据"""
        self._data = df
        if df is not None and len(df) > 0:
            # 自动推断日期范围
            if isinstance(df.index, pd.DatetimeIndex):
                self.start_date = str(df.index.min())
                self.end_date = str(df.index.max())

    def get_data(self) -> Optional[pd.DataFrame]:
        """获取数据"""
        return self._data

    def get_stats(self) -> DatasetStats:
        """获取统计信息"""
        if self._data is None:
            return DatasetStats()

        df = self._data
        n_missing = int(df.isnull().sum().sum())
        total_cells = df.shape[0] * df.shape[1]

        date_range = []
        if isinstance(df.index, pd.DatetimeIndex):
            date_range = [str(df.index.min()), str(df.index.max())]

        return DatasetStats(
            n_rows=df.shape[0],
            n_cols=df.shape[1],
            n_symbols=len(self.symbols),
            n_missing=n_missing,
            missing_pct=n_missing / total_cells if total_cells > 0 else 0,
            columns=list(df.columns),
            dtypes={c: str(df[c].dtype) for c in df.columns},
            date_range=date_range,
        )

    def preview(self, n: int = 10) -> Dict:
        """预览数据"""
        if self._data is None:
            return {"head": [], "tail": [], "describe": {}}
        df = self._data
        return {
            "head": df.head(n).to_dict(orient="records"),
            "tail": df.tail(n).to_dict(orient="records"),
            "describe": df.describe().to_dict() if len(df) > 0 else {},
        }

    def to_dict(self) -> Dict:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "symbols": self.symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency": self.frequency,
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "has_data": self._data is not None,
        }


class DatasetManager:
    """
    数据集管理器

    用法：
        mgr = get_dataset_manager()
        ds = mgr.create_dataset(name="Crypto_1H", symbols=["BTC", "ETH"])
        mgr.load_csv("Crypto_1H", "data/btc_1h.csv")
        stats = mgr.get_stats("Crypto_1H")

    持久化（M2 新增）：
        mgr = DatasetManager(persist=True)        # 开启 SQLite + Parquet 持久化
        mgr.load_from_store()                      # 从 DB 恢复所有 Dataset
        # create / load_csv / remove_dataset 会自动同步到 DB 和 Parquet
    """

    def __init__(self, persist: bool = False) -> None:
        self._datasets: Dict[str, Dataset] = {}
        self._persist = persist
        self._store = None
        self._parquet = None
        if persist:
            from ..storage import get_ml_store, get_parquet_store
            self._store = get_ml_store()
            self._parquet = get_parquet_store()

    def create_dataset(
        self,
        name: str,
        symbols: List[str],
        frequency: str = "1d",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dataset:
        """创建数据集"""
        ds = Dataset(
            name=name,
            symbols=symbols,
            frequency=frequency,
            description=description,
            tags=tags or [],
        )
        self._datasets[ds.dataset_id] = ds
        if self._persist and self._store:
            self._store.save_dataset(ds.to_dict(), has_data=False)
        logger.info(f"Dataset created: {ds.dataset_id} ({name})")
        return ds

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        return self._datasets.get(dataset_id)

    def get_by_name(self, name: str) -> Optional[Dataset]:
        for ds in self._datasets.values():
            if ds.name == name:
                return ds
        return None

    def list_datasets(self) -> List[Dataset]:
        return list(self._datasets.values())

    def remove_dataset(self, dataset_id: str) -> bool:
        if dataset_id in self._datasets:
            self._datasets.pop(dataset_id)
            if self._persist and self._store:
                self._store.delete_dataset(dataset_id)
            if self._parquet:
                self._parquet.delete_dataset_data(dataset_id)
            return True
        return False

    def load_csv(self, dataset_id: str, filepath: str) -> bool:
        """从 CSV 加载数据"""
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        try:
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            ds.set_data(df)
            if self._persist and self._parquet:
                self._parquet.save_dataset_data(dataset_id, df)
                if self._store:
                    self._store.update_dataset_has_data(dataset_id, True)
            logger.info(f"CSV loaded: {filepath} → {ds.dataset_id} ({df.shape})")
            return True
        except Exception as e:
            logger.error(f"CSV load failed: {e}")
            return False

    def load_dataframe(self, dataset_id: str, df: pd.DataFrame) -> bool:
        """从 DataFrame 加载数据"""
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        ds.set_data(df)
        if self._persist and self._parquet:
            self._parquet.save_dataset_data(dataset_id, df)
            if self._store:
                self._store.update_dataset_has_data(dataset_id, True)
        return True

    def get_stats(self, dataset_id: str) -> Optional[DatasetStats]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return ds.get_stats()

    def preview(self, dataset_id: str, n: int = 10) -> Optional[Dict]:
        ds = self._datasets.get(dataset_id)
        if not ds:
            return None
        return ds.preview(n)

    def to_dict(self) -> Dict:
        return {
            "total": len(self._datasets),
            "datasets": [ds.to_dict() for ds in self._datasets.values()],
        }

    # ------------------------------------------------------------------
    # 持久化：从 DB 恢复
    # ------------------------------------------------------------------

    def load_from_store(self) -> int:
        """
        从 SQLite 恢复所有 Dataset 元信息到内存。
        数据 DataFrame 不自动加载（按需调用 load_dataset_data）。
        返回恢复的 Dataset 数量。
        """
        if not self._store:
            return 0
        rows = self._store.list_datasets()
        count = 0
        for row in rows:
            if row["dataset_id"] in self._datasets:
                continue
            ds = Dataset(
                name=row["name"],
                symbols=row["symbols"],
                frequency=row["frequency"],
                description=row["description"],
                tags=row["tags"],
            )
            # 覆盖为 DB 中的 id 和时间戳，保持一致
            ds.dataset_id = row["dataset_id"]
            ds.created_at = row["created_at"]
            ds.start_date = row["start_date"]
            ds.end_date = row["end_date"]
            self._datasets[ds.dataset_id] = ds
            count += 1
        logger.info(f"Loaded {count} datasets from store")
        return count

    def load_dataset_data(self, dataset_id: str) -> bool:
        """从 Parquet 加载 Dataset 数据到内存（按需加载）"""
        if not self._parquet:
            return False
        ds = self._datasets.get(dataset_id)
        if not ds:
            return False
        df = self._parquet.load_dataset_data(dataset_id)
        if df is None:
            return False
        ds.set_data(df)
        return True


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_dataset_manager: Optional[DatasetManager] = None


def get_dataset_manager(persist: bool = True) -> DatasetManager:
    """
    获取 DatasetManager 单例。

    Args:
        persist: 是否开启 SQLite + Parquet 持久化（默认 True）
                 首次创建时会自动从 DB 恢复已有 Dataset 元信息
    """
    global _dataset_manager
    if _dataset_manager is None:
        _dataset_manager = DatasetManager(persist=persist)
        if persist:
            _dataset_manager.load_from_store()
    return _dataset_manager
