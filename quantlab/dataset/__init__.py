"""
V4.3 Dataset Registry — 数据注册中心

与 Strategy Registry 对称设计：
  StrategyRegistry → 有哪些策略
  DatasetRegistry  → 有哪些数据

模块：
  metadata   DatasetMetadata / DatasetSchema / DatasetVersion / DatasetColumn
  registry   DatasetRegistry（注册/查询/搜索/加载/校验）
  catalog    DataCatalog（自动扫描 data/ 目录注册数据集）
  loader     BaseLoader / CSVLoader / ParquetLoader
  validator  DatasetValidator / ValidationResult
"""

from .metadata import (
    DatasetColumn,
    DatasetSchema,
    DatasetVersion,
    DatasetMetadata,
    DATASET_TAGS,
    FREQUENCIES,
    ASSET_TYPES,
)

from .registry import (
    DatasetRegistry,
    get_dataset_registry,
    set_dataset_registry,
)

from .catalog import DataCatalog

from .loader import (
    BaseLoader,
    CSVLoader,
    ParquetLoader,
    get_loader,
)

from .validator import (
    DatasetValidator,
    ValidationResult,
)


__all__ = [
    # metadata
    "DatasetColumn",
    "DatasetSchema",
    "DatasetVersion",
    "DatasetMetadata",
    "DATASET_TAGS",
    "FREQUENCIES",
    "ASSET_TYPES",
    # registry
    "DatasetRegistry",
    "get_dataset_registry",
    "set_dataset_registry",
    # catalog
    "DataCatalog",
    # loader
    "BaseLoader",
    "CSVLoader",
    "ParquetLoader",
    "get_loader",
    # validator
    "DatasetValidator",
    "ValidationResult",
]
