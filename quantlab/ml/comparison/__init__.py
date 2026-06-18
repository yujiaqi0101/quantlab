"""
Model Comparison — 模型对比（Model Arena）

ML Lab 第九层：前端特别有价值的页面

  例如：
    Model       Sharpe
    Linear      0.8
    RF          1.1
    LGBM        1.5
    XGBoost     1.4

  直接比较，像 AI 模型排行榜。

  用法：
      arena = ModelArena()
      arena.add("Linear", result_linear)
      arena.add("LGBM", result_lgbm)
      leaderboard = arena.get_leaderboard(metric="ic")
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..model import ModelType, create_model
from ..pipeline import TrainingDataset

logger = logging.getLogger("quantlab.ml.comparison")


@dataclass
class ModelResult:
    """单个模型的训练结果（用于对比）"""
    name: str                              # 模型显示名
    model_type: str                        # 模型类型
    model_params: Dict[str, Any] = field(default_factory=dict)
    is_classifier: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    train_time: float = 0.0
    n_train_samples: int = 0
    n_test_samples: int = 0
    status: str = "COMPLETED"
    error: str = ""
    result_id: str = field(default_factory=lambda: f"MR-{uuid.uuid4().hex[:8]}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "name": self.name,
            "model_type": self.model_type,
            "model_params": self.model_params,
            "is_classifier": self.is_classifier,
            "metrics": self.metrics,
            "feature_importance": self.feature_importance,
            "train_time": round(self.train_time, 4),
            "n_train_samples": self.n_train_samples,
            "n_test_samples": self.n_test_samples,
            "status": self.status,
            "error": self.error,
        }


class ModelArena:
    """
    模型竞技场

    用法：
        arena = ModelArena()
        arena.add("Linear", result1)
        arena.add("LGBM", result2)
        leaderboard = arena.get_leaderboard(metric="ic")
    """

    def __init__(self) -> None:
        self._results: Dict[str, ModelResult] = {}

    def add(self, result: ModelResult) -> str:
        """添加模型结果"""
        self._results[result.result_id] = result
        logger.info(f"ModelArena added: {result.name} ({result.model_type})")
        return result.result_id

    def add_from_training_result(self, name: str, training_result, model_type: str = "") -> str:
        """从 TrainingResult 添加"""
        result = ModelResult(
            name=name,
            model_type=model_type or training_result.job_id,
            metrics=training_result.metrics.to_dict() if training_result.metrics else {},
            feature_importance=training_result.feature_importance,
            train_time=training_result.train_time,
            n_train_samples=training_result.n_train_samples,
            n_test_samples=training_result.n_test_samples,
            status=training_result.status.value if hasattr(training_result.status, "value") else str(training_result.status),
            error=training_result.error,
        )
        return self.add(result)

    def get(self, result_id: str) -> Optional[ModelResult]:
        return self._results.get(result_id)

    def list_all(self) -> List[ModelResult]:
        return list(self._results.values())

    def get_leaderboard(
        self,
        metric: str = "ic",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        获取排行榜

        Args:
            metric: 排序指标，如 "ic", "sharpe", "rmse"
            ascending: True 表示越小越好（如 rmse）
        """
        results = [r for r in self._results.values() if r.status == "COMPLETED"]
        # 过滤有该指标的
        valid = [r for r in results if metric in r.metrics]
        valid.sort(key=lambda r: r.metrics[metric], reverse=not ascending)

        leaderboard = []
        for rank, r in enumerate(valid, 1):
            d = r.to_dict()
            d["rank"] = rank
            d["metric_value"] = r.metrics.get(metric, 0)
            leaderboard.append(d)
        return leaderboard

    def get_best(self, metric: str = "ic", ascending: bool = False) -> Optional[ModelResult]:
        """获取最优模型"""
        board = self.get_leaderboard(metric=metric, ascending=ascending)
        if not board:
            return None
        return self.get(board[0]["result_id"])

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame"""
        data = []
        for r in self.list_all():
            d = r.to_dict()
            # 展平 metrics
            for k, v in d.pop("metrics", {}).items():
                d[f"metric_{k}"] = v
            data.append(d)
        return pd.DataFrame(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._results),
            "results": [r.to_dict() for r in self.list_all()],
        }


def compare_models(
    tds: TrainingDataset,
    model_types: List[ModelType],
    model_params: Optional[Dict[ModelType, Dict]] = None,
    is_classifier: bool = False,
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> ModelArena:
    """
    快捷函数：对比多个模型

    用法：
        arena = compare_models(
            tds=tds,
            model_types=[ModelType.LINEAR_REGRESSION, ModelType.LIGHTGBM],
        )
        leaderboard = arena.get_leaderboard(metric="ic")
    """
    import time

    arena = ModelArena()
    model_params = model_params or {}

    splits = tds.split(train_ratio=train_ratio, val_ratio=val_ratio)
    X_train, y_train = splits["train"].X, splits["train"].y
    X_test, y_test = splits["test"].X, splits["test"].y

    for mt in model_types:
        name = mt.value
        params = model_params.get(mt, {})
        start = time.time()

        try:
            model = create_model(
                model_type=mt,
                params=params,
                is_classifier=is_classifier,
            )
            model.fit(X_train, y_train)
            metrics = model.evaluate(X_test, y_test) if len(X_test) > 0 else None
            fi = model.feature_importance()
            fi_dict = fi.to_dict() if fi is not None else {}

            result = ModelResult(
                name=name,
                model_type=mt.value,
                model_params=params,
                is_classifier=is_classifier,
                metrics=metrics.to_dict() if metrics else {},
                feature_importance=fi_dict,
                train_time=time.time() - start,
                n_train_samples=len(X_train),
                n_test_samples=len(X_test),
                status="COMPLETED",
            )
            logger.info(
                f"ModelArena {name}: IC={metrics.ic if metrics else 0:.4f}, "
                f"time={result.train_time:.2f}s"
            )
        except Exception as e:
            result = ModelResult(
                name=name,
                model_type=mt.value,
                model_params=params,
                is_classifier=is_classifier,
                train_time=time.time() - start,
                status="FAILED",
                error=str(e),
            )
            logger.error(f"ModelArena {name} failed: {e}")

        arena.add(result)

    return arena


_arena: Optional[ModelArena] = None


def get_model_arena() -> ModelArena:
    """全局 ModelArena 单例"""
    global _arena
    if _arena is None:
        _arena = ModelArena()
    return _arena
