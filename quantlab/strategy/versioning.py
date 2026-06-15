"""
V4.1 Strategy Registry — Versioning

策略版本 + 源码快照。

为什么必须做：
  同一份 "ma_cross" 策略，
  v1.0 用 SMA，v2.0 用 EMA，
  跑出来 Sharpe 差一倍。

  如果不记录：
    2026 年跑出 sharpe=1.8
    2028 年想复现 → 代码已变 → 复现不了

  所以 Experiment 必须记录：
    strategy_id
    strategy_version
    strategy_source_snapshot
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


logger = logging.getLogger("quantlab.strategy.versioning")


# -------------------------------------------------------------
# semver 工具（极简，不引外部依赖）
# -------------------------------------------------------------
_SEMVER_RE = re.compile(
    r"^(\d+)\.(\d+)\.(\d+)(?:-([\w\.\-]+))?(?:\+([\w\.\-]+))?$"
)


def parse_version(v: str) -> Dict[str, Any]:
    """
    解析 "1.2.3" / "1.2.3-beta.1" / "1.0.0+build.5"
    返回 {major, minor, patch, pre, build}
    解析失败返回 {}
    """
    if not isinstance(v, str):
        return {}
    m = _SEMVER_RE.match(v.strip())
    if not m:
        return {}
    return {
        "major": int(m.group(1)),
        "minor": int(m.group(2)),
        "patch": int(m.group(3)),
        "pre": m.group(4) or "",
        "build": m.group(5) or "",
    }


def version_lt(a: str, b: str) -> bool:
    """a < b（仅 major.minor.patch 比较，忽略 pre/build）"""
    pa = parse_version(a)
    pb = parse_version(b)
    if not pa or not pb:
        return False
    return (pa["major"], pa["minor"], pa["patch"]) < (
        pb["major"],
        pb["minor"],
        pb["patch"],
    )


def version_eq(a: str, b: str) -> bool:
    pa = parse_version(a)
    pb = parse_version(b)
    if not pa or not pb:
        return a == b
    return (
        pa["major"] == pb["major"]
        and pa["minor"] == pb["minor"]
        and pa["patch"] == pb["patch"]
    )


# -------------------------------------------------------------
# 源码快照
# -------------------------------------------------------------
def snapshot_source(cls: type) -> str:
    """
    用 inspect.getsource() 拿类源码
    注意：
      - 类可能定义在 .py / .pyc / 动态生成
      - 动态生成的类拿不到源码 → 返回空字符串
    """
    try:
        src = inspect.getsource(cls)
        return src
    except (OSError, TypeError) as exc:
        logger.debug(
            "snapshot_source failed for %s: %s",
            cls, exc,
        )
        return ""


def source_hash(source: str) -> str:
    """源码 SHA256（短 16 位）"""
    if not source:
        return ""
    return hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()[:16]


def class_fingerprint(cls: type) -> Dict[str, str]:
    """
    类指纹（去重/版本比较用）
      source_hash:  源码哈希
      qualname:     全限定名
      file:         源文件
      lineno:       起始行
    """
    try:
        src_file = inspect.getsourcefile(cls) or ""
    except TypeError:
        src_file = ""
    try:
        _, lineno = inspect.getsourcelines(cls)
    except (OSError, TypeError):
        lineno = 0
    src = snapshot_source(cls)
    return {
        "source_hash": source_hash(src),
        "qualname": getattr(cls, "__qualname__", cls.__name__),
        "file": src_file,
        "lineno": str(lineno),
    }


# -------------------------------------------------------------
# StrategyVersion（注册表里的"版本记录"）
# -------------------------------------------------------------
@dataclass(slots=True)
class StrategyVersion:
    """
    一个策略的某个版本记录

    字段：
      strategy_id   "ma_cross"
      version       "1.0.0"
      class_path    "quantlab.signals.MACrossStrategy"
      fingerprint   {source_hash, qualname, file, lineno}
      source        源码字符串（快照）
      registered_at ISO
    """
    strategy_id: str
    version: str
    class_path: str = ""
    fingerprint: Dict[str, str] = field(
        default_factory=dict
    )
    source: str = ""
    registered_at: str = field(
        default_factory=lambda: (
            datetime.utcnow().isoformat()
        )
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def source_hash(self) -> str:
        return self.fingerprint.get("source_hash", "")
