"""
Label — 标签抽象基类

ML Lab 第三部分：统一标签接口

  class MyLabel(Label):
      def generate(self, df: pd.DataFrame) -> pd.Series:
          ...

  registry = get_label_registry()
  registry.register(MyLabel())
  series = registry.generate("future_return_10", df)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.ml.label")


@dataclass
class Label(ABC):
    """标签抽象基类"""
    label_id: str = ""
    name: str = ""
    description: str = ""
    label_type: str = "regression"     # regression / classification
    classes: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    required_columns: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.label_id:
            self.label_id = self.name.lower().replace(" ", "_")

    @abstractmethod
    def generate(self, df: pd.DataFrame) -> pd.Series:
        """生成标签"""
        ...

    def validate(self, df: pd.DataFrame) -> bool:
        for col in self.required_columns:
            if col not in df.columns:
                return False
        return True

    def to_dict(self) -> Dict:
        return {
            "label_id": self.label_id,
            "name": self.name,
            "description": self.description,
            "label_type": self.label_type,
            "classes": self.classes,
            "params": self.params,
            "required_columns": self.required_columns,
        }


class LabelRegistry:
    """标签注册表"""

    def __init__(self) -> None:
        self._labels: Dict[str, Label] = {}

    def register(self, label: Label) -> None:
        self._labels[label.label_id] = label
        logger.info(f"Label registered: {label.label_id} ({label.name})")

    def unregister(self, label_id: str) -> bool:
        return self._labels.pop(label_id, None) is not None

    def get_label(self, label_id: str) -> Optional[Label]:
        return self._labels.get(label_id)

    def has(self, label_id: str) -> bool:
        return label_id in self._labels

    def list_labels(self, label_type: str = "") -> List[Label]:
        result = list(self._labels.values())
        if label_type:
            result = [l for l in result if l.label_type == label_type]
        return result

    def generate(self, label_id: str, df: pd.DataFrame) -> Optional[pd.Series]:
        label = self._labels.get(label_id)
        if not label:
            return None
        if not label.validate(df):
            return None
        try:
            return label.generate(df)
        except Exception as e:
            logger.error(f"Label {label_id} generate failed: {e}")
            return None

    def to_dict(self) -> Dict:
        return {
            "total": len(self._labels),
            "labels": [l.to_dict() for l in self._labels.values()],
        }


_label_registry: Optional[LabelRegistry] = None


def get_label_registry() -> LabelRegistry:
    global _label_registry
    if _label_registry is None:
        _label_registry = LabelRegistry()
        try:
            from .builtin import register_all_builtin
            register_all_builtin(_label_registry)
        except Exception as e:
            logger.warning(f"Failed to register builtin labels: {e}")
    return _label_registry
