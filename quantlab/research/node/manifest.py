"""
NodeManifest — 节点元数据（可序列化、可版本化）

每个 Node 实例生成 manifest，可持久化、可对比版本。
RSI@1.0.0 与 RSI@2.0.0 可并存。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from .ports import Port


class NodeCategory(str, Enum):
    """节点分类 — 统一替代旧 Feature.category 与 FactorInfo.category"""
    DATA = "data"                     # 原始数据 (Close/High/Low/Open/Volume/VWAP)
    TRANSFORM = "transform"          # 数据变换 (Return/ZScore/Log/Diff/Normalize)
    INDICATOR = "indicator"          # 技术指标 (RSI/ATR/MACD/EMA/SMA)
    ALPHA = "alpha"                  # Alpha 因子 (Alpha001-101, Alpha001-191)
    AGGREGATION = "aggregation"      # 聚合 (RollingMean/Std/Max/Min)
    RANKING = "ranking"              # 截面排名 (CrossSectionRank/Percentile/TopN)
    SELECTION = "selection"          # 标的筛选 (UniverseFilter/LiquidityFilter)
    LABEL = "label"                  # 标签 (FutureReturn/TripleBarrier/Direction)
    CUSTOM = "custom"                # 用户自定义


@dataclass
class NodeMetadata:
    """节点附加元信息"""
    description: str = ""
    author: str = ""
    cost: int = 1                   # 1-5 星级，越高越昂贵
    deprecated: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "author": self.author,
            "cost": self.cost,
            "deprecated": self.deprecated,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NodeMetadata":
        return cls(
            description=d.get("description", ""),
            author=d.get("author", ""),
            cost=d.get("cost", 1),
            deprecated=d.get("deprecated", False),
            tags=list(d.get("tags", [])),
        )


@dataclass
class NodeManifest:
    """
    节点清单 — 可序列化、可版本化、可对比

    Attributes:
        id:              节点唯一标识 (如 "rsi14", "alpha017")
        version:         版本号 (如 "1.0.0")
        category:        节点分类
        inputs:          输入端口声明
        outputs:         输出端口声明
        params:          默认参数
        metadata:        附加元信息
        fingerprint_basis: 用于计算指纹的代码+参数哈希基串
        deprecated:       是否已废弃
    """
    id: str
    version: str = "1.0.0"
    category: NodeCategory = NodeCategory.CUSTOM
    inputs: List[Port] = field(default_factory=list)
    outputs: List[Port] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: NodeMetadata = field(default_factory=NodeMetadata)
    fingerprint_basis: str = ""
    deprecated: bool = False

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("NodeManifest.id must not be empty")
        if not self.version:
            self.version = "1.0.0"
        if self.deprecated:
            self.metadata.deprecated = True

    # ------------------------------------------------------------------ #
    # 序列化
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "category": self.category.value,
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "params": dict(self.params),
            "metadata": self.metadata.to_dict(),
            "fingerprint_basis": self.fingerprint_basis,
            "deprecated": self.deprecated,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "NodeManifest":
        return cls(
            id=d["id"],
            version=d.get("version", "1.0.0"),
            category=NodeCategory(d.get("category", "custom")),
            inputs=[Port.from_dict(p) for p in d.get("inputs", [])],
            outputs=[Port.from_dict(p) for p in d.get("outputs", [])],
            params=dict(d.get("params", {})),
            metadata=NodeMetadata.from_dict(d.get("metadata", {})),
            fingerprint_basis=d.get("fingerprint_basis", ""),
            deprecated=d.get("deprecated", False),
        )

    @classmethod
    def from_json(cls, s: str) -> "NodeManifest":
        return cls.from_dict(json.loads(s))

    # ------------------------------------------------------------------ #
    # 指纹
    # ------------------------------------------------------------------ #
    def fingerprint(self) -> str:
        """基于 id+version+params+fingerprint_basis 计算稳定指纹。"""
        basis = self.fingerprint_basis or self._default_basis()
        h = hashlib.sha256(basis.encode("utf-8"))
        h.update(self.id.encode("utf-8"))
        h.update(self.version.encode("utf-8"))
        # params 排序保证稳定
        params_str = json.dumps(self.params, sort_keys=True, ensure_ascii=False)
        h.update(params_str.encode("utf-8"))
        return h.hexdigest()[:16]

    def _default_basis(self) -> str:
        return f"{self.category.value}:{self.id}:{self.version}"

    # ------------------------------------------------------------------ #
    # 版本对比
    # ------------------------------------------------------------------ #
    def same_identity(self, other: "NodeManifest") -> bool:
        """同一节点 (id 相同)，忽略版本。"""
        return self.id == other.id

    def same_version(self, other: "NodeManifest") -> bool:
        return self.id == other.id and self.version == other.version

    def __repr__(self) -> str:
        return f"NodeManifest(id={self.id!r}, version={self.version!r}, category={self.category.value})"
