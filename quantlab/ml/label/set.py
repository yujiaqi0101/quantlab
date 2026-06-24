"""
LabelSet — 标签集合

ML Lab 第三层：标签集合版本化

  不要把 FutureReturn10 散落在代码里。
  统一 LabelSet 命名、版本化、复用。

  label_set = LabelSet(
      name="return_10d",
      label_id="future_return_10",
      description="未来10期收益率",
      version="1.0",
  )

  y = label_set.generate(df)  # → pd.Series
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import Label, LabelRegistry, get_label_registry

logger = logging.getLogger("quantlab.ml.label.set")


@dataclass
class LabelSet:
    """
    标签集合

    用法：
        ls = LabelSet(
            name="return_10d",
            label_id="future_return_10",
            description="未来10期收益率",
        )
        y = ls.generate(df)
    """
    name: str                                  # 唯一名称，如 "return_10d"
    label_id: str = ""                         # 关联的 Label ID
    description: str = ""
    version: str = "1.0"
    label_type: str = "regression"             # regression / classification
    classes: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    ls_id: str = field(default_factory=lambda: f"LS-{uuid.uuid4().hex[:8]}")
    created_at: str = ""

    # 可选：直接持有 Label 对象
    _label: Optional[Label] = None
    _registry: Optional[LabelRegistry] = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()

    def set_registry(self, registry: LabelRegistry) -> "LabelSet":
        self._registry = registry
        return self

    def set_label(self, label: Label) -> "LabelSet":
        """直接设置 Label 对象"""
        self._label = label
        self.label_id = label.label_id
        return self

    def get_label(self) -> Optional[Label]:
        if self._label is not None:
            return self._label
        reg = self._registry or get_label_registry()
        return reg.get(self.label_id)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """生成标签"""
        if self._label is not None:
            return self._label.generate(df)
        reg = self._registry or get_label_registry()
        return reg.generate(self.label_id, df)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ls_id": self.ls_id,
            "name": self.name,
            "label_id": self.label_id,
            "description": self.description,
            "version": self.version,
            "label_type": self.label_type,
            "classes": self.classes,
            "tags": self.tags,
            "created_at": self.created_at,
        }


class LabelSetRegistry:
    """
    标签集合注册表

    用法：
        reg = get_label_set_registry()
        reg.register(ls)
        ls = reg.get("return_10d")

    持久化（M2 新增）：
        reg = LabelSetRegistry(persist=True)    # 开启 SQLite 持久化
        reg.load_from_store()                    # 从 DB 恢复
        # register / delete 会自动同步到 DB
    """

    def __init__(self, persist: bool = False) -> None:
        self._sets: Dict[str, LabelSet] = {}
        self._persist = persist
        self._store = None
        if persist:
            from ..storage import get_ml_store
            self._store = get_ml_store()
        self._register_builtin()

    def _register_builtin(self) -> None:
        """注册内置 LabelSet"""
        builtins = [
            LabelSet(
                name="return_5d",
                label_id="future_return_5",
                description="未来5期收益率（回归）",
                version="1.0",
                label_type="regression",
                tags=["builtin", "return"],
            ),
            LabelSet(
                name="return_10d",
                label_id="future_return_10",
                description="未来10期收益率（回归）",
                version="1.0",
                label_type="regression",
                tags=["builtin", "return"],
            ),
            LabelSet(
                name="return_20d",
                label_id="future_return_20",
                description="未来20期收益率（回归）",
                version="1.0",
                label_type="regression",
                tags=["builtin", "return"],
            ),
            LabelSet(
                name="direction_5d",
                label_id="updown_5",
                description="未来5期方向（三分类：Up/Neutral/Down）",
                version="1.0",
                label_type="classification",
                classes=["Down", "Neutral", "Up"],
                tags=["builtin", "direction"],
            ),
            LabelSet(
                name="direction_10d",
                label_id="updown_10",
                description="未来10期方向（三分类：Up/Neutral/Down）",
                version="1.0",
                label_type="classification",
                classes=["Down", "Neutral", "Up"],
                tags=["builtin", "direction"],
            ),
        ]
        for ls in builtins:
            self._sets[ls.name] = ls

    def register(self, ls: LabelSet) -> str:
        self._sets[ls.name] = ls
        if self._persist and self._store:
            self._store.save_label_set(ls.to_dict())
        logger.info(f"LabelSet registered: {ls.name}")

        # 自动注册到 AssetRegistry
        try:
            from ...asset import register_label_set_asset
            register_label_set_asset(ls)
        except Exception as e:
            logger.warning(f"Failed to auto-register LabelSet asset: {e}")

        return ls.name

    def get(self, name: str) -> Optional[LabelSet]:
        return self._sets.get(name)

    def list_all(self, tag: Optional[str] = None) -> List[LabelSet]:
        result = list(self._sets.values())
        if tag:
            result = [ls for ls in result if tag in ls.tags]
        return result

    def delete(self, name: str) -> bool:
        ok = self._sets.pop(name, None) is not None
        if ok and self._persist and self._store:
            self._store.delete_label_set_by_name(name)
        return ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._sets),
            "sets": [ls.to_dict() for ls in self.list_all()],
        }

    # ------------------------------------------------------------------
    # 持久化：从 DB 恢复
    # ------------------------------------------------------------------

    def load_from_store(self) -> int:
        """
        从 SQLite 恢复所有 LabelSet（不含 builtin，builtin 已在 __init__ 注册）。
        返回恢复的 LabelSet 数量。
        """
        if not self._store:
            return 0
        rows = self._store.list_label_sets()
        count = 0
        for row in rows:
            name = row["name"]
            if name in self._sets:
                continue    # builtin 优先，不覆盖
            ls = LabelSet(
                name=name,
                label_id=row["label_id"],
                description=row["description"],
                version=row["version"],
                label_type=row["label_type"],
                classes=row["classes"],
                tags=row["tags"],
            )
            ls.ls_id = row["ls_id"]
            ls.created_at = row["created_at"]
            self._sets[name] = ls
            count += 1
        logger.info(f"Loaded {count} label sets from store")
        return count


_ls_registry: Optional[LabelSetRegistry] = None


def get_label_set_registry(persist: bool = True) -> LabelSetRegistry:
    """
    获取 LabelSetRegistry 单例。

    Args:
        persist: 是否开启 SQLite 持久化（默认 True）
                 首次创建时会自动从 DB 恢复已有 LabelSet
    """
    global _ls_registry
    if _ls_registry is None:
        _ls_registry = LabelSetRegistry(persist=persist)
        if persist:
            _ls_registry.load_from_store()
    return _ls_registry
