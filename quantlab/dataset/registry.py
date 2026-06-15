"""
V4.3 Dataset Registry — Registry

数据集注册中心。
与 StrategyRegistry 对称设计。

核心能力：
  - register(metadata)   注册数据集
  - get(dataset_id)      查询数据集
  - list()               列出所有数据集
  - search()             按标签/类型/频率搜索
  - load(dataset_id)     加载数据
  - validate(dataset_id) 校验数据
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from .metadata import DatasetMetadata, DatasetSchema
from .validator import DatasetValidator
from .loader import get_loader, BaseLoader


logger = logging.getLogger("quantlab.dataset.registry")


class DatasetRegistry:
    """
    数据集注册中心

    用法：
        registry = DatasetRegistry()
        registry.register(metadata)
        meta = registry.get("btcusdt_1m")
        data = registry.load("btcusdt_1m")
    """

    def __init__(self) -> None:
        self._datasets: Dict[str, DatasetMetadata] = {}
        self._validator = DatasetValidator()
        # 缓存：dataset_id → {symbol: DataFrame}
        self._cache: Dict[str, Dict[str, pd.DataFrame]] = {}

    # ---------------------------------------------------------
    # 注册
    # ---------------------------------------------------------
    def register(self, metadata: DatasetMetadata) -> None:
        """
        注册数据集

        如果 dataset_id 已存在，覆盖（更新版本）
        """
        existing = self._datasets.get(metadata.dataset_id)
        if existing is not None:
            logger.info(
                f"dataset '{metadata.dataset_id}' re-registered "
                f"(v{existing.version.version} → v{metadata.version.version})"
            )
        else:
            logger.info(f"dataset registered: {metadata.dataset_id}")

        self._datasets[metadata.dataset_id] = metadata
        # 清除缓存（数据可能已变）
        self._cache.pop(metadata.dataset_id, None)

    def register_from_dataframe(
        self,
        dataset_id: str,
        data: Dict[str, pd.DataFrame],
        *,
        name: str = "",
        symbol: str = "",
        frequency: str = "1d",
        asset_type: str = "other",
        tags: Optional[List[str]] = None,
        storage_format: str = "memory",
    ) -> DatasetMetadata:
        """
        从 DataFrame 字典快速注册数据集

        参数：
          dataset_id     短 ID
          data           {symbol: DataFrame}
          name           显示名
          symbol         标的（多标的用逗号分隔）
          frequency      频率
          asset_type     资产类型
          tags           标签
          storage_format 存储格式
        """
        # 取第一个 DataFrame 推导 schema
        first_df = next(iter(data.values())) if data else pd.DataFrame()
        schema = DatasetSchema.from_dataframe(first_df) if not first_df.empty else DatasetSchema()

        # 推导时间范围
        start_time = None
        end_time = None
        total_rows = 0
        for sym, df in data.items():
            total_rows += len(df)
            if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
                s = str(df.index.min())
                e = str(df.index.max())
                if start_time is None or s < start_time:
                    start_time = s
                if end_time is None or e > end_time:
                    end_time = e

        if not symbol:
            symbol = ",".join(data.keys())

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            name=name or dataset_id,
            symbol=symbol,
            frequency=frequency,
            asset_type=asset_type,
            start_time=start_time,
            end_time=end_time,
            rows=total_rows,
            storage_path=":memory:",
            storage_format=storage_format,
            schema=schema,
            tags=tags or [],
        )

        self.register(metadata)
        # 缓存数据
        self._cache[dataset_id] = data
        return metadata

    def unregister(self, dataset_id: str) -> None:
        """注销数据集"""
        self._datasets.pop(dataset_id, None)
        self._cache.pop(dataset_id, None)

    # ---------------------------------------------------------
    # 查询
    # ---------------------------------------------------------
    def get(self, dataset_id: str) -> Optional[DatasetMetadata]:
        """获取数据集元信息"""
        return self._datasets.get(dataset_id)

    def list(
        self,
        *,
        tag: Optional[str] = None,
        asset_type: Optional[str] = None,
        frequency: Optional[str] = None,
    ) -> List[DatasetMetadata]:
        """
        列出数据集（可按标签/类型/频率过滤）
        """
        result = list(self._datasets.values())

        if tag is not None:
            result = [m for m in result if tag in m.tags]

        if asset_type is not None:
            result = [m for m in result if m.asset_type == asset_type]

        if frequency is not None:
            result = [m for m in result if m.frequency == frequency]

        return result

    def search(self, q: str = "") -> List[DatasetMetadata]:
        """
        搜索数据集（ID / name / symbol 模糊匹配）
        """
        if not q:
            return list(self._datasets.values())

        q_lower = q.lower()
        return [
            m for m in self._datasets.values()
            if q_lower in m.dataset_id.lower()
            or q_lower in m.name.lower()
            or q_lower in m.symbol.lower()
        ]

    # ---------------------------------------------------------
    # 加载
    # ---------------------------------------------------------
    def load(
        self,
        dataset_id: str,
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        加载数据集

        优先从缓存取，否则从存储路径加载
        """
        # 1. 内存缓存
        if dataset_id in self._cache:
            data = self._cache[dataset_id]
            # 过滤
            result = {}
            target = symbols if symbols else list(data.keys())
            for sym in target:
                if sym in data:
                    df = data[sym]
                    if start:
                        df = df[df.index >= pd.Timestamp(start)]
                    if end:
                        df = df[df.index <= pd.Timestamp(end)]
                    result[sym] = df
            return result

        # 2. 从存储路径加载
        meta = self.get(dataset_id)
        if meta is None:
            raise ValueError(f"Dataset '{dataset_id}' not registered")

        if not meta.storage_path or meta.storage_path == ":memory:":
            raise ValueError(
                f"Dataset '{dataset_id}' has no storage path and is not cached"
            )

        loader = get_loader(meta.storage_format)
        data = loader.load(meta.storage_path, symbols=symbols, start=start, end=end)

        # 缓存
        self._cache[dataset_id] = data
        return data

    def preview(
        self,
        dataset_id: str,
        n: int = 100,
    ) -> Dict[str, Any]:
        """
        预览数据集（前 n 行）

        返回格式：
          {
            "dataset_id": "btcusdt_1m",
            "symbols": ["BTCUSDT"],
            "preview": {
              "BTCUSDT": {
                "columns": [...],
                "rows": [[...], ...]
              }
            }
          }
        """
        data = self.load(dataset_id)
        preview = {}
        for sym, df in data.items():
            head = df.head(n)
            preview[sym] = {
                "columns": list(df.columns),
                "dtypes": {c: str(dt) for c, dt in df.dtypes.items()},
                "rows": head.values.tolist(),
                "index": [str(i) for i in head.index],
            }

        return {
            "dataset_id": dataset_id,
            "symbols": list(data.keys()),
            "preview": preview,
        }

    def stats(self, dataset_id: str) -> Dict[str, Any]:
        """
        数据集统计

        返回：
          {
            "rows": 1000000,
            "missing": 0,
            "duplicates": 0,
            "symbols": 3,
            ...
          }
        """
        data = self.load(dataset_id)
        total_rows = 0
        total_missing = 0
        total_duplicates = 0

        for sym, df in data.items():
            total_rows += len(df)
            total_missing += int(df.isnull().sum().sum())
            total_duplicates += int(df.index.duplicated().sum())

        return {
            "dataset_id": dataset_id,
            "symbols": len(data),
            "rows": total_rows,
            "missing": total_missing,
            "duplicates": total_duplicates,
        }

    # ---------------------------------------------------------
    # 校验
    # ---------------------------------------------------------
    def validate(self, dataset_id: str) -> Dict[str, Any]:
        """
        校验数据集

        对每个 symbol 的 DataFrame 运行校验
        """
        data = self.load(dataset_id)
        results = {}
        overall_ok = True

        for sym, df in data.items():
            vr = self._validator.validate(df)
            results[sym] = vr.to_dict()
            if not vr.ok:
                overall_ok = False

        return {
            "dataset_id": dataset_id,
            "ok": overall_ok,
            "symbols": results,
        }

    # ---------------------------------------------------------
    # 全量导出
    # ---------------------------------------------------------
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """所有数据集元信息导出为 dict 列表"""
        return [m.to_dict() for m in self._datasets.values()]


# ---- 全局单例 ----

_registry: Optional[DatasetRegistry] = None


def get_dataset_registry() -> DatasetRegistry:
    """获取全局 DatasetRegistry"""
    global _registry
    if _registry is None:
        _registry = DatasetRegistry()
    return _registry


def set_dataset_registry(registry: DatasetRegistry) -> None:
    """设置全局 DatasetRegistry"""
    global _registry
    _registry = registry
