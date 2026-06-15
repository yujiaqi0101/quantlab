"""
V4.3 Dataset Registry — Metadata

数据集"自描述"模型。
前端拿到 DatasetMetadata + schema
→ 自动展示数据集信息（不需要为每个数据集手写页面）。

与 StrategyMetadata 对称设计：
  StrategyMetadata  → 策略是什么
  DatasetMetadata   → 数据是什么
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# -------------------------------------------------------------
# 数据集标签
# -------------------------------------------------------------
DATASET_TAGS = (
    "crypto",
    "equity",
    "future",
    "factor",
    "fundamental",
    "index",
    "etf",
    "forex",
    "other",
)

# 频率枚举
FREQUENCIES = (
    "tick",
    "1s", "5s", "15s", "30s",
    "1m", "5m", "15m", "30m",
    "1h", "4h",
    "1d", "1w", "1M",
    "other",
)

# 资产类型
ASSET_TYPES = (
    "crypto",
    "stock",
    "future",
    "etf",
    "index",
    "forex",
    "factor",
    "other",
)


@dataclass(slots=True)
class DatasetColumn:
    """
    单列的 schema

    字段：
      name        列名
      dtype       数据类型（float64 / int64 / object / datetime64 ...）
      role        角色（timestamp / open / high / low / close / volume / factor / other）
      description 描述
    """
    name: str
    dtype: str = "float64"
    role: str = "other"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DatasetSchema:
    """
    数据集的列定义

    前端可以据此显示：
      OHLCV → K线图
      factor → 因子表
      其他 → 通用表格
    """
    columns: List[DatasetColumn] = field(default_factory=list)

    @property
    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]

    @property
    def has_ohlcv(self) -> bool:
        roles = {c.role for c in self.columns}
        return roles >= {"open", "high", "low", "close"}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "column_names": self.column_names,
            "has_ohlcv": self.has_ohlcv,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetSchema":
        cols = []
        for c in d.get("columns", []):
            if isinstance(c, dict):
                cols.append(DatasetColumn(**c))
            elif isinstance(c, str):
                cols.append(DatasetColumn(name=c))
        return cls(columns=cols)

    @classmethod
    def from_dataframe(cls, df: Any) -> "DatasetSchema":
        """从 DataFrame 推导 schema"""
        cols = []
        OHLCV_MAP = {
            "open": "open", "high": "high", "low": "low",
            "close": "close", "volume": "volume", "vol": "volume",
        }
        for col_name in df.columns:
            role = OHLCV_MAP.get(col_name.lower(), "other")
            dtype = str(df[col_name].dtype)
            cols.append(DatasetColumn(
                name=col_name,
                dtype=dtype,
                role=role,
            ))
        return cls(columns=cols)


@dataclass(slots=True)
class DatasetVersion:
    """
    数据集版本

    数据会变化（修复缺失、修复复权、修复错误），
    所以 dataset_version 必须记录。
    Experiment 保存 dataset_id + dataset_version → 回测可复现。
    """
    version: str = "1.0.0"
    hash: str = ""           # 数据指纹（行数+列哈希）
    created_at: str = ""
    note: str = ""           # "修复 2024-01 缺失值"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class DatasetMetadata:
    """
    数据集的"对外定义"

    字段：
      dataset_id     短 ID（前端/URL 用："btcusdt_1m"）
      name           显示名
      symbol         标的（"BTCUSDT" / "CSI300" / 多标的用逗号分隔）
      frequency      频率（"1m" / "1d" / "tick"）
      asset_type     资产类型（"crypto" / "stock" / "future" ...）
      start_time     数据起始时间
      end_time       数据结束时间
      rows           行数
      storage_path   存储路径
      storage_format 存储格式（"csv" / "parquet" / "duckdb"）
      schema         DatasetSchema
      tags           标签（"crypto" / "equity" / "factor" ...）
      version        DatasetVersion
      extra          其它元数据
    """
    dataset_id: str
    name: str = ""
    symbol: str = ""
    frequency: str = "1d"
    asset_type: str = "other"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    rows: int = 0
    storage_path: str = ""
    storage_format: str = "csv"
    schema: DatasetSchema = field(default_factory=DatasetSchema)
    tags: List[str] = field(default_factory=list)
    version: DatasetVersion = field(default_factory=DatasetVersion)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.dataset_id

    # ---------------------------------------------------------
    # 派生属性
    # ---------------------------------------------------------
    @property
    def coverage(self) -> str:
        """时间覆盖范围描述"""
        if self.start_time and self.end_time:
            return f"{self.start_time} ~ {self.end_time}"
        return "unknown"

    @property
    def is_ohlcv(self) -> bool:
        return self.schema.has_ohlcv

    # ---------------------------------------------------------
    # 序列化
    # ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "name": self.name,
            "symbol": self.symbol,
            "frequency": self.frequency,
            "asset_type": self.asset_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "rows": self.rows,
            "storage_path": self.storage_path,
            "storage_format": self.storage_format,
            "schema": self.schema.to_dict(),
            "tags": list(self.tags),
            "version": self.version.to_dict(),
            "extra": dict(self.extra),
            "coverage": self.coverage,
            "is_ohlcv": self.is_ohlcv,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetMetadata":
        schema_d = d.get("schema", {})
        if isinstance(schema_d, dict):
            schema = DatasetSchema.from_dict(schema_d)
        else:
            schema = DatasetSchema()

        version_d = d.get("version", {})
        if isinstance(version_d, dict):
            version = DatasetVersion(**version_d)
        else:
            version = DatasetVersion()

        return cls(
            dataset_id=d.get("dataset_id", ""),
            name=d.get("name", ""),
            symbol=d.get("symbol", ""),
            frequency=d.get("frequency", "1d"),
            asset_type=d.get("asset_type", "other"),
            start_time=d.get("start_time"),
            end_time=d.get("end_time"),
            rows=d.get("rows", 0),
            storage_path=d.get("storage_path", ""),
            storage_format=d.get("storage_format", "csv"),
            schema=schema,
            tags=list(d.get("tags", [])),
            version=version,
            extra=dict(d.get("extra", {})),
        )
