"""
DatasetService — 数据集业务入口

V2.0 重构：统一封装数据集注册、加载、查询、校验、预览
API 层只调本 Service，不直接碰 DatasetRegistry / DataCatalog
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..dataset.registry import DatasetRegistry, get_dataset_registry
from ..dataset.catalog import DataCatalog
from ..dataset.loader import CSVLoader

logger = logging.getLogger("quantlab.services.dataset")


class DatasetService:
    """
    数据集服务（Facade）

    统一入口：
      - 列出数据集 / 搜索
      - 获取元信息 / 详情
      - 加载数据
      - 预览 / 统计 / 校验
    """

    def __init__(
        self,
        registry: Optional[DatasetRegistry] = None,
    ) -> None:
        # 默认使用模块级 DatasetRegistry 单例，
        # 与 DataCatalog().scan() 共享同一个实例，
        # 否则 service 里的 list_datasets 永远为空
        self._registry = registry or get_dataset_registry()
        self._loader = CSVLoader()
        self._catalog_initialized = False

    def _ensure_catalog(self) -> None:
        """首次请求时自动扫描 data/ 目录"""
        if self._catalog_initialized:
            return
        try:
            catalog = DataCatalog()
            catalog.scan()
        except Exception as exc:
            logger.warning("catalog scan failed: %s", exc)
        self._catalog_initialized = True

    # ---- 查询 ----

    def list_datasets(
        self,
        q: str = "",
        tag: Optional[str] = None,
        asset_type: Optional[str] = None,
        frequency: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """列出所有数据集"""
        self._ensure_catalog()
        if q:
            datasets = self._registry.search(q)
        elif tag or asset_type or frequency:
            datasets = self._registry.list(tag=tag, asset_type=asset_type, frequency=frequency)
        else:
            datasets = self._registry.list()
        return [d.to_dict() for d in datasets]

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """获取数据集详情"""
        self._ensure_catalog()
        meta = self._registry.get(dataset_id)
        if meta is None:
            return None
        return meta.to_dict()

    def get_symbols(self, dataset_id: str) -> List[str]:
        """列出数据集中的标的"""
        self._ensure_catalog()
        meta = self._registry.get(dataset_id)
        if meta is None:
            return []
        return [s.strip() for s in meta.symbol.split(",") if s.strip()]

    # ---- 数据加载 ----

    def load_data(self, dataset_id: str, symbols: Optional[List[str]] = None) -> Any:
        """加载数据集"""
        self._ensure_catalog()
        return self._registry.load(dataset_id)

    # ---- 预览 / 统计 / 校验 ----

    def preview(self, dataset_id: str, n: int = 100) -> Dict[str, Any]:
        """数据预览"""
        self._ensure_catalog()
        return self._registry.preview(dataset_id, n=n)

    def stats(self, dataset_id: str) -> Dict[str, Any]:
        """数据统计"""
        self._ensure_catalog()
        return self._registry.stats(dataset_id)

    def validate(self, dataset_id: str) -> Dict[str, Any]:
        """校验数据集"""
        self._ensure_catalog()
        return self._registry.validate(dataset_id)
