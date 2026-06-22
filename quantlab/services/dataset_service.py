"""
DatasetService — 数据集业务入口

统一封装数据集查询、加载、预览、统计。
基于 DatasetManager 实现，不再依赖独立的 datasets.db。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..ml.dataset import get_dataset_manager

logger = logging.getLogger("quantlab.services.dataset")


class DatasetService:
    """
    数据集服务（Facade）

    统一入口：
      - 列出数据集 / 搜索
      - 获取元信息 / 详情
      - 加载数据
      - 预览 / 统计
    """

    def __init__(self) -> None:
        self._mgr = get_dataset_manager()

    # ---- 查询 ----

    def list_datasets(
        self,
        q: str = "",
        tag: Optional[str] = None,
        asset_type: Optional[str] = None,
        frequency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出所有数据集"""
        result = []
        for ds in self._mgr.list_datasets():
            if q and q.lower() not in ds.name.lower():
                continue
            if tag and tag not in ds.tags:
                continue
            if asset_type and ds.asset_type != asset_type:
                continue
            if frequency and ds.frequency != frequency:
                continue
            result.append(ds.to_dict())
        return result

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """获取数据集详情"""
        ds = self._mgr.get_dataset(dataset_id)
        if ds is None:
            return None
        return ds.to_dict()

    def get_symbols(self, dataset_id: str) -> List[str]:
        """列出数据集中的标的"""
        ds = self._mgr.get_dataset(dataset_id)
        if ds is None:
            return []
        return ds.symbols if isinstance(ds.symbols, list) else [ds.symbols]

    # ---- 数据加载 ----

    def load_data(self, dataset_id: str, symbols: Optional[List[str]] = None) -> Any:
        """加载数据集"""
        ds = self._mgr.get_dataset(dataset_id)
        if ds is None:
            return None
        df = ds.get_data()
        if df is None:
            self._mgr.load_dataset_data(dataset_id)
            df = ds.get_data()
        return df

    # ---- 预览 / 统计 ----

    def preview(self, dataset_id: str, n: int = 100) -> Dict[str, Any]:
        """数据预览"""
        return self._mgr.preview(dataset_id, n) or {}

    def stats(self, dataset_id: str) -> Dict[str, Any]:
        """数据统计"""
        s = self._mgr.get_stats(dataset_id)
        return s.to_dict() if s else {}
