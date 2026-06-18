"""
Training Queue — 训练队列

ML Lab M2 第八部分：不要同步训练

  TrainingQueue 支持：
    - Pending    等待执行
    - Running    正在训练
    - Completed  训练完成
    - Failed     训练失败

  以后同时训练多个模型很方便。

  用法：
      queue = get_training_queue()
      job_id = queue.submit(job)       # 异步提交，立即返回
      status = queue.get_status(job_id)  # 查询状态
      result = queue.get_result(job_id)  # 获取结果（阻塞或非阻塞）
      queue.wait(job_id)                # 等待完成
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .job import TrainingJob, TrainingResult, TrainingStatus

logger = logging.getLogger("quantlab.ml.training.queue")


@dataclass
class QueueEntry:
    """队列条目"""
    job_id: str
    job: TrainingJob
    status: TrainingStatus = TrainingStatus.PENDING
    result: Optional[TrainingResult] = None
    future: Optional[Future] = None
    submitted_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "metrics": self.result.metrics.to_dict() if self.result and self.result.metrics else None,
            "experiment_id": self.result.experiment_id if self.result else "",
        }


class TrainingQueue:
    """
    训练队列（异步执行）

    用法：
        queue = get_training_queue()
        job_id = queue.submit(job)
        # 做其他事...
        result = queue.wait(job_id)
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._entries: Dict[str, QueueEntry] = {}
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="training-queue",
        )
        self._max_workers = max_workers

    def submit(self, job: TrainingJob) -> str:
        """
        提交训练任务（异步，立即返回 job_id）

        Args:
            job: 训练任务

        Returns:
            job_id
        """
        if not job.job_id:
            job.job_id = f"JOB-{uuid.uuid4().hex[:8]}"

        import pandas as pd
        entry = QueueEntry(
            job_id=job.job_id,
            job=job,
            status=TrainingStatus.PENDING,
            submitted_at=pd.Timestamp.now().isoformat(),
        )

        with self._lock:
            self._entries[job.job_id] = entry

        # 提交到线程池
        entry.future = self._executor.submit(self._run_job, job.job_id)
        logger.info(f"Training job submitted: {job.job_id} (queue size: {self.size()})")
        return job.job_id

    def _run_job(self, job_id: str) -> None:
        """线程池中执行训练"""
        import pandas as pd
        with self._lock:
            entry = self._entries.get(job_id)
            if not entry:
                logger.error(f"Job not found: {job_id}")
                return
            entry.status = TrainingStatus.RUNNING
            entry.started_at = pd.Timestamp.now().isoformat()

        logger.info(f"Training job started: {job_id}")
        try:
            result = entry.job.run()
            with self._lock:
                entry.result = result
                entry.status = result.status
                entry.completed_at = pd.Timestamp.now().isoformat()
            logger.info(
                f"Training job completed: {job_id} "
                f"status={result.status.value}"
            )
        except Exception as e:
            logger.error(f"Training job failed: {job_id} - {e}", exc_info=True)
            with self._lock:
                entry.status = TrainingStatus.FAILED
                entry.error = str(e)
                entry.completed_at = pd.Timestamp.now().isoformat()
                entry.result = TrainingResult(
                    job_id=job_id,
                    status=TrainingStatus.FAILED,
                    error=str(e),
                )

    def get_status(self, job_id: str) -> Optional[TrainingStatus]:
        """获取任务状态"""
        with self._lock:
            entry = self._entries.get(job_id)
            return entry.status if entry else None

    def get_entry(self, job_id: str) -> Optional[QueueEntry]:
        """获取队列条目"""
        with self._lock:
            return self._entries.get(job_id)

    def get_result(self, job_id: str) -> Optional[TrainingResult]:
        """获取训练结果（非阻塞，未完成返回 None）"""
        with self._lock:
            entry = self._entries.get(job_id)
            return entry.result if entry else None

    def wait(self, job_id: str, timeout: Optional[float] = None) -> Optional[TrainingResult]:
        """
        等待任务完成并返回结果

        Args:
            job_id: 任务 ID
            timeout: 超时时间（秒），None 表示无限等待

        Returns:
            TrainingResult
        """
        with self._lock:
            entry = self._entries.get(job_id)
        if not entry:
            return None
        if entry.future is not None:
            try:
                entry.future.result(timeout=timeout)
            except Exception as e:
                logger.warning(f"Wait for {job_id} raised: {e}")
        with self._lock:
            return entry.result

    def cancel(self, job_id: str) -> bool:
        """取消任务（仅 Pending 状态可取消）"""
        with self._lock:
            entry = self._entries.get(job_id)
            if not entry:
                return False
            if entry.status != TrainingStatus.PENDING:
                return False
            if entry.future and entry.future.cancel():
                entry.status = TrainingStatus.FAILED
                entry.error = "Cancelled"
                return True
            return False

    def list_jobs(
        self,
        status: Optional[TrainingStatus] = None,
    ) -> List[Dict[str, Any]]:
        """列出所有任务"""
        with self._lock:
            entries = list(self._entries.values())
        result = [e.to_dict() for e in entries]
        if status:
            result = [r for r in result if r["status"] == status.value]
        # 按提交时间降序
        result.sort(key=lambda x: x.get("submitted_at", ""), reverse=True)
        return result

    def size(self) -> int:
        """队列总大小"""
        with self._lock:
            return len(self._entries)

    def get_queue_status(self) -> Dict[str, int]:
        """获取队列状态统计"""
        with self._lock:
            entries = list(self._entries.values())
        return {
            "total": len(entries),
            "pending": sum(1 for e in entries if e.status == TrainingStatus.PENDING),
            "running": sum(1 for e in entries if e.status == TrainingStatus.RUNNING),
            "completed": sum(1 for e in entries if e.status == TrainingStatus.COMPLETED),
            "failed": sum(1 for e in entries if e.status == TrainingStatus.FAILED),
        }

    def clear_completed(self) -> int:
        """清理已完成/失败的任务"""
        with self._lock:
            to_remove = [
                jid for jid, e in self._entries.items()
                if e.status in (TrainingStatus.COMPLETED, TrainingStatus.FAILED)
            ]
            for jid in to_remove:
                self._entries.pop(jid, None)
        logger.info(f"Cleared {len(to_remove)} completed/failed jobs")
        return len(to_remove)

    def shutdown(self, wait: bool = True) -> None:
        """关闭队列（等待所有任务完成）"""
        logger.info("Shutting down training queue...")
        self._executor.shutdown(wait=wait)


# 单例
_training_queue: Optional[TrainingQueue] = None
_queue_lock = threading.Lock()


def get_training_queue(max_workers: int = 2) -> TrainingQueue:
    """
    获取 TrainingQueue 单例

    Args:
        max_workers: 最大并发训练数（仅首次创建时生效）
    """
    global _training_queue
    if _training_queue is None:
        with _queue_lock:
            if _training_queue is None:
                _training_queue = TrainingQueue(max_workers=max_workers)
    return _training_queue
