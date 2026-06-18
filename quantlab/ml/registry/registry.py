"""
Model Registry — 模型版本管理

ML Lab M4：模型注册中心 + Family 概念 + Lifecycle

  ModelVersion
    - version_id: MV-xxx
    - name: LGBM_Momentum_v3
    - family: LGBM_Momentum          # M4 新增：模型族
    - version_number: 3              # M4 新增：版本号
    - model_type: LIGHTGBM
    - params: {...}
    - metrics: {sharpe: 1.4, ic: 0.1}
    - dataset_id: DS-xxx
    - feature_ids: [...]
    - label_id: future_return_10
    - lifecycle: CANDIDATE           # M4 新增：生命周期状态
    - parent_version_id: MV-yyy      # M4 新增：父版本（用于 lineage）
    - created_at: 2025-01-01

  ModelRegistry
    - register(version)
    - get_version(version_id)
    - list_versions(model_type=None)
    - get_latest(model_type)
    - list_families()                # M4 新增
    - get_family(name)               # M4 新增
    - get_champion(family)           # M4 新增
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

from ..model import Model, ModelType

logger = logging.getLogger("quantlab.ml.registry")


class LifecycleStatus(str, Enum):
    """M4 模型生命周期状态"""
    TRAINING = "TRAINING"           # 训练中
    VALIDATING = "VALIDATING"       # 验证中
    CANDIDATE = "CANDIDATE"         # 候选（通过验证）
    CHAMPION = "CHAMPION"           # 冠军（上线）
    RETIRED = "RETIRED"             # 退役


@dataclass
class ModelVersion:
    """模型版本"""
    version_id: str = field(default_factory=lambda: f"MV-{uuid.uuid4().hex[:8]}")
    name: str = ""                          # 例如 LGBM_Momentum_v3
    model_type: ModelType = ModelType.LIGHTGBM
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    dataset_id: str = ""
    feature_ids: List[str] = field(default_factory=list)
    label_id: str = ""
    is_classifier: bool = False
    created_at: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    _model: Optional[Model] = None         # 实际模型对象（可选）

    # M4 新增字段
    family: str = ""                        # 模型族名（如 LGBM_Momentum）
    version_number: int = 0                 # 版本号（如 3）
    lifecycle: LifecycleStatus = LifecycleStatus.TRAINING
    parent_version_id: str = ""             # 父版本 ID（用于 lineage）
    lineage_note: str = ""                  # 血统变更说明（如 "增加 ATR 特征"）
    promoted_at: str = ""                   # 成为 Champion 的时间
    retired_at: str = ""                    # 退役时间

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.name:
            self.name = f"{self.model_type.value}_v{self.version_id[-4:]}"
        # 自动推断 family
        if not self.family:
            self.family = self._infer_family()
        # 自动推断 version_number
        if self.version_number == 0:
            self.version_number = self._infer_version_number()

    def _infer_family(self) -> str:
        """从 name 推断 family（LGBM_Momentum_v3 → LGBM_Momentum）"""
        if "_v" in self.name:
            return self.name.rsplit("_v", 1)[0]
        return self.name

    def _infer_version_number(self) -> int:
        """从 name 推断版本号（LGBM_Momentum_v3 → 3）"""
        if "_v" in self.name:
            try:
                return int(self.name.rsplit("_v", 1)[1])
            except (ValueError, IndexError):
                pass
        return 1

    def set_model(self, model: Model) -> None:
        """关联已训练的模型对象"""
        self._model = model

    def get_model(self) -> Optional[Model]:
        return self._model

    def to_dict(self, include_model: bool = False) -> Dict:
        d = {
            "version_id": self.version_id,
            "name": self.name,
            "model_type": self.model_type.value,
            "params": self.params,
            "metrics": self.metrics,
            "dataset_id": self.dataset_id,
            "feature_ids": self.feature_ids,
            "label_id": self.label_id,
            "is_classifier": self.is_classifier,
            "created_at": self.created_at,
            "description": self.description,
            "tags": self.tags,
            "has_model": self._model is not None,
            # M4 新增
            "family": self.family,
            "version_number": self.version_number,
            "lifecycle": self.lifecycle.value,
            "parent_version_id": self.parent_version_id,
            "lineage_note": self.lineage_note,
            "promoted_at": self.promoted_at,
            "retired_at": self.retired_at,
        }
        if include_model and self._model:
            d["model_info"] = self._model.to_dict()
        return d


class ModelRegistry:
    """
    模型注册中心

    M4 升级：支持 Model Family 概念

    用法：
        reg = get_model_registry()
        version = ModelVersion(
            name="LGBM_Momentum_v1",
            model_type=ModelType.LIGHTGBM,
            metrics={"sharpe": 1.4, "ic": 0.1},
        )
        reg.register(version)
        latest = reg.get_latest(ModelType.LIGHTGBM)
        # M4 新增
        family_versions = reg.get_family("LGBM_Momentum")
        champion = reg.get_champion("LGBM_Momentum")
    """

    def __init__(self) -> None:
        self._versions: Dict[str, ModelVersion] = {}
        # M4: family → champion version_id
        self._champions: Dict[str, str] = {}

    def register(self, version: ModelVersion) -> str:
        """注册模型版本"""
        self._versions[version.version_id] = version
        logger.info(
            f"Model version registered: {version.version_id} "
            f"({version.name}, family={version.family})"
        )
        return version.version_id

    def get_version(self, version_id: str) -> Optional[ModelVersion]:
        return self._versions.get(version_id)

    def get_latest(self, model_type: ModelType) -> Optional[ModelVersion]:
        """获取指定类型的最新版本"""
        versions = [
            v for v in self._versions.values()
            if v.model_type == model_type
        ]
        if not versions:
            return None
        # 按 created_at 降序
        versions.sort(key=lambda v: v.created_at, reverse=True)
        return versions[0]

    def list_versions(
        self,
        model_type: Optional[ModelType] = None,
        tag: Optional[str] = None,
        family: Optional[str] = None,
        lifecycle: Optional[LifecycleStatus] = None,
    ) -> List[ModelVersion]:
        """列出模型版本（M4 扩展：支持 family/lifecycle 过滤）"""
        result = list(self._versions.values())
        if model_type:
            result = [v for v in result if v.model_type == model_type]
        if tag:
            result = [v for v in result if tag in v.tags]
        if family:
            result = [v for v in result if v.family == family]
        if lifecycle:
            result = [v for v in result if v.lifecycle == lifecycle]
        # 按创建时间降序
        result.sort(key=lambda v: v.created_at, reverse=True)
        return result

    def delete_version(self, version_id: str) -> bool:
        return self._versions.pop(version_id, None) is not None

    # ------------------------------------------------------------------
    # M4 新增：Family 管理
    # ------------------------------------------------------------------

    def list_families(self) -> List[str]:
        """列出所有模型族"""
        families = set(v.family for v in self._versions.values() if v.family)
        return sorted(families)

    def get_family(self, family: str) -> List[ModelVersion]:
        """获取指定族的所有版本（按版本号升序）"""
        versions = [v for v in self._versions.values() if v.family == family]
        versions.sort(key=lambda v: v.version_number)
        return versions

    def get_latest_in_family(self, family: str) -> Optional[ModelVersion]:
        """获取指定族的最新版本"""
        versions = self.get_family(family)
        if not versions:
            return None
        return versions[-1]

    def get_next_version_number(self, family: str) -> int:
        """获取下一个版本号"""
        versions = self.get_family(family)
        if not versions:
            return 1
        return max(v.version_number for v in versions) + 1

    # ------------------------------------------------------------------
    # M4 新增：Champion 管理
    # ------------------------------------------------------------------

    def set_champion(self, family: str, version_id: str) -> bool:
        """设置指定族的 Champion"""
        version = self._versions.get(version_id)
        if version is None or version.family != family:
            return False
        # 取消旧 Champion
        old_champion_id = self._champions.get(family)
        if old_champion_id and old_champion_id in self._versions:
            old = self._versions[old_champion_id]
            if old.lifecycle == LifecycleStatus.CHAMPION:
                old.lifecycle = LifecycleStatus.RETIRED
                old.retired_at = pd.Timestamp.now().isoformat()
        # 设置新 Champion
        self._champions[family] = version_id
        version.lifecycle = LifecycleStatus.CHAMPION
        version.promoted_at = pd.Timestamp.now().isoformat()
        logger.info(f"Champion set: {family} → {version.name}")
        return True

    def get_champion(self, family: str) -> Optional[ModelVersion]:
        """获取指定族的 Champion"""
        champion_id = self._champions.get(family)
        if champion_id is None:
            return None
        return self._versions.get(champion_id)

    def get_all_champions(self) -> Dict[str, ModelVersion]:
        """获取所有族的 Champion"""
        result = {}
        for family, vid in self._champions.items():
            v = self._versions.get(vid)
            if v:
                result[family] = v
        return result

    # ------------------------------------------------------------------
    # M4 新增：Lineage 查询
    # ------------------------------------------------------------------

    def get_lineage(self, version_id: str) -> List[ModelVersion]:
        """
        获取版本的血统链（从最早祖先到当前版本）

        返回：[v1, v2, v3, current]
        """
        chain: List[ModelVersion] = []
        visited = set()
        current = self._versions.get(version_id)
        while current and current.version_id not in visited:
            visited.add(current.version_id)
            chain.append(current)
            if current.parent_version_id:
                current = self._versions.get(current.parent_version_id)
            else:
                break
        chain.reverse()
        return chain

    def get_children(self, version_id: str) -> List[ModelVersion]:
        """获取直接子版本"""
        return [
            v for v in self._versions.values()
            if v.parent_version_id == version_id
        ]

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict:
        return {
            "total": len(self._versions),
            "families": self.list_families(),
            "n_champions": len(self._champions),
            "versions": [v.to_dict() for v in self.list_versions()],
        }

    def get_summary(self) -> pd.DataFrame:
        """获取模型版本摘要 DataFrame"""
        data = []
        for v in self.list_versions():
            data.append({
                "version_id": v.version_id,
                "name": v.name,
                "family": v.family,
                "version_number": v.version_number,
                "model_type": v.model_type.value,
                "dataset_id": v.dataset_id,
                "label_id": v.label_id,
                "n_features": len(v.feature_ids),
                "ic": v.metrics.get("ic", 0),
                "sharpe": v.metrics.get("sharpe", 0),
                "lifecycle": v.lifecycle.value,
                "is_champion": self._champions.get(v.family) == v.version_id,
                "created_at": v.created_at,
            })
        return pd.DataFrame(data)


_model_registry: Optional[ModelRegistry] = None


def get_model_registry() -> ModelRegistry:
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
