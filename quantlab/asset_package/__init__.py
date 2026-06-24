"""
Asset Package — 统一 Package 系统

将 Signal/Position/Risk/Execution/Observe/Strategy 从硬编码类升级为
可注册、可版本管理、可复用的 Package。

设计原则：
  1. 配置驱动：Package = manifest.yaml + artifacts/
  2. 强版本引用：ref://<name>@<version>
  3. 全是 ref：Strategy manifest 里全是引用，不复制数据
  4. 与现有 .qlmodel 一致：文件系统目录存储

目录结构：
  storage/asset_packages/<type>/<name>@<version>/
    manifest.yaml    # 元数据 + ref 引用
    artifacts/        # 实际文件

Package 类型：
  MODEL / SIGNAL / POSITION / RISK / EXECUTION / OBSERVE / STRATEGY
"""

from .base import (
    AssetPackage,
    PackageType,
    PackageStatus,
    Ref,
    parse_ref,
)
from .storage import PackageStorage, get_package_storage
from .registry import PackageRegistry, get_package_registry

__all__ = [
    "AssetPackage",
    "PackageType",
    "PackageStatus",
    "Ref",
    "parse_ref",
    "PackageStorage",
    "get_package_storage",
    "PackageRegistry",
    "get_package_registry",
]
