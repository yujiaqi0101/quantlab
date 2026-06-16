"""
DatasetService — 数据集业务入口

封装：数据集注册、加载、查询、校验
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..dataset.registry import DatasetRegistry
from ..dataset.catalog import DataCatalog
from ..dataset.loader import CSVLoader

logger = logging.getLogger("quantlab.services.dataset")


class DatasetService:
    """
    数据集服务（Facade）

    统一入口：
      - 列出数据集
      - 加载数据
      - 获取元信息
      - 校验数据
    """

    def __init__(
        self,
        registry: Optional[DatasetRegistry] = None,
    ) -> None:
        self._registry = registry or DatasetRegistry()
        self._loader = CSVLoader()

    def list_datasets(self) -> List[Dict[str, Any]]:
        """列出所有数据集"""
        if hasattr(self._registry, 'list_all'):
            return self._registry.list_all()
        return []

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """获取数据集详情"""
        result = self._registry.get(dataset_id)
        if result and hasattr(result, '__dict__'):
            return result.__dict__
        return result

    def load_data(self, dataset_id: str, symbols: Optional[List[str]] = None) -> Any:
        """加载数据集"""
        meta = self._registry.get(dataset_id)
        if meta and hasattr(meta, 'path'):
            return self._loader.load(meta.path, symbols=symbols)
        return None

    def symbols(self, dataset_id: str) -> List[str]:
        """列出数据集中的标的"""
        ds = self._registry.get(dataset_id)
        if ds and "symbols" in ds:
            return ds["symbols"]
        return []

    def validate(self, dataset_id: str) -> Dict[str, Any]:
        """校验数据集"""
        try:
            data = self.load_data(dataset_id)
            if data is None:
                return {"valid": False, "error": "Data is None"}
            return {"valid": True, "message": "OK"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
