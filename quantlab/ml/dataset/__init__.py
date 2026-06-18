"""
Dataset Center — 数据集中心

ML Lab 第一部分：管理训练数据

  Dataset
    - dataset_id
    - name
    - symbols
    - start_date / end_date
    - frequency

  DatasetManager
    - 创建 / 查询 / 加载数据
    - 统计：样本量 / 缺失值 / 字段
"""

from .dataset import Dataset, DatasetStats, DatasetManager, get_dataset_manager

__all__ = [
    "Dataset",
    "DatasetStats",
    "DatasetManager",
    "get_dataset_manager",
]
