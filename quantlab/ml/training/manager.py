"""
Training Manager — 训练管理器

ML Lab 第六部分：管理训练任务

  mgr = get_training_manager()
  result = mgr.submit(job)
  results = mgr.list_jobs()
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .job import TrainingJob, TrainingResult, TrainingStatus

logger = logging.getLogger("quantlab.ml.training.manager")


class TrainingManager:
    """训练管理器"""

    def __init__(self) -> None:
        self._jobs: Dict[str, TrainingJob] = {}
        self._results: Dict[str, TrainingResult] = {}

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
            else:
                job_dict["status"] = TrainingStatus.PENDING.value
                job_dict["metrics"] = None

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
