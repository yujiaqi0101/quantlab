"""
FeatureSet — 特征集合

ML Lab 第二层：特征集合可复用、版本化

  不要把 Feature 单独管理。
  升级：FeatureSet 把多个 Feature 组合起来，命名、版本化、复用。

  feature_set = FeatureSet(
      name="momentum_features",
      features=[RSI14, RSI21, Momentum20, ATR14, VolumeZScore],
      description="动量类特征集合 v1",
      version="1.0",
  )

  X = feature_set.compute(df)  # → DataFrame，每列一个特征
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .base import Feature, FeatureRegistry, get_feature_registry

logger = logging.getLogger("quantlab.ml.feature.set")


@dataclass
class FeatureSet:
    """
    特征集合

    用法：
        fs = FeatureSet(
            name="momentum_v1",
            feature_ids=["rsi14", "rsi21", "momentum20", "atr14"],
            description="动量特征集合 v1",
        )
        X = fs.compute(df)
    """
    name: str                                  # 唯一名称，如 "momentum_v1"
    feature_ids: List[str] = field(default_factory=list)
    description: str = ""
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    fs_id: str = field(default_factory=lambda: f"FS-{uuid.uuid4().hex[:8]}")
    created_at: str = ""

    # 可选：直接持有 Feature 对象（绕过 registry）
    _features: Optional[List[Feature]] = None
    _registry: Optional[FeatureRegistry] = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()

    def set_registry(self, registry: FeatureRegistry) -> "FeatureSet":
        self._registry = registry
        return self

    def set_features(self, features: List[Feature]) -> "FeatureSet":
        """直接设置 Feature 对象列表"""
        self._features = features
        self.feature_ids = [f.feature_id for f in features]
        return self

    def get_features(self) -> List[Feature]:
        """获取 Feature 对象列表"""
        if self._features is not None:
            return self._features
        reg = self._registry or get_feature_registry()
        return [reg.get(fid) for fid in self.feature_ids if reg.get(fid) is not None]

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有特征

        Returns:
            DataFrame，每列一个特征，index 与 df 对齐
        """
        if self._features is not None:
            # 直接使用持有的 Feature 对象
            data = {}
            for feat in self._features:
                try:
                    series = feat.compute(df)
                    # 若返回 DataFrame，取第一列
                    if isinstance(series, pd.DataFrame):
                        for col in series.columns:
                            data[col] = series[col]
                    else:
                        data[feat.feature_id] = series
                except Exception as e:
                    logger.error(f"Feature {feat.feature_id} compute failed: {e}")
            return pd.DataFrame(data, index=df.index)
        else:
            # 通过 registry 计算
            reg = self._registry or get_feature_registry()
            return reg.compute_many(self.feature_ids, df)

    def add_feature(self, feature_id: str) -> "FeatureSet":
        """添加特征"""
        if feature_id not in self.feature_ids:
            self.feature_ids.append(feature_id)
        return self

    def remove_feature(self, feature_id: str) -> "FeatureSet":
        """移除特征"""
        if feature_id in self.feature_ids:
            self.feature_ids.remove(feature_id)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fs_id": self.fs_id,
            "name": self.name,
            "feature_ids": self.feature_ids,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "n_features": len(self.feature_ids),
            "created_at": self.created_at,
        }


class FeatureSetRegistry:
    """
    特征集合注册表

    管理所有 FeatureSet，支持命名复用。

    用法：
        reg = get_feature_set_registry()
        reg.register(fs)
        fs = reg.get("momentum_v1")
        all_fs = reg.list_all()

    持久化（M2 新增）：
        reg = FeatureSetRegistry(persist=True)   # 开启 SQLite 持久化
        reg.load_from_store()                     # 从 DB 恢复
        # register / delete 会自动同步到 DB
    """

    def __init__(self, persist: bool = False) -> None:
        self._sets: Dict[str, FeatureSet] = {}
        self._persist = persist
        self._store = None
        if persist:
            from ..storage import get_ml_store
            self._store = get_ml_store()
        self._register_builtin()

    def _register_builtin(self) -> None:
        """注册内置 FeatureSet"""
        builtins = [
            FeatureSet(
                name="momentum_v1",
                feature_ids=["rsi14", "rsi21", "momentum20", "atr14"],
                description="动量特征集合 v1：RSI + Momentum + ATR",
                version="1.0",
                tags=["momentum", "builtin"],
            ),
            FeatureSet(
                name="volume_v1",
                feature_ids=["vol_zscore20", "momentum20"],
                description="成交量特征集合 v1：VolumeZScore + Momentum",
                version="1.0",
                tags=["volume", "builtin"],
            ),
            FeatureSet(
                name="trend_v1",
                feature_ids=["rsi14", "macd_12_26_9", "atr14"],
                description="趋势特征集合 v1：RSI + MACD + ATR",
                version="1.0",
                tags=["trend", "builtin"],
            ),
        ]
        for fs in builtins:
            self._sets[fs.name] = fs

    def register(self, fs: FeatureSet) -> str:
        """注册 FeatureSet"""
        self._sets[fs.name] = fs
        if self._persist and self._store:
            self._store.save_feature_set(fs.to_dict())
        logger.info(f"FeatureSet registered: {fs.name} ({len(fs.feature_ids)} features)")

        # 自动注册到 AssetRegistry
        try:
            from ...asset import register_feature_set_asset
            register_feature_set_asset(fs)
        except Exception as e:
            logger.warning(f"Failed to auto-register FeatureSet asset: {e}")

        return fs.name

    def get(self, name: str) -> Optional[FeatureSet]:
        return self._sets.get(name)

    def list_all(self, tag: Optional[str] = None) -> List[FeatureSet]:
        """列出所有 FeatureSet"""
        result = list(self._sets.values())
        if tag:
            result = [fs for fs in result if tag in fs.tags]
        return result

    def delete(self, name: str) -> bool:
        ok = self._sets.pop(name, None) is not None
        if ok and self._persist and self._store:
            self._store.delete_feature_set_by_name(name)
        return ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._sets),
            "sets": [fs.to_dict() for fs in self.list_all()],
        }

    # ------------------------------------------------------------------
    # 持久化：从 DB 恢复
    # ------------------------------------------------------------------

    def load_from_store(self) -> int:
        """
        从 SQLite 恢复所有 FeatureSet（不含 builtin，builtin 已在 __init__ 注册）。
        返回恢复的 FeatureSet 数量。
        """
        if not self._store:
            return 0
        rows = self._store.list_feature_sets()
        count = 0
        for row in rows:
            name = row["name"]
            if name in self._sets:
                continue    # builtin 优先，不覆盖
            fs = FeatureSet(
                name=name,
                feature_ids=row["feature_ids"],
                description=row["description"],
                version=row["version"],
                tags=row["tags"],
            )
            fs.fs_id = row["fs_id"]
            fs.created_at = row["created_at"]
            self._sets[name] = fs
            count += 1
        logger.info(f"Loaded {count} feature sets from store")
        return count


_fs_registry: Optional[FeatureSetRegistry] = None


def get_feature_set_registry(persist: bool = True) -> FeatureSetRegistry:
    """
    获取 FeatureSetRegistry 单例。

    Args:
        persist: 是否开启 SQLite 持久化（默认 True）
                 首次创建时会自动从 DB 恢复已有 FeatureSet
    """
    global _fs_registry
    if _fs_registry is None:
        _fs_registry = FeatureSetRegistry(persist=persist)
        if persist:
            _fs_registry.load_from_store()
    return _fs_registry
