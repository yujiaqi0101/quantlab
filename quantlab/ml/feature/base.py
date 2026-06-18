"""
Feature — 特征抽象基类

ML Lab 第二部分：统一特征接口

  class MyFeature(Feature):
      def compute(self, df: pd.DataFrame) -> pd.Series:
          ...

  registry = get_feature_registry()
  registry.register(MyFeature())
  series = registry.compute("rsi14", df)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.ml.feature")


@dataclass
class Feature(ABC):
    """特征抽象基类"""
    feature_id: str = ""
    name: str = ""
    description: str = ""
    category: str = "general"       # momentum / mean_reversion / volatility / volume / trend
    tags: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    required_columns: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.feature_id:
            self.feature_id = self.name.lower().replace(" ", "_")

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算特征，返回 pd.Series（index 与 df 对齐）"""
        ...

    def validate(self, df: pd.DataFrame) -> bool:
        """校验输入数据是否包含所需列"""
        for col in self.required_columns:
            if col not in df.columns:
                return False
        return True

    def to_dict(self) -> Dict:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "params": self.params,
            "required_columns": self.required_columns,
        }


class FeatureRegistry:
    """
    特征注册表

    用法：
        reg = get_feature_registry()
        reg.register(RSI14())
        series = reg.compute("rsi14", df)
        features = reg.list_features()
    """

    def __init__(self) -> None:
        self._features: Dict[str, Feature] = {}

    def register(self, feature: Feature) -> None:
        self._features[feature.feature_id] = feature
        logger.info(f"Feature registered: {feature.feature_id} ({feature.name})")

    def unregister(self, feature_id: str) -> bool:
        return self._features.pop(feature_id, None) is not None

    def get_feature(self, feature_id: str) -> Optional[Feature]:
        return self._features.get(feature_id)

    def has(self, feature_id: str) -> bool:
        return feature_id in self._features

    def list_features(
        self,
        category: str = "",
        tag: str = "",
    ) -> List[Feature]:
        result = list(self._features.values())
        if category:
            result = [f for f in result if f.category == category]
        if tag:
            result = [f for f in result if tag in f.tags]
        return result

    def list_categories(self) -> List[str]:
        return list(set(f.category for f in self._features.values()))

    def compute(self, feature_id: str, df: pd.DataFrame) -> Optional[pd.Series]:
        """计算单个特征"""
        feature = self._features.get(feature_id)
        if not feature:
            return None
        if not feature.validate(df):
            logger.warning(
                f"Feature {feature_id} validation failed: missing columns "
                f"{set(feature.required_columns) - set(df.columns)}"
            )
            return None
        try:
            return feature.compute(df)
        except Exception as e:
            logger.error(f"Feature {feature_id} compute failed: {e}")
            return None

    def compute_many(
        self,
        feature_ids: List[str],
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """计算多个特征，返回 DataFrame"""
        result = {}
        for fid in feature_ids:
            series = self.compute(fid, df)
            if series is not None:
                result[fid] = series
        return pd.DataFrame(result, index=df.index)

    def to_dict(self) -> Dict:
        return {
            "total": len(self._features),
            "features": [f.to_dict() for f in self._features.values()],
            "categories": self.list_categories(),
        }


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_feature_registry: Optional[FeatureRegistry] = None


def get_feature_registry() -> FeatureRegistry:
    global _feature_registry
    if _feature_registry is None:
        _feature_registry = FeatureRegistry()
        try:
            from .builtin import register_all_builtin
            register_all_builtin(_feature_registry)
        except Exception as e:
            logger.warning(f"Failed to register builtin features: {e}")
    return _feature_registry
