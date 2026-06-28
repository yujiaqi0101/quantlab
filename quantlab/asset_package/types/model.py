"""
Model Package — 模型包

封装机器学习模型，供策略工作室引用和组合。

内置实现（示例/模板）：
  - TrainedModel: 引用已训练的模型（通过 model_id 关联 ML Lab）
  - LinearModel: 线性模型配置模板
  - TreeModel: 树模型（LightGBM/XGBoost）配置模板
  - EnsembleModel: 集成模型配置模板
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..base import AssetPackage, PackageType

logger = logging.getLogger("quantlab.asset_package.types.model")


class ModelFramework(str, Enum):
    """模型框架"""
    SCIKIT_LEARN = "sklearn"
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    PYTORCH = "pytorch"
    CUSTOM = "custom"


class ModelTask(str, Enum):
    """模型任务类型"""
    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    RANKING = "ranking"


@dataclass
class ModelPackage(AssetPackage):
    """模型包基类"""
    package_type: PackageType = PackageType.MODEL

    framework: ModelFramework = ModelFramework.CUSTOM
    task: ModelTask = ModelTask.REGRESSION
    model_id: str = ""
    features: List[str] = field(default_factory=list)
    label: str = ""
    hyperparams: Dict[str, Any] = field(default_factory=dict)

    def predict(self, data: Any) -> Any:
        raise NotImplementedError("Subclass must implement predict()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            "framework": self.framework.value,
            "task": self.task.value,
            "model_id": self.model_id,
            "features": sorted(self.features),
            "label": self.label,
            **self.to_config(),
        })

    def _load_config(self, config: Dict[str, Any]) -> None:
        fw = config.get("framework", "custom")
        try:
            self.framework = ModelFramework(fw)
        except ValueError:
            self.framework = ModelFramework.CUSTOM
        tk = config.get("task", "regression")
        try:
            self.task = ModelTask(tk)
        except ValueError:
            self.task = ModelTask.REGRESSION
        self.model_id = config.get("model_id", "")
        self.features = config.get("features", [])
        self.label = config.get("label", "")
        self.hyperparams = config.get("hyperparams", {})


# ==================================================================
# 1. TrainedModel — 引用已训练模型
# ==================================================================

@dataclass
class TrainedModel(ModelPackage):
    """
    引用 ML Lab 中已训练完成的模型
    
    model_id 关联 ML Lab 的实验/模型记录
    """
    experiment_id: str = ""

    def to_config(self) -> Dict[str, Any]:
        return {
            "framework": self.framework.value,
            "task": self.task.value,
            "model_id": self.model_id,
            "experiment_id": self.experiment_id,
            "features": self.features,
            "label": self.label,
            "hyperparams": self.hyperparams,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        self.experiment_id = config.get("experiment_id", "")

    def predict(self, data: Any) -> Any:
        raise NotImplementedError("TrainedModel.predict() requires runtime model loading")


# ==================================================================
# 2. LinearModel — 线性模型模板
# ==================================================================

@dataclass
class LinearModel(ModelPackage):
    """线性模型（Ridge/Lasso/LogisticRegression）配置模板"""
    linear_type: str = "ridge"
    alpha: float = 1.0
    fit_intercept: bool = True
    normalize: bool = False

    def __post_init__(self):
        if not self.framework or self.framework == ModelFramework.CUSTOM:
            self.framework = ModelFramework.SCIKIT_LEARN
        super().__post_init__()

    def to_config(self) -> Dict[str, Any]:
        return {
            "framework": self.framework.value,
            "task": self.task.value,
            "model_id": self.model_id,
            "features": self.features,
            "label": self.label,
            "hyperparams": {
                "linear_type": self.linear_type,
                "alpha": self.alpha,
                "fit_intercept": self.fit_intercept,
                "normalize": self.normalize,
                **self.hyperparams,
            },
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        hp = config.get("hyperparams", {})
        self.linear_type = hp.get("linear_type", "ridge")
        self.alpha = hp.get("alpha", 1.0)
        self.fit_intercept = hp.get("fit_intercept", True)
        self.normalize = hp.get("normalize", False)

    def predict(self, data: Any) -> Any:
        raise NotImplementedError("LinearModel requires training before prediction")


# ==================================================================
# 3. TreeModel — 树模型模板
# ==================================================================

@dataclass
class TreeModel(ModelPackage):
    """树模型（LightGBM/XGBoost）配置模板"""
    tree_type: str = "lightgbm"
    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    num_leaves: int = 31

    def __post_init__(self):
        if not self.framework or self.framework == ModelFramework.CUSTOM:
            if self.tree_type == "xgboost":
                self.framework = ModelFramework.XGBOOST
            else:
                self.framework = ModelFramework.LIGHTGBM
        super().__post_init__()

    def to_config(self) -> Dict[str, Any]:
        return {
            "framework": self.framework.value,
            "task": self.task.value,
            "model_id": self.model_id,
            "features": self.features,
            "label": self.label,
            "hyperparams": {
                "tree_type": self.tree_type,
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "subsample": self.subsample,
                "colsample_bytree": self.colsample_bytree,
                "num_leaves": self.num_leaves,
                **self.hyperparams,
            },
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        hp = config.get("hyperparams", {})
        self.tree_type = hp.get("tree_type", "lightgbm")
        self.n_estimators = hp.get("n_estimators", 200)
        self.max_depth = hp.get("max_depth", 6)
        self.learning_rate = hp.get("learning_rate", 0.05)
        self.subsample = hp.get("subsample", 0.8)
        self.colsample_bytree = hp.get("colsample_bytree", 0.8)
        self.num_leaves = hp.get("num_leaves", 31)

    def predict(self, data: Any) -> Any:
        raise NotImplementedError("TreeModel requires training before prediction")


# ==================================================================
# 4. EnsembleModel — 集成模型模板
# ==================================================================

@dataclass
class EnsembleModel(ModelPackage):
    """集成模型（多模型投票/堆叠）配置模板"""
    ensemble_type: str = "voting"
    member_refs: List[str] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)

    def to_config(self) -> Dict[str, Any]:
        return {
            "framework": self.framework.value,
            "task": self.task.value,
            "model_id": self.model_id,
            "features": self.features,
            "label": self.label,
            "hyperparams": {
                "ensemble_type": self.ensemble_type,
                "member_refs": self.member_refs,
                "weights": self.weights,
                **self.hyperparams,
            },
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        super()._load_config(config)
        hp = config.get("hyperparams", {})
        self.ensemble_type = hp.get("ensemble_type", "voting")
        self.member_refs = hp.get("member_refs", [])
        self.weights = hp.get("weights", [])

    def predict(self, data: Any) -> Any:
        raise NotImplementedError("EnsembleModel requires member models for prediction")
