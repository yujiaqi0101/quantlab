"""
Materializer — 训练数据集实体化

将 Research Graph 的输出 + LabelNode 组装为 TrainingDataset (X, y)。

流程:
  1. Join: 把多个特征节点输出按 (datetime, symbol) 对齐
  2. Align: 与 LabelNode 输出对齐 (删除 NaN)
  3. Normalize: 可选归一化 (fit on train, apply to test)
  4. Split: 时序切分 (严格无未来信息泄漏)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .frame import ResearchFrame


@dataclass
class SplitConfig:
    """时序切分配置。"""
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    method: str = "time"  # "time" / "random" (不推荐)


@dataclass
class TrainingDataset:
    """训练数据集。"""
    X_train: pd.DataFrame
    y_train: pd.Series
    X_val: Optional[pd.DataFrame] = None
    y_val: Optional[pd.Series] = None
    X_test: Optional[pd.DataFrame] = None
    y_test: Optional[pd.Series] = None
    feature_names: List[str] = field(default_factory=list)
    label_name: str = ""
    normalize_params: Dict = field(default_factory=dict)


class Materializer:
    """训练数据集实体化器。"""

    def materialize(
        self,
        feature_frames: Dict[str, ResearchFrame],
        label_frame: ResearchFrame,
        split_config: Optional[SplitConfig] = None,
        normalize: bool = True,
    ) -> TrainingDataset:
        """实体化训练数据集。

        Args:
            feature_frames: {feature_name: ResearchFrame}
            label_frame: ResearchFrame (单列)
            split_config: 切分配置
            normalize: 是否归一化
        """
        split_config = split_config or SplitConfig()
        # 1. Join: 把所有特征按 (datetime, symbol) 对齐
        X = self._join_features(feature_frames)
        # 2. Align: 与 label 对齐
        label_col = label_frame.data.columns[0]
        y = label_frame.data[label_col]
        X, y = self._align(X, y)
        # 3. Split: 时序切分
        X_train, y_train, X_val, y_val, X_test, y_test = self._split(
            X, y, split_config
        )
        # 4. Normalize: fit on train, apply to val/test
        normalize_params = {}
        if normalize:
            X_train, X_val, X_test, normalize_params = self._normalize(
                X_train, X_val, X_test
            )
        return TrainingDataset(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            feature_names=list(X.columns),
            label_name=label_col,
            normalize_params=normalize_params,
        )

    def _join_features(self, frames: Dict[str, ResearchFrame]) -> pd.DataFrame:
        """把多个特征 frame 按 (datetime, symbol) join。"""
        if not frames:
            return pd.DataFrame()
        cols = {}
        for name, rf in frames.items():
            col_name = rf.data.columns[0]
            cols[name] = rf.data[col_name]
        return pd.DataFrame(cols)

    def _align(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """对齐 X 和 y，删除任一为 NaN 的行。"""
        # 确保 index 一致
        common_idx = X.index.intersection(y.index)
        X = X.loc[common_idx]
        y = y.loc[common_idx]
        # 删除 NaN
        mask = X.notna().all(axis=1) & y.notna()
        return X[mask], y[mask]

    def _split(
        self, X: pd.DataFrame, y: pd.Series, config: SplitConfig
    ) -> Tuple:
        """时序切分。"""
        if config.method == "random":
            # 随机切分 (不推荐用于时序)
            n = len(X)
            idx = np.random.permutation(n)
            n_train = int(n * config.train_ratio)
            n_val = int(n * config.val_ratio)
            train_idx = idx[:n_train]
            val_idx = idx[n_train : n_train + n_val]
            test_idx = idx[n_train + n_val :]
            return (
                X.iloc[train_idx], y.iloc[train_idx],
                X.iloc[val_idx], y.iloc[val_idx],
                X.iloc[test_idx], y.iloc[test_idx],
            )
        # 时序切分: 按 datetime 排序后切分
        X = X.sort_index(level="datetime")
        y = y.loc[X.index]
        # 按 datetime 分组
        dates = X.index.get_level_values("datetime").unique().sort_values()
        n_dates = len(dates)
        n_train = int(n_dates * config.train_ratio)
        n_val = int(n_dates * config.val_ratio)
        train_dates = dates[:n_train]
        val_dates = dates[n_train : n_train + n_val]
        test_dates = dates[n_train + n_val :]
        X_train = X[X.index.get_level_values("datetime").isin(train_dates)]
        y_train = y[y.index.get_level_values("datetime").isin(train_dates)]
        X_val = X[X.index.get_level_values("datetime").isin(val_dates)]
        y_val = y[y.index.get_level_values("datetime").isin(val_dates)]
        X_test = X[X.index.get_level_values("datetime").isin(test_dates)]
        y_test = y[y.index.get_level_values("datetime").isin(test_dates)]
        return X_train, y_train, X_val, y_val, X_test, y_test

    def _normalize(self, X_train, X_val, X_test):
        """Z-Score 归一化: fit on train, apply to val/test。"""
        mean = X_train.mean()
        std = X_train.std().replace(0, 1)
        X_train = (X_train - mean) / std
        if X_val is not None and len(X_val):
            X_val = (X_val - mean) / std
        if X_test is not None and len(X_test):
            X_test = (X_test - mean) / std
        params = {"mean": mean.to_dict(), "std": std.to_dict()}
        return X_train, X_val, X_test, params


__all__ = ["Materializer", "TrainingDataset", "SplitConfig"]
