"""
Training Manager — 训练管理器

ML Lab 第六部分：管理训练任务

  mgr = get_training_manager()
  result = mgr.submit(job)
  results = mgr.list_jobs()

  M2 升级：启动时从 ExperimentTracker 恢复历史任务
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..experiment import ExperimentTracker, get_experiment_tracker
from ..model import ModelMetrics, ModelType
from .job import TrainingJob, TrainingResult, TrainingStatus

logger = logging.getLogger("quantlab.ml.training.manager")


def _metrics_from_dict(d: dict) -> ModelMetrics:
    """从 dict 构造 ModelMetrics"""
    return ModelMetrics(
        mae=d.get("mae", 0.0),
        mse=d.get("mse", 0.0),
        rmse=d.get("rmse", 0.0),
        r2=d.get("r2", 0.0),
        ic=d.get("ic", 0.0),
        rank_ic=d.get("rank_ic", 0.0),
        sharpe=d.get("sharpe", 0.0),
        accuracy=d.get("accuracy", 0.0),
        precision=d.get("precision", 0.0),
        recall=d.get("recall", 0.0),
        auc=d.get("auc", 0.0),
        n_samples=d.get("n_samples", 0),
        extra=d.get("extra", {}),
    )


class TrainingManager:
    """训练管理器"""

    def __init__(self) -> None:
        self._jobs: Dict[str, TrainingJob] = {}
        self._results: Dict[str, TrainingResult] = {}
        self._restore_from_experiments()

    def _restore_from_experiments(self) -> None:
        """从 ExperimentTracker 恢复历史任务"""
        try:
            tracker = get_experiment_tracker()
            exps = tracker.list_all()
            restored = 0
            for exp in exps:
                if not exp.job_id:
                    continue
                if exp.job_id in self._jobs:
                    continue  # 内存中已有，跳过
                self._restore_one(exp)
                restored += 1
            if restored:
                logger.info(f"TrainingManager restored {restored} jobs from ExperimentTracker")
        except Exception as e:
            logger.warning(f"Failed to restore jobs from experiments: {e}")

    def _restore_one(self, exp) -> None:
        """将单个 Experiment 恢复为 TrainingJob + TrainingResult"""
        # 恢复 TrainingJob
        try:
            model_type = ModelType(exp.model_type)
        except ValueError:
            model_type = ModelType.LIGHTGBM

        # 从 feature_importance_by_method 推断 methods
        fi_by_method = exp.feature_importance_by_method or {}
        if fi_by_method:
            methods = list(fi_by_method.keys())
        elif exp.feature_importance:
            methods = ["gain"]
        else:
            methods = ["gain"]

        job = TrainingJob(
            job_id=exp.job_id,
            name=exp.name,
            dataset_id=exp.dataset_id,
            feature_set_id=exp.feature_set_id,
            label_set_id=exp.label_set_id,
            model_type=model_type,
            model_params=exp.model_params,
            is_classifier=exp.is_classifier,
            methods=methods,
            tags=exp.tags,
            notes=exp.notes,
            created_at=exp.created_at,
        )
        self._jobs[exp.job_id] = job

        # 恢复 TrainingResult
        status = TrainingStatus.COMPLETED if exp.status == "COMPLETED" else TrainingStatus.FAILED
        result = TrainingResult(
            job_id=exp.job_id,
            status=status,
            metrics=_metrics_from_dict(exp.metrics) if exp.metrics else None,
            feature_importance=exp.feature_importance,
            feature_importance_by_method=fi_by_method,
            n_train_samples=exp.train_samples,
            n_test_samples=exp.test_samples,
            train_time=exp.train_time,
            completed_at=exp.created_at,
            experiment_id=exp.experiment_id,
        )
        self._results[exp.job_id] = result

    def submit(self, job: TrainingJob) -> TrainingResult:
        """提交并执行训练任务"""
        self._jobs[job.job_id] = job
        result = job.run()
        self._results[job.job_id] = result
        return result

    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        return self._jobs.get(job_id)

    def get_result(self, job_id: str) -> Optional[TrainingResult]:
        return self._results.get(job_id)

    def list_jobs(self, status: Optional[TrainingStatus] = None) -> List[Dict]:
        """列出所有训练任务"""
        results = []
        for job_id, job in self._jobs.items():
            result = self._results.get(job_id)
            job_dict = job.to_dict()
            if result:
                job_dict["status"] = result.status.value
                job_dict["metrics"] = result.metrics.to_dict() if result.metrics else None
                job_dict["feature_importance_by_method"] = result.feature_importance_by_method
            else:
                job_dict["status"] = TrainingStatus.PENDING.value
                job_dict["metrics"] = None
                job_dict["feature_importance_by_method"] = {}

            if status and job_dict["status"] != status.value:
                continue
            results.append(job_dict)
        return results

    def list_results(self, status: Optional[TrainingStatus] = None) -> List[TrainingResult]:
        """列出所有训练结果"""
        results = list(self._results.values())
        if status:
            results = [r for r in results if r.status == status]
        return results

    def get_status(self) -> Dict:
        """获取训练管理器状态"""
        all_results = list(self._results.values())
        return {
            "total": len(self._jobs),
            "completed": sum(1 for r in all_results if r.status == TrainingStatus.COMPLETED),
            "failed": sum(1 for r in all_results if r.status == TrainingStatus.FAILED),
            "running": sum(1 for r in all_results if r.status == TrainingStatus.RUNNING),
        }


_training_manager: Optional[TrainingManager] = None


def get_training_manager() -> TrainingManager:
    global _training_manager
    if _training_manager is None:
        _training_manager = TrainingManager()
    return _training_manager
