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
    model_version_id: str = ""           # 关联的 Raw Model 版本 ID（持久化到 ModelStore）

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
            "model_version_id": self.model_version_id,
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

    模式3（Graph，新体系推荐）：
        job = TrainingJob(
            dataset_id="DS-xxx",
            research_graph=g,                 # ResearchGraph 实例
            label_node_id="future_return",    # LabelNode id
            materialize_config={"normalize": True, "train_ratio": 0.7},
            model_type=ModelType.LIGHTGBM,
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

    # 模式3：Graph（新体系，推荐）
    research_graph: Optional[Any] = None  # ResearchGraph 实例
    label_node_id: str = ""
    materialize_config: Dict[str, Any] = field(default_factory=dict)
    feature_node_ids: List[str] = field(default_factory=list)  # 为空=自动选图内非 label 节点

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
        # 模式3: Graph (新体系)
        if self.research_graph is not None:
            return self._build_from_graph()

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
                "or (feature_ids + label_id) "
                "or (research_graph + label_node_id)"
            )

    def _build_from_graph(self) -> TrainingDataset:
        """模式3: 用 ResearchGraph + Materializer 构建训练数据集。"""
        import pandas as pd
        from ...research.context import ExecutionContext
        from ...research.executor import ResearchExecutor
        from ...research.materializer import Materializer, SplitConfig
        from ...research import ResearchFrame

        # 1. 加载原始数据
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.get_dataset(self.dataset_id)
        if not ds:
            raise ValueError(f"Dataset not found: {self.dataset_id}")
        df = ds.get_data()
        if df is None:
            raise ValueError(f"Dataset has no data: {self.dataset_id}")

        # 2. 执行图
        ex_ctx = ExecutionContext()
        ex_ctx.set("frame", ResearchFrame.from_panel(df))
        ex = ResearchExecutor()
        result = ex.execute(self.research_graph, initial_store=ex_ctx.frame_store)

        # 3. 提取特征 + 标签
        feature_frames = {}
        all_node_ids = self.research_graph.node_ids()
        for nid in all_node_ids:
            if nid == self.label_node_id:
                continue
            if self.feature_node_ids and nid not in self.feature_node_ids:
                continue
            rf = result.get(nid)
            if rf is not None:
                feature_frames[nid] = rf

        if self.label_node_id not in all_node_ids:
            raise ValueError(
                f"label_node_id '{self.label_node_id}' not in graph"
            )
        label_frame = result.get(self.label_node_id)
        if label_frame is None:
            raise ValueError(
                f"label node '{self.label_node_id}' produced no output"
            )

        # 4. Materializer 实体化
        mat = Materializer()
        config = self.materialize_config or {}
        split_config = SplitConfig(
            train_ratio=config.get("train_ratio", self.train_ratio),
            val_ratio=config.get("val_ratio", self.val_ratio),
            test_ratio=config.get("test_ratio", 1.0 - self.train_ratio - self.val_ratio),
            method="time",
        )
        normalize = config.get("normalize", True)
        gtds = mat.materialize(
            feature_frames=feature_frames,
            label_frame=label_frame,
            split_config=split_config,
            normalize=normalize,
        )

        # 5. 转换为旧 TrainingDataset 接口 (兼容下游 model.fit)
        return self._convert_graph_td_to_legacy(gtds)

    def _convert_graph_td_to_legacy(self, gtds):
        """把 Graph 体系的 TrainingDataset 转换为旧 MLPipeline 的 TrainingDataset。

        旧 TD 只有 X/y/metadata，且 split() 自己再切。
        新 Graph TD 已经切好，所以把 train+val+test 拼回一个 TD，
        再用 split() 切一次会得到错误结果。
        策略: 直接返回合并后的 TD (train+val 合并为 train，test 独立)，
        并把已切分的 X_test/y_test 挂到 metadata 供 run() 直接取用。
        """
        from ..pipeline import TrainingDataset as LegacyTD
        import pandas as pd

        # 合并 X_train + X_val 作为新的 X (供 LegacyTD.split 再切)
        if gtds.X_val is not None and len(gtds.X_val):
            X_merged = pd.concat([gtds.X_train, gtds.X_val])
            y_merged = pd.concat([gtds.y_train, gtds.y_val])
            # 排序保证时序
            if isinstance(X_merged.index, pd.MultiIndex):
                X_merged = X_merged.sort_index()
                y_merged = y_merged.loc[X_merged.index]
        else:
            X_merged = gtds.X_train
            y_merged = gtds.y_train

        legacy = LegacyTD(
            X=X_merged,
            y=y_merged,
            metadata={
                "dataset_id": self.dataset_id,
                "feature_names": gtds.feature_names,
                "label_name": gtds.label_name,
                "mode": "graph",
                "normalize_params": gtds.normalize_params,
                "_graph_test_X": gtds.X_test,
                "_graph_test_y": gtds.y_test,
            },
        )
        return legacy

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

            # 2. 切分 (Graph 模式已切分，直接取用)
            if self.research_graph is not None:
                X_train = tds.X
                y_train = tds.y
                X_val = X_train.iloc[:0]  # Graph 模式 val 已合并到 train
                y_val = y_train.iloc[:0]
                X_test = tds.metadata.get("_graph_test_X")
                y_test = tds.metadata.get("_graph_test_y")
            else:
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

            # 6. 持久化 Raw Model（状态=DRAFT，未验证的裸模型）
            # Training Center 产出 = Raw Model + Experiment
            # Validation Pipeline 的输入 = Experiment ID → 加载 Raw Model
            try:
                from ..registry import ModelVersion, LifecycleStatus
                from ..registry.model_store import get_model_store

                family = f"{self.model_type.value}_{self.name}"
                store = get_model_store()
                # 计算下一个版本号（扫描文件系统已有版本）
                existing = store.list_files(family)
                next_vn = max(
                    [f["version_number"] for f in existing],
                    default=0,
                ) + 1

                raw_version = ModelVersion(
                    name=f"{family}_v{next_vn}",
                    model_type=self.model_type,
                    params=self.model_params,
                    metrics=test_metrics.to_dict(),
                    dataset_id=self.dataset_id,
                    feature_ids=self.feature_ids,
                    label_id=self.label_id,
                    is_classifier=self.is_classifier,
                    family=family,
                    version_number=next_vn,
                    lifecycle=LifecycleStatus.DRAFT,
                    tags=self.tags + ["raw_model"],
                    description=f"Raw model from training job {self.job_id}",
                )
                raw_version.set_model(model)
                store.save(raw_version)
                result.model_version_id = raw_version.version_id
                logger.info(
                    f"Raw Model persisted: {raw_version.version_id} "
                    f"({raw_version.name}, family={family}, DRAFT)"
                )
            except Exception as e:
                logger.error(f"Failed to persist Raw Model: {e}", exc_info=True)
                # 持久化失败不阻断训练流程，但标记 model_version_id 为空

            # 7. 保存实验
            if self.save_experiment:
                exp = Experiment(
                    name=self.name,
                    dataset_id=self.dataset_id,
                    feature_set_id=self.feature_set_id,
                    label_set_id=self.label_set_id,
                    feature_ids=self.feature_ids,
                    label_id=self.label_id,
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
                    model_version_id=result.model_version_id,
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
                    feature_ids=self.feature_ids,
                    label_id=self.label_id,
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
