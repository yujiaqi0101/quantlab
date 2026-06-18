"""
Training Center — 训练中心

ML Lab 第六部分：TrainingJob 记录与执行

  TrainingJob
    - dataset
    - feature_set
    - label
    - model
    - params
    - run()

  M2 第八部分：TrainingQueue 异步训练
    - Pending / Running / Completed / Failed
    - 同时训练多个模型
"""

from .job import TrainingJob, TrainingResult, TrainingStatus
from .manager import TrainingManager, get_training_manager
from .queue import TrainingQueue, QueueEntry, get_training_queue

__all__ = [
    "TrainingJob",
    "TrainingResult",
    "TrainingStatus",
    "TrainingManager",
    "get_training_manager",
    "TrainingQueue",
    "QueueEntry",
    "get_training_queue",
]
