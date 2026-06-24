"""
AssetPackage — 统一 Package 基类

所有 Package（Signal/Position/Risk/Execution/Observe/Strategy）继承此类。

与现有 QuantAsset（asset/base.py）的关系：
  - QuantAsset 是索引层抽象，已有完整体系
  - AssetPackage 是配置驱动的新 Package 层，专注 manifest + ref
  - AssetPackage 可通过 adapter 注册到 AssetRegistry（后续 P4 实现）

ref 引用格式：
  ref://<name>@<version>
  例如 ref://Momentum_LGBM@1.2.0
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger("quantlab.asset_package.base")


# ==================================================================
# 枚举
# ==================================================================

class PackageType(str, Enum):
    """Package 类型"""
    MODEL = "MODEL"
    SIGNAL = "SIGNAL"
    POSITION = "POSITION"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    OBSERVE = "OBSERVE"
    STRATEGY = "STRATEGY"


class PackageStatus(str, Enum):
    """Package 生命周期状态"""
    DRAFT = "DRAFT"                 # 草稿
    ACTIVE = "ACTIVE"               # 活跃
    ARCHIVED = "ARCHIVED"           # 归档
    DEPRECATED = "DEPRECATED"       # 废弃


# ==================================================================
# ref 引用
# ==================================================================

@dataclass
class Ref:
    """强版本引用：name@version"""
    name: str
    version: str

    def __str__(self) -> str:
        return f"ref://{self.name}@{self.version}"

    @classmethod
    def from_string(cls, ref_str: str) -> "Ref":
        """解析 ref://name@version"""
        return parse_ref(ref_str)

    @property
    def id(self) -> str:
        """唯一标识 name@version"""
        return f"{self.name}@{self.version}"


def parse_ref(ref_str: str) -> Ref:
    """
    解析 ref 引用字符串

    支持格式：
      ref://Momentum_LGBM@1.2.0
      Momentum_LGBM@1.2.0
      ref://Momentum_LGBM@1
      Momentum_LGBM@1
    """
    s = ref_str.strip()
    if s.startswith("ref://"):
        s = s[6:]
    if "@" not in s:
        raise ValueError(f"Invalid ref (missing @version): {ref_str}")
    name, version = s.rsplit("@", 1)
    if not name or not version:
        raise ValueError(f"Invalid ref (empty name or version): {ref_str}")
    return Ref(name=name, version=version)


# ==================================================================
# AssetPackage 基类
# ==================================================================

@dataclass
class AssetPackage(ABC):
    """
    统一 Package 基类

    子类必须实现：
      - package_type: PackageType
      - to_config() / from_config(): 类型特定配置
      - compute_hash(): 内容 hash

    用法：
        class SignalPackage(AssetPackage):
            package_type = PackageType.SIGNAL

            def to_config(self):
                return {"long_threshold": self.long_threshold, ...}
    """
    # 通用元数据
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    status: PackageStatus = PackageStatus.DRAFT
    created_at: str = ""
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)

    # 内容 hash（由 compute_hash 计算）
    hash: str = ""

    # 子类必须覆盖
    package_type: PackageType = PackageType.SIGNAL

    def __post_init__(self) -> None:
        import pandas as pd
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.hash:
            self.hash = self.compute_hash()

    # ------------------------------------------------------------------
    # 子类必须实现
    # ------------------------------------------------------------------

    @abstractmethod
    def to_config(self) -> Dict[str, Any]:
        """返回类型特定的配置（写入 manifest.yaml 的 config 字段）"""
        raise NotImplementedError

    @abstractmethod
    def compute_hash(self) -> str:
        """计算内容 hash（基于 name + version + config）"""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 序列化 / 反序列化
    # ------------------------------------------------------------------

    def to_manifest(self) -> Dict[str, Any]:
        """序列化为 manifest 字典"""
        return {
            "id": f"{self.name}@{self.version}",
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "tags": self.tags,
            "hash": self.hash,
            "config": self.to_config(),
        }

    def to_manifest_yaml(self) -> str:
        """序列化为 manifest.yaml 字符串"""
        return yaml.safe_dump(self.to_manifest(), allow_unicode=True, sort_keys=False)

    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any]) -> "AssetPackage":
        """从 manifest 字典反序列化（子类可覆盖以处理 config）"""
        pkg = cls.__new__(cls)
        pkg.name = manifest.get("name", "")
        pkg.version = manifest.get("version", "1.0.0")
        pkg.description = manifest.get("description", "")
        pkg.status = PackageStatus(manifest.get("status", "DRAFT"))
        pkg.created_at = manifest.get("created_at", "")
        pkg.created_by = manifest.get("created_by", "system")
        pkg.tags = manifest.get("tags", [])
        pkg.hash = manifest.get("hash", "")
        pkg.package_type = PackageType(manifest.get("type", cls.package_type.value))
        # 子类应覆盖 _load_config 来处理 config 字段
        pkg._load_config(manifest.get("config", {}))
        if not pkg.hash:
            pkg.hash = pkg.compute_hash()
        return pkg

    def _load_config(self, config: Dict[str, Any]) -> None:
        """从 config 字典加载类型特定配置（子类可覆盖）"""
        pass

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """唯一标识 name@version"""
        return f"{self.name}@{self.version}"

    def _hash_dict(self, d: Dict[str, Any]) -> str:
        """计算字典的 hash"""
        content = yaml.safe_dump(d, allow_unicode=True, sort_keys=True)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """完整序列化（包含 manifest）"""
        return self.to_manifest()
