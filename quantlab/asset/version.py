"""
VersionManager — 语义化版本管理

采用 SemVer（Major.Minor.Patch）替代简单的 v1/v2/v3 编号。

版本规则：
  Major  FeatureSet 改变（不兼容变更）
  Minor  参数调整（兼容性变更）
  Patch   Bug 修复（小修补）

例如：
  Momentum_LGBM
  ├── 1.0.0
  ├── 1.1.0
  ├── 1.2.0
  └── 2.0.0  (FeatureSet 改变 → Major bump)

以后 Observe 就知道：当前跑的是 Momentum_LGBM 1.2.0，而不是 v17。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("quantlab.asset.version")


# SemVer 正则：1.2.3 或 1.2.3-alpha
SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?"
    r"(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


class VersionBumpType(str):
    """版本递增类型"""
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


@dataclass
class SemanticVersion:
    """
    语义化版本

    用法：
        v = SemanticVersion.parse("1.2.3")
        v2 = v.bump_minor()
        print(v2)  # 1.3.0

        SemanticVersion.compare(SemanticVersion(1, 0, 0), SemanticVersion(2, 0, 0))  # -1
    """
    major: int = 0
    minor: int = 1
    patch: int = 0
    prerelease: str = ""
    build: str = ""

    def __post_init__(self) -> None:
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError(f"Version numbers must be non-negative: {self}")

    def __str__(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            s += f"-{self.prerelease}"
        if self.build:
            s += f"+{self.build}"
        return s

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.prerelease == other.prerelease
        )

    def __lt__(self, other: "SemanticVersion") -> bool:
        return self.compare(self, other) < 0

    def __le__(self, other: "SemanticVersion") -> bool:
        return self.compare(self, other) <= 0

    def __gt__(self, other: "SemanticVersion") -> bool:
        return self.compare(self, other) > 0

    def __ge__(self, other: "SemanticVersion") -> bool:
        return self.compare(self, other) >= 0

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.prerelease))

    # ------------------------------------------------------------------
    # 解析 / 格式化
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, version_str: str) -> "SemanticVersion":
        """解析版本字符串"""
        match = SEMVER_PATTERN.match(version_str.strip())
        if not match:
            raise ValueError(f"Invalid SemVer string: {version_str}")
        return cls(
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("prerelease") or "",
            build=match.group("build") or "",
        )

    @classmethod
    def try_parse(cls, version_str: str) -> Optional["SemanticVersion"]:
        """尝试解析，失败返回 None"""
        try:
            return cls.parse(version_str)
        except (ValueError, AttributeError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build": self.build,
            "string": str(self),
        }

    # ------------------------------------------------------------------
    # 递增
    # ------------------------------------------------------------------

    def bump_major(self) -> "SemanticVersion":
        """Major 递增（FeatureSet 改变）"""
        return SemanticVersion(major=self.major + 1, minor=0, patch=0)

    def bump_minor(self) -> "SemanticVersion":
        """Minor 递增（参数调整）"""
        return SemanticVersion(major=self.major, minor=self.minor + 1, patch=0)

    def bump_patch(self) -> "SemanticVersion":
        """Patch 递增（Bug 修复）"""
        return SemanticVersion(major=self.major, minor=self.minor, patch=self.patch + 1)

    def bump(self, bump_type: str) -> "SemanticVersion":
        """按类型递增"""
        if bump_type == VersionBumpType.MAJOR:
            return self.bump_major()
        elif bump_type == VersionBumpType.MINOR:
            return self.bump_minor()
        elif bump_type == VersionBumpType.PATCH:
            return self.bump_patch()
        raise ValueError(f"Unknown bump type: {bump_type}")

    # ------------------------------------------------------------------
    # 比较
    # ------------------------------------------------------------------

    @staticmethod
    def compare(v1: "SemanticVersion", v2: "SemanticVersion") -> int:
        """
        比较两个版本

        Returns:
            -1 if v1 < v2
             0 if v1 == v2
             1 if v1 > v2
        """
        if v1.major != v2.major:
            return -1 if v1.major < v2.major else 1
        if v1.minor != v2.minor:
            return -1 if v1.minor < v2.minor else 1
        if v1.patch != v2.patch:
            return -1 if v1.patch < v2.patch else 1
        # prerelease 比较（有 prerelease 的版本优先级低于无 prerelease 的）
        if not v1.prerelease and not v2.prerelease:
            return 0
        if not v1.prerelease:
            return 1
        if not v2.prerelease:
            return -1
        if v1.prerelease < v2.prerelease:
            return -1
        if v1.prerelease > v2.prerelease:
            return 1
        return 0

    def is_compatible_with(self, other: "SemanticVersion") -> bool:
        """
        检查是否与另一个版本兼容（Major 相同）

        SemVer 规则：Major 版本不同表示不兼容变更。
        """
        return self.major == other.major


class VersionManager:
    """
    版本管理器

    管理 Family 下的版本序列，确保版本唯一性。

    用法：
        mgr = VersionManager()
        v1 = mgr.get_next_version("LGBM_Momentum", bump_type="minor")
        mgr.register("LGBM_Momentum", v1)
        v2 = mgr.get_next_version("LGBM_Momentum", bump_type="patch")
    """

    def __init__(self) -> None:
        # family → List[SemanticVersion]
        self._versions: Dict[str, List[SemanticVersion]] = {}

    def register(self, family: str, version: SemanticVersion) -> bool:
        """注册版本（检查唯一性）"""
        if family not in self._versions:
            self._versions[family] = []

        # 检查版本是否已存在
        for existing in self._versions[family]:
            if existing == version:
                logger.warning(f"Version {version} already exists in family {family}")
                return False

        self._versions[family].append(version)
        # 保持排序
        self._versions[family].sort()
        logger.info(f"Version registered: {family} {version}")
        return True

    def get_latest(self, family: str) -> Optional[SemanticVersion]:
        """获取 Family 的最新版本"""
        versions = self._versions.get(family, [])
        if not versions:
            return None
        return versions[-1]

    def get_next_version(
        self,
        family: str,
        bump_type: str = VersionBumpType.MINOR,
    ) -> SemanticVersion:
        """
        获取下一个版本号

        Args:
            family: 资产族名
            bump_type: 递增类型（major / minor / patch）

        Returns:
            新的 SemanticVersion
        """
        latest = self.get_latest(family)
        if latest is None:
            # 第一个版本
            return SemanticVersion(major=1, minor=0, patch=0)
        return latest.bump(bump_type)

    def list_versions(self, family: str) -> List[SemanticVersion]:
        """列出 Family 的所有版本（升序）"""
        return list(self._versions.get(family, []))

    def list_families(self) -> List[str]:
        """列出所有 Family"""
        return sorted(self._versions.keys())

    def has_version(self, family: str, version: SemanticVersion) -> bool:
        """检查版本是否存在"""
        versions = self._versions.get(family, [])
        return any(v == version for v in versions)

    def get_version_history(self, family: str) -> List[Dict[str, Any]]:
        """获取版本历史"""
        versions = self._versions.get(family, [])
        return [v.to_dict() for v in versions]

    def to_dict(self) -> Dict[str, Any]:
        return {
            family: [v.to_dict() for v in versions]
            for family, versions in self._versions.items()
        }
