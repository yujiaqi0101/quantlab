"""
Walk Forward — 滚动验证（L7 升级版）

ML Lab 第七层：量化必须的验证方式

  流程：
    训练 2020-2022 → 验证 2023 → 测试 2024
    滚动：2020-2023 → 验证 2024

  WalkForward
    - config: ValidationConfig
    - run(features, label, model_factory) → WalkForwardResult
    - run_tds(tds) → WalkForwardResult  # 新增：直接接收 TrainingDataset

  这一层的重要性：大于任何模型
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from ..model import Model, ModelMetrics, create_model, ModelType
from ..pipeline import TrainingDataset

logger = logging.getLogger("quantlab.ml.validation")


@dataclass
class ValidationConfig:
    """验证配置"""
    n_splits: int = 5              # 滚动次数
    train_size: int = 252          # 训练集大小（天数）
    test_size: int = 63            # 测试集大小（天数）
    step_size: int = 63            # 滚动步长（天数）
    gap: int = 0                   # 训练集和测试集之间的间隔（避免标签泄漏）

    def to_dict(self) -> Dict:
        return {
            "n_splits": self.n_splits,
            "train_size": self.train_size,
            "test_size": self.test_size,
            "step_size": self.step_size,
            "gap": self.gap,
        }


@dataclass
class WalkForwardResult:
    """Walk Forward 结果"""
    n_splits: int = 0
    metrics_per_fold: List[ModelMetrics] = field(default_factory=list)
    avg_ic: float = 0.0
    avg_rank_ic: float = 0.0
    avg_rmse: float = 0.0
    avg_sharpe: float = 0.0           # M3 新增：平均夏普
    avg_return: float = 0.0           # M3 新增：平均收益（信号加权）
    ic_stability: float = 0.0       # IC 稳定性 = mean / std
    predictions: Optional[pd.Series] = None
    fold_details: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "n_splits": self.n_splits,
            "metrics_per_fold": [m.to_dict() for m in self.metrics_per_fold],
            "avg_ic": round(self.avg_ic, 6),
            "avg_rank_ic": round(self.avg_rank_ic, 6),
            "avg_rmse": round(self.avg_rmse, 6),
            "avg_sharpe": round(self.avg_sharpe, 6),
            "avg_return": round(self.avg_return, 6),
            "ic_stability": round(self.ic_stability, 6),
            "fold_details": self.fold_details,
        }


class WalkForward:
    """
    Walk Forward 滚动验证（L7 升级版）

    用法1（传统）：
        config = ValidationConfig(n_splits=5, train_size=252, test_size=63)
        wf = WalkForward(config)
        result = wf.run(
            features=features_df,
            label=label_series,
            model_type=ModelType.LIGHTGBM,
        )

    用法2（推荐，使用 TrainingDataset）：
        result = wf.run_tds(tds, model_type=ModelType.LIGHTGBM)
    """

    def __init__(self, config: ValidationConfig = ValidationConfig()) -> None:
        self.config = config

    def run(
        self,
        features: pd.DataFrame,
        label: pd.Series,
        model_type: ModelType,
        model_params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> WalkForwardResult:
        """执行 Walk Forward 验证（传统接口）"""
        # 对齐索引
        common_idx = features.index.intersection(label.index)
        features = features.loc[common_idx].copy()
        label = label.loc[common_idx].copy()

        n = len(features)
        result = WalkForwardResult(n_splits=0)

        all_predictions = []
        fold_details = []
        metrics_list: List[ModelMetrics] = []

        train_size = self.config.train_size
        test_size = self.config.test_size
        step_size = self.config.step_size
        gap = self.config.gap

        # 生成滚动窗口
        start = 0
        fold_idx = 0

        while start + train_size + gap + test_size <= n:
            if fold_idx >= self.config.n_splits:
                break

            train_end = start + train_size
            test_start = train_end + gap
            test_end = test_start + test_size

            X_train = features.iloc[start:train_end]
            y_train = label.iloc[start:train_end]
            X_test = features.iloc[test_start:test_end]
            y_test = label.iloc[test_start:test_end]

            # 训练
            model = create_model(
                model_type=model_type,
                params=model_params,
                is_classifier=is_classifier,
            )

            try:
                model.fit(X_train, y_train)
                metrics = model.evaluate(X_test, y_test)
                preds = model.predict(X_test)

                metrics_list.append(metrics)
                all_predictions.append(preds)

                fold_detail = {
                    "fold": fold_idx,
                    "train_start": str(X_train.index[0]) if len(X_train) > 0 else "",
                    "train_end": str(X_train.index[-1]) if len(X_train) > 0 else "",
                    "test_start": str(X_test.index[0]) if len(X_test) > 0 else "",
                    "test_end": str(X_test.index[-1]) if len(X_test) > 0 else "",
                    "n_train": len(X_train),
                    "n_test": len(X_test),
                    "ic": metrics.ic,
                    "rank_ic": metrics.rank_ic,
                    "rmse": metrics.rmse,
                }
                fold_details.append(fold_detail)

                logger.info(
                    f"Walk Forward fold {fold_idx}: "
                    f"train={len(X_train)}, test={len(X_test)}, "
                    f"IC={metrics.ic:.4f}"
                )

            except Exception as e:
                logger.error(f"Walk Forward fold {fold_idx} failed: {e}")
                fold_details.append({
                    "fold": fold_idx,
                    "error": str(e),
                })

            start += step_size
            fold_idx += 1

        # 汇总
        result.n_splits = fold_idx
        result.metrics_per_fold = metrics_list
        result.fold_details = fold_details

        if metrics_list:
            ics = [m.ic for m in metrics_list]
            rank_ics = [m.rank_ic for m in metrics_list]
            rmses = [m.rmse for m in metrics_list]
            sharpes = [m.sharpe for m in metrics_list]

            result.avg_ic = float(np.mean(ics))
            result.avg_rank_ic = float(np.mean(rank_ics))
            result.avg_rmse = float(np.mean(rmses))
            result.avg_sharpe = float(np.mean(sharpes))

            # avg_return：信号加权收益的均值
            # 使用每折的 sharpe 近似（sharpe = mean/std * sqrt(N)）
            # 这里用 predictions 与 label 的乘积均值作为收益代理
            if result.predictions is not None:
                try:
                    common = result.predictions.index.intersection(label.index)
                    if len(common) > 0:
                        sig = result.predictions.loc[common]
                        ret = label.loc[common]
                        mask = sig.notna() & ret.notna()
                        if mask.sum() > 0:
                            strategy_ret = sig[mask] * ret[mask]
                            result.avg_return = float(strategy_ret.mean())
                except Exception:
                    pass

            ic_std = float(np.std(ics))
            result.ic_stability = result.avg_ic / ic_std if ic_std > 0 else 0.0

        if all_predictions:
            result.predictions = pd.concat(all_predictions).sort_index()

        return result

    def run_tds(
        self,
        tds: TrainingDataset,
        model_type: ModelType,
        model_params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> WalkForwardResult:
        """
        执行 Walk Forward 验证（TrainingDataset 接口，推荐）

        Args:
            tds: TrainingDataset
            model_type: 模型类型
            model_params: 模型参数
            is_classifier: 是否分类
        """
        return self.run(
            features=tds.X,
            label=tds.y,
            model_type=model_type,
            model_params=model_params,
            is_classifier=is_classifier,
        )


# M3 第一部分：WalkForwardEngine 别名（统一命名）
class WalkForwardEngine(WalkForward):
    """
    Walk Forward Engine — M3 统一命名

    与 WalkForward 完全兼容，仅命名调整以匹配 M3 文档。

    用法：
        engine = WalkForwardEngine(config)
        result = engine.run(features, label, model_type=ModelType.LIGHTGBM)
    """
    pass
