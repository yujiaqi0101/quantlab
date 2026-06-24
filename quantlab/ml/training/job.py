"""
Training Job — 训练任务（L4 升级版）

ML Lab 第四层：Training Job System

  支持两种模式：
    1. 传统模式：dataset_id + feature_ids + label_id
    2. 集合模式：dataset_id + feature_set_id + label_set_id（推荐）

  job = TrainingJob(
      dataset_id="crypto_1h",
      feature_set_id="momentum_v1",     # 使用 FeatureSet
      label_set_id="return_10d",        # 使用 LabelSet
      model_type=ModelType.LIGHTGBM,
      model_params={"n_estimators": 200},
  )
  result = job.run()

  训练完成后自动保存到 Experiment Tracker。
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..dataset import DatasetManager, get_dataset_manager
from ..feature import FeatureRegistry, get_feature_registry, FeatureSetRegistry, get_feature_set_registry
from ..label import LabelRegistry, get_label_registry, LabelSetRegistry, get_label_set_registry
from ..model import Model, ModelType, ModelMetrics, create_model
from ..pipeline import TrainingDataset, MLPipeline, get_pipeline
from ..experiment import Experiment, get_experiment_tracker
from ..feature_analysis import FeatureImportanceAnalyzer

logger = logging.getLogger("quantlab.ml.training")


class TrainingStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class TrainingResult:
    """训练结果"""
    job_id: str = ""
    status: TrainingStatus = TrainingStatus.PENDING
    metrics: Optional[ModelMetrics] = None
    feature_importance: Dict[str, float] = field(default_factory=dict)
    feature_importance_by_method: Dict[str, Dict[str, float]] = field(default_factory=dict)
    n_train_samples: int = 0
    n_test_samples: int = 0
    train_time: float = 0.0
    error: str = ""
    model: Optional[Model] = None
    completed_at: str = ""
    experiment_id: str = ""              # 关联的实验 ID

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "feature_importance": self.feature_importance,
            "feature_importance_by_method": self.feature_importance_by_method,
            "n_train_samples": self.n_train_samples,
            "n_test_samples": self.n_test_samples,
            "train_time": round(self.train_time, 4),
            "error": self.error,
            "completed_at": self.completed_at,
            "experiment_id": self.experiment_id,
        }


@dataclass
class TrainingJob:
    """
    训练任务（L4 升级版）

    支持两种模式：
      模式1（传统）：dataset_id + feature_ids + label_id
      模式2（集合，推荐）：dataset_id + feature_set_id + label_set_id

    用法：
        job = TrainingJob(
            dataset_id="DS-xxx",
            feature_set_id="momentum_v1",
            label_set_id="return_10d",
            model_type=ModelType.LIGHTGBM,
            model_params={"n_estimators": 200},
        )
        result = job.run()
    """
    job_id: str = field(default_factory=lambda: f"JOB-{uuid.uuid4().hex[:8]}")
    dataset_id: str = ""

    # 模式1：传统
    feature_ids: List[str] = field(default_factory=list)
    label_id: str = ""

    # 模式2：集合（推荐）
    feature_set_id: str = ""
    label_set_id: str = ""

    # 模型
    model_type: ModelType = ModelType.LIGHTGBM
    model_params: Dict[str, Any] = field(default_factory=dict)
    is_classifier: bool = False

    # 切分
    train_ratio: float = 0.7
    val_ratio: float = 0.15

    # 特征重要性方法（gain / permutation / shap），默认 gain
    methods: List[str] = field(default_factory=lambda: ["gain"])

    # 元信息
    name: str = ""
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""

    # 是否自动保存实验
    save_experiment: bool = True

    # 依赖注入（可选）
    _pipeline: Optional[MLPipeline] = None
    _experiment_tracker = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.name:
            self.name = f"{self.model_type.value}_{self.job_id[-4:]}"

    def to_dict(self) -> Dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "dataset_id": self.dataset_id,
            "feature_ids": self.feature_ids,
            "label_id": self.label_id,
            "feature_set_id": self.feature_set_id,
            "label_set_id": self.label_set_id,
            "model_type": self.model_type.value,
            "model_params": self.model_params,
            "is_classifier": self.is_classifier,
            "train_ratio": self.train_ratio,
            "val_ratio": self.val_ratio,
            "methods": self.methods,
            "tags": self.tags,
            "notes": self.notes,
            "created_at": self.created_at,
        }

    def _build_training_dataset(self) -> TrainingDataset:
        """构建 TrainingDataset"""
        pipeline = self._pipeline or get_pipeline()

        if self.feature_set_id and self.label_set_id:
            # 模式2：使用 FeatureSet + LabelSet
            return pipeline.build(
                dataset_id=self.dataset_id,
                feature_set_id=self.feature_set_id,
                label_set_id=self.label_set_id,
            )
        elif self.feature_ids and self.label_id:
            # 模式1：传统
            return pipeline.build_from_raw(
                df=self._load_raw_df(),
                feature_ids=self.feature_ids,
                label_id=self.label_id,
            )
        else:
            raise ValueError(
                "Must specify either (feature_set_id + label_set_id) "
                "or (feature_ids + label_id)"
            )

    def _load_raw_df(self) -> pd.DataFrame:
        """加载原始数据（模式1用）"""
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(self.dataset_id)
        if not ds:
            raise ValueError(f"Dataset not found: {self.dataset_id}")
        df = ds.get_data()
        if df is None:
            raise ValueError(f"Dataset has no data: {self.dataset_id}")
        return df

    def run(self) -> TrainingResult:
        """执行训练"""
        result = TrainingResult(job_id=self.job_id, status=TrainingStatus.RUNNING)
        start = time.time()

        try:
            # 1. 构建 TrainingDataset
            tds = self._build_training_dataset()
            if len(tds) == 0:
                raise ValueError("TrainingDataset is empty after dropna")

            # 2. 切分
            splits = tds.split(train_ratio=self.train_ratio, val_ratio=self.val_ratio)
            X_train, y_train = splits["train"].X, splits["train"].y
            X_val, y_val = splits["val"].X, splits["val"].y
            X_test, y_test = splits["test"].X, splits["test"].y

            # 3. 创建并训练模型
            model = create_model(
                model_type=self.model_type,
                params=self.model_params,
                is_classifier=self.is_classifier,
            )
            model.fit(X_train, y_train)

            # 4. 评估
            val_metrics = model.evaluate(X_val, y_val) if len(X_val) > 0 else ModelMetrics()
            test_metrics = model.evaluate(X_test, y_test) if len(X_test) > 0 else ModelMetrics()

            # 5. 特征重要性（按 methods 计算）
            methods = self.methods if self.methods else ["gain"]
            analyzer = FeatureImportanceAnalyzer()
            analysis = analyzer.analyze(model, X=X_test, y=y_test, methods=methods)

            # 按方法存储：{method: {feature: importance}}
            fi_by_method: Dict[str, Dict[str, float]] = {}
            for method_name, imp_result in analysis.items():
                fi_by_method[method_name] = {
                    imp_result.feature_names[i]: float(imp_result.importances[i])
                    for i in range(len(imp_result.feature_names))
                }

            # 兼容老字段：feature_importance 默认存 gain
            fi_dict = fi_by_method.get("gain", {})
            if not fi_dict and fi_by_method:
                # 没有 gain 时取第一个方法
                first_method = next(iter(fi_by_method))
                fi_dict = fi_by_method[first_method]

            result.status = TrainingStatus.COMPLETED
            result.metrics = test_metrics
            result.feature_importance = fi_dict
            result.feature_importance_by_method = fi_by_method
            result.n_train_samples = len(X_train)
            result.n_test_samples = len(X_test)
            result.train_time = time.time() - start
            result.model = model
            result.completed_at = pd.Timestamp.now().isoformat()

            # 6. 保存实验
            if self.save_experiment:
                exp = Experiment(
                    name=self.name,
                    dataset_id=self.dataset_id,
                    feature_set_id=self.feature_set_id,
                    label_set_id=self.label_set_id,
                    model_type=self.model_type.value,
                    model_params=self.model_params,
                    is_classifier=self.is_classifier,
                    metrics=test_metrics.to_dict(),
                    feature_importance=fi_dict,
                    feature_importance_by_method=fi_by_method,
                    train_samples=len(X_train),
                    test_samples=len(X_test),
                    train_time=result.train_time,
                    status="COMPLETED",
                    tags=self.tags,
                    notes=self.notes,
                    job_id=self.job_id,
                )
                tracker = self._experiment_tracker or get_experiment_tracker()
                tracker.save(exp)
                result.experiment_id = exp.experiment_id

            logger.info(
                f"Training {self.job_id} completed: "
                f"train={len(X_train)}, test={len(X_test)}, "
                f"IC={test_metrics.ic:.4f}, time={result.train_time:.2f}s, "
                f"exp={result.experiment_id}"
            )

        except Exception as e:
            result.status = TrainingStatus.FAILED
            result.error = str(e)
            result.train_time = time.time() - start
            logger.error(f"Training {self.job_id} failed: {e}", exc_info=True)

            # 失败也记录实验
            if self.save_experiment:
                exp = Experiment(
                    name=self.name,
                    dataset_id=self.dataset_id,
                    feature_set_id=self.feature_set_id,
                    label_set_id=self.label_set_id,
                    model_type=self.model_type.value,
                    model_params=self.model_params,
                    is_classifier=self.is_classifier,
                    status="FAILED",
                    tags=self.tags,
                    notes=self.notes,
                    job_id=self.job_id,
                )
                tracker = self._experiment_tracker or get_experiment_tracker()
                tracker.save(exp)
                result.experiment_id = exp.experiment_id

        return result
