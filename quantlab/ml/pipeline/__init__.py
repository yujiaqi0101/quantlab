"""
ML Data Pipeline — 数据流水线

ML Lab 第一层：统一数据流

  Dataset
      ↓
  FeatureSet  (compute)
      ↓
  LabelSet    (generate)
      ↓
  TrainingDataset
      - X: features DataFrame
      - y: label Series
      - metadata: 完整元信息

所有模型都吃 TrainingDataset 对象，避免散落的 DataFrame。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.pipeline")


@dataclass
class TrainingDataset:
    """
    训练数据集 — ML Lab 的统一数据容器

    所有模型、验证、搜索模块都接收此对象。

    用法：
        tds = TrainingDataset(
            X=features_df,
            y=label_series,
            metadata={
                "dataset_id": "crypto_1h",
                "feature_set_id": "momentum_v1",
                "label_set_id": "future_return_10",
            },
        )
    """
    X: pd.DataFrame
    y: pd.Series
    metadata: Dict[str, Any] = field(default_factory=dict)
    tds_id: str = field(default_factory=lambda: f"TDS-{uuid.uuid4().hex[:8]}")
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        # 对齐索引
        self._align()

    def _align(self) -> None:
        """对齐 X 和 y 的索引，丢弃 NaN"""
        if self.X is None or self.y is None:
            return
        common = self.X.index.intersection(self.y.index)
        self.X = self.X.loc[common].copy()
        self.y = self.y.loc[common].copy()

    # ------------------------------------------------------------------
    # 切分
    # ------------------------------------------------------------------

    def split(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> Dict[str, "TrainingDataset"]:
        """
        按时间顺序切分 train / val / test

        Returns:
            {"train": TrainingDataset, "val": TrainingDataset, "test": TrainingDataset}
        """
        n = len(self.X)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))

        meta = self.metadata.copy()
        return {
            "train": TrainingDataset(
                X=self.X.iloc[:train_end],
                y=self.y.iloc[:train_end],
                metadata={**meta, "split": "train"},
            ),
            "val": TrainingDataset(
                X=self.X.iloc[train_end:val_end],
                y=self.y.iloc[train_end:val_end],
                metadata={**meta, "split": "val"},
            ),
            "test": TrainingDataset(
                X=self.X.iloc[val_end:],
                y=self.y.iloc[val_end:],
                metadata={**meta, "split": "test"},
            ),
        }

    def split_by_date(
        self,
        train_end: str,
        val_end: Optional[str] = None,
    ) -> Dict[str, "TrainingDataset"]:
        """
        按日期切分（时间序列推荐）

        Args:
            train_end: 训练集结束日期（含）
            val_end: 验证集结束日期（含），若 None 则剩余全部作为 test
        """
        train_mask = self.X.index <= pd.Timestamp(train_end)
        if val_end:
            val_mask = (self.X.index > pd.Timestamp(train_end)) & (
                self.X.index <= pd.Timestamp(val_end)
            )
            test_mask = self.X.index > pd.Timestamp(val_end)
        else:
            val_mask = None
            test_mask = self.X.index > pd.Timestamp(train_end)

        meta = self.metadata.copy()
        result = {
            "train": TrainingDataset(
                X=self.X[train_mask],
                y=self.y[train_mask],
                metadata={**meta, "split": "train", "train_end": train_end},
            ),
        }
        if val_mask is not None:
            result["val"] = TrainingDataset(
                X=self.X[val_mask],
                y=self.y[val_mask],
                metadata={**meta, "split": "val", "train_end": train_end, "val_end": val_end},
            )
        result["test"] = TrainingDataset(
            X=self.X[test_mask],
            y=self.y[test_mask],
            metadata={**meta, "split": "test", "train_end": train_end, "val_end": val_end or ""},
        )
        return result

    # ------------------------------------------------------------------
    # 滚动窗口（供 Walk Forward 使用）
    # ------------------------------------------------------------------

    def rolling_windows(
        self,
        train_size: int,
        test_size: int,
        step_size: Optional[int] = None,
        gap: int = 0,
        max_splits: Optional[int] = None,
    ) -> List[Dict[str, "TrainingDataset"]]:
        """
        生成滚动窗口（Walk Forward 用）

        Args:
            train_size: 训练集样本数
            test_size: 测试集样本数
            step_size: 滚动步长，默认 = test_size
            gap: 训练集与测试集之间的间隔（避免标签泄漏）
            max_splits: 最大分片数
        """
        if step_size is None:
            step_size = test_size

        n = len(self.X)
        splits = []
        start = 0
        fold = 0

        while start + train_size + gap + test_size <= n:
            if max_splits is not None and fold >= max_splits:
                break

            train_end = start + train_size
            test_start = train_end + gap
            test_end = test_start + test_size

            meta = {**self.metadata, "fold": fold}
            splits.append({
                "train": TrainingDataset(
                    X=self.X.iloc[start:train_end],
                    y=self.y.iloc[start:train_end],
                    metadata={**meta, "split": "train"},
                ),
                "test": TrainingDataset(
                    X=self.X.iloc[test_start:test_end],
                    y=self.y.iloc[test_start:test_end],
                    metadata={**meta, "split": "test"},
                ),
            })

            start += step_size
            fold += 1

        return splits

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        """统计信息"""
        return {
            "tds_id": self.tds_id,
            "n_samples": len(self.X),
            "n_features": self.X.shape[1],
            "feature_names": list(self.X.columns),
            "start": str(self.X.index[0]) if len(self.X) > 0 else "",
            "end": str(self.X.index[-1]) if len(self.X) > 0 else "",
            "y_mean": float(self.y.mean()) if len(self.y) > 0 else 0.0,
            "y_std": float(self.y.std()) if len(self.y) > 0 else 0.0,
            "n_nan_X": int(self.X.isna().sum().sum()),
            "n_nan_y": int(self.y.isna().sum()),
            "metadata": self.metadata,
        }

    def dropna(self) -> "TrainingDataset":
        """丢弃任何含 NaN 的样本"""
        mask = ~(self.X.isna().any(axis=1) | self.y.isna())
        return TrainingDataset(
            X=self.X[mask].copy(),
            y=self.y[mask].copy(),
            metadata={**self.metadata, "dropna": True},
            tds_id=self.tds_id,
            created_at=self.created_at,
        )

    def __len__(self) -> int:
        return len(self.X)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tds_id": self.tds_id,
            "n_samples": len(self.X),
            "n_features": self.X.shape[1],
            "feature_names": list(self.X.columns),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ----------------------------------------------------------------------
# Pipeline 构建器
# ----------------------------------------------------------------------

class MLPipeline:
    """
    ML 数据流水线

    统一串联：Dataset → FeatureSet → LabelSet → TrainingDataset

    用法：
        pipeline = MLPipeline()
        tds = pipeline.build(
            dataset_id="crypto_1h",
            feature_set_id="momentum_v1",
            label_set_id="future_return_10",
        )
    """

    def __init__(self) -> None:
        # 延迟加载避免循环依赖
        self._dataset_manager = None
        self._feature_set_registry = None
        self._label_set_registry = None

    def _get_dataset_manager(self):
        if self._dataset_manager is None:
            from ..dataset import get_dataset_manager
            self._dataset_manager = get_dataset_manager()
        return self._dataset_manager

    def _get_feature_set_registry(self):
        if self._feature_set_registry is None:
            from ..feature import get_feature_set_registry
            self._feature_set_registry = get_feature_set_registry()
        return self._feature_set_registry

    def _get_label_set_registry(self):
        if self._label_set_registry is None:
            from ..label import get_label_set_registry
            self._label_set_registry = get_label_set_registry()
        return self._label_set_registry

    def build(
        self,
        dataset_id: str,
        feature_set_id: str,
        label_set_id: str,
        dropna: bool = True,
    ) -> TrainingDataset:
        """
        构建 TrainingDataset

        Args:
            dataset_id: 数据集 ID
            feature_set_id: FeatureSet ID
            label_set_id: LabelSet ID
            dropna: 是否丢弃 NaN 样本
        """
        # 1. 加载原始数据
        ds_mgr = self._get_dataset_manager()
        ds = ds_mgr.get_dataset(dataset_id)
        if not ds:
            raise ValueError(f"Dataset not found: {dataset_id}")
        df = ds.get_data()
        if df is None:
            raise ValueError(f"Dataset has no data: {dataset_id}")

        # 2. 计算 FeatureSet
        fs_reg = self._get_feature_set_registry()
        fs = fs_reg.get(feature_set_id)
        if fs is None:
            raise ValueError(f"FeatureSet not found: {feature_set_id}")
        X = fs.compute(df)

        # 3. 生成 LabelSet
        ls_reg = self._get_label_set_registry()
        ls = ls_reg.get(label_set_id)
        if ls is None:
            raise ValueError(f"LabelSet not found: {label_set_id}")
        y = ls.generate(df)

        # 4. 组装 TrainingDataset
        tds = TrainingDataset(
            X=X,
            y=y,
            metadata={
                "dataset_id": dataset_id,
                "feature_set_id": feature_set_id,
                "label_set_id": label_set_id,
                "feature_set_name": fs.name,
                "label_set_name": ls.name,
                "symbols": ds.symbols,
                "frequency": ds.frequency,
            },
        )

        if dropna:
            tds = tds.dropna()

        logger.info(
            f"Pipeline built TrainingDataset: "
            f"{len(tds)} samples, {tds.X.shape[1]} features"
        )
        return tds

    def build_from_raw(
        self,
        df: pd.DataFrame,
        feature_ids: List[str],
        label_id: str,
        dropna: bool = True,
    ) -> TrainingDataset:
        """从原始 DataFrame 构建（不依赖 Dataset/FeatureSet/LabelSet 注册表）"""
        from ..feature import get_feature_registry
        from ..label import get_label_registry

        feat_reg = get_feature_registry()
        label_reg = get_label_registry()

        X = feat_reg.compute_many(feature_ids, df)
        y = label_reg.generate(label_id, df)

        tds = TrainingDataset(
            X=X,
            y=y,
            metadata={
                "feature_ids": feature_ids,
                "label_id": label_id,
                "source": "raw",
            },
        )
        if dropna:
            tds = tds.dropna()
        return tds


_pipeline: Optional[MLPipeline] = None


def get_pipeline() -> MLPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = MLPipeline()
    return _pipeline
