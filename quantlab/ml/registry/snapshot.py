"""
Snapshot Manager — 依赖快照管理

ML Lab M6：FeatureSet/LabelSet 快照

  问题：
    训练时用 RSI14, Momentum20, ATR14
    实盘时 FeatureSet 被修改成 RSI21, Momentum10, ATR20
    → 预测立即失效

  解决：
    训练完成时，保存 FeatureSet 和 LabelSet 的完整定义快照到模型包
    实盘加载模型时，从快照恢复特征定义

  快照内容：
    - feature_set_id / label_set_id（引用）
    - hash（内容指纹，检测源是否被修改）
    - 完整定义（feature_ids + 每个 feature 的参数）
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from .package import FeatureSetSnapshot, LabelSetSnapshot

logger = logging.getLogger("quantlab.ml.registry.snapshot")


class SnapshotManager:
    """
    快照管理器

    用法：
        mgr = SnapshotManager()
        fs_snap = mgr.capture_feature_set("momentum_v1")
        ls_snap = mgr.capture_label_set("return_10d")
        # 保存到 ModelPackage
        pkg.feature_set_snapshot = fs_snap
        pkg.label_set_snapshot = ls_snap
    """

    def capture_feature_set(self, feature_set_id: str) -> Optional[FeatureSetSnapshot]:
        """
        捕获 FeatureSet 快照

        Args:
            feature_set_id: FeatureSet 名称

        Returns:
            FeatureSetSnapshot 或 None（如果 FeatureSet 不存在）
        """
        try:
            from ..feature import get_feature_set_registry, get_feature_registry
            fs_reg = get_feature_set_registry()
            fs = fs_reg.get(feature_set_id)
            if fs is None:
                logger.warning(f"FeatureSet not found: {feature_set_id}")
                return None

            # 收集每个 feature 的完整定义
            feat_reg = get_feature_registry()
            feature_defs: List[Dict[str, Any]] = []
            for fid in fs.feature_ids:
                feat = feat_reg.get_feature(fid)
                if feat is not None:
                    feature_defs.append({
                        "feature_id": feat.feature_id,
                        "name": getattr(feat, "name", feat.feature_id),
                        "params": getattr(feat, "params", {}),
                        "category": getattr(feat, "category", ""),
                    })
                else:
                    feature_defs.append({
                        "feature_id": fid,
                        "name": fid,
                        "params": {},
                        "category": "",
                    })

            # 计算 hash
            hash_str = self._hash_feature_set(fs.feature_ids, feature_defs)

            import pandas as pd
            return FeatureSetSnapshot(
                feature_set_id=feature_set_id,
                name=fs.name,
                feature_ids=list(fs.feature_ids),
                feature_defs=feature_defs,
                hash=hash_str,
                snapshot_at=pd.Timestamp.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"Capture FeatureSet snapshot failed: {e}")
            return None

    def capture_label_set(self, label_set_id: str) -> Optional[LabelSetSnapshot]:
        """
        捕获 LabelSet 快照

        Args:
            label_set_id: LabelSet 名称

        Returns:
            LabelSetSnapshot 或 None
        """
        try:
            from ..label import get_label_set_registry, get_label_registry
            ls_reg = get_label_set_registry()
            ls = ls_reg.get(label_set_id)
            if ls is None:
                logger.warning(f"LabelSet not found: {label_set_id}")
                return None

            # 获取 Label 的完整定义
            label_reg = get_label_registry()
            label = label_reg.get_label(ls.label_id)
            params = getattr(label, "params", {}) if label else {}

            hash_str = self._hash_label_set(ls.label_id, ls.label_type, params)

            import pandas as pd
            return LabelSetSnapshot(
                label_set_id=label_set_id,
                name=ls.name,
                label_id=ls.label_id,
                label_type=ls.label_type,
                classes=list(ls.classes),
                params=params,
                hash=hash_str,
                snapshot_at=pd.Timestamp.now().isoformat(),
            )
        except Exception as e:
            logger.error(f"Capture LabelSet snapshot failed: {e}")
            return None

    def verify_feature_set(self, snapshot: FeatureSetSnapshot) -> bool:
        """
        验证当前 FeatureSet 是否与快照一致

        Returns:
            True 如果 hash 一致（源未被修改）
        """
        try:
            from ..feature import get_feature_set_registry, get_feature_registry
            fs_reg = get_feature_set_registry()
            fs = fs_reg.get(snapshot.feature_set_id)
            if fs is None:
                return False

            feat_reg = get_feature_registry()
            feature_defs: List[Dict[str, Any]] = []
            for fid in fs.feature_ids:
                feat = feat_reg.get_feature(fid)
                if feat is not None:
                    feature_defs.append({
                        "feature_id": feat.feature_id,
                        "name": getattr(feat, "name", feat.feature_id),
                        "params": getattr(feat, "params", {}),
                        "category": getattr(feat, "category", ""),
                    })
                else:
                    feature_defs.append({
                        "feature_id": fid,
                        "name": fid,
                        "params": {},
                        "category": "",
                    })

            current_hash = self._hash_feature_set(fs.feature_ids, feature_defs)
            return current_hash == snapshot.hash
        except Exception:
            return False

    def verify_label_set(self, snapshot: LabelSetSnapshot) -> bool:
        """验证当前 LabelSet 是否与快照一致"""
        try:
            from ..label import get_label_set_registry, get_label_registry
            ls_reg = get_label_set_registry()
            ls = ls_reg.get(snapshot.label_set_id)
            if ls is None:
                return False

            label_reg = get_label_registry()
            label = label_reg.get_label(ls.label_id)
            params = getattr(label, "params", {}) if label else {}

            current_hash = self._hash_label_set(ls.label_id, ls.label_type, params)
            return current_hash == snapshot.hash
        except Exception:
            return False

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _hash_feature_set(feature_ids: List[str], feature_defs: List[Dict]) -> str:
        """计算 FeatureSet 内容 hash"""
        content = json.dumps({
            "feature_ids": feature_ids,
            "feature_defs": feature_defs,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _hash_label_set(label_id: str, label_type: str, params: Dict) -> str:
        """计算 LabelSet 内容 hash"""
        content = json.dumps({
            "label_id": label_id,
            "label_type": label_type,
            "params": params,
        }, sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# 模块级单例
_snapshot_manager: Optional[SnapshotManager] = None


def get_snapshot_manager() -> SnapshotManager:
    global _snapshot_manager
    if _snapshot_manager is None:
        _snapshot_manager = SnapshotManager()
    return _snapshot_manager
