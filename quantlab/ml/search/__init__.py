"""
Hyperparameter Search — 超参搜索

ML Lab 第六层：自动搜索最优超参

  支持：
    - GridSearch：网格搜索
    - RandomSearch：随机搜索

  不做：Bayesian Search / AutoML（没必要，收益低）

  用法：
      search = GridSearch(
          model_type=ModelType.LIGHTGBM,
          param_grid={
              "n_estimators": [100, 200, 300],
              "max_depth": [3, 5, 7],
              "learning_rate": [0.01, 0.05, 0.1],
          },
          metric="ic",
      )
      result = search.run(tds)
"""

from __future__ import annotations

import itertools
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..model import Model, ModelType, ModelMetrics, create_model
from ..pipeline import TrainingDataset

logger = logging.getLogger("quantlab.ml.search")


@dataclass
class TrialResult:
    """单次试验结果"""
    trial_id: int
    params: Dict[str, Any]
    metrics: Dict[str, Any]
    train_time: float = 0.0
    status: str = "COMPLETED"        # COMPLETED / FAILED
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trial_id": self.trial_id,
            "params": self.params,
            "metrics": self.metrics,
            "train_time": round(self.train_time, 4),
            "status": self.status,
            "error": self.error,
        }


@dataclass
class SearchResult:
    """搜索结果"""
    search_id: str = field(default_factory=lambda: f"SRCH-{uuid.uuid4().hex[:8]}")
    search_type: str = "grid"        # grid / random
    model_type: str = ""
    metric: str = "ic"
    n_trials: int = 0
    best_params: Dict[str, Any] = field(default_factory=dict)
    best_metric: float = 0.0
    best_trial_id: int = -1
    trials: List[TrialResult] = field(default_factory=list)
    total_time: float = 0.0
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "search_id": self.search_id,
            "search_type": self.search_type,
            "model_type": self.model_type,
            "metric": self.metric,
            "n_trials": self.n_trials,
            "best_params": self.best_params,
            "best_metric": round(self.best_metric, 6),
            "best_trial_id": self.best_trial_id,
            "trials": [t.to_dict() for t in self.trials],
            "total_time": round(self.total_time, 4),
            "created_at": self.created_at,
        }


def _evaluate_params(
    model_type: ModelType,
    params: Dict[str, Any],
    tds: TrainingDataset,
    is_classifier: bool,
    train_ratio: float,
    val_ratio: float,
    metric: str,
) -> Tuple[Dict[str, Any], float, str]:
    """评估单组参数"""
    try:
        splits = tds.split(train_ratio=train_ratio, val_ratio=val_ratio)
        X_train, y_train = splits["train"].X, splits["train"].y
        X_val, y_val = splits["val"].X, splits["val"].y

        model = create_model(
            model_type=model_type,
            params=params,
            is_classifier=is_classifier,
        )
        model.fit(X_train, y_train)
        m = model.evaluate(X_val, y_val) if len(X_val) > 0 else ModelMetrics()
        metrics_dict = m.to_dict()
        score = metrics_dict.get(metric, 0.0)
        return metrics_dict, float(score), "COMPLETED"
    except Exception as e:
        return {}, 0.0, f"FAILED: {e}"


class GridSearch:
    """
    网格搜索

    用法：
        search = GridSearch(
            model_type=ModelType.LIGHTGBM,
            param_grid={
                "n_estimators": [100, 200],
                "max_depth": [3, 5],
            },
            metric="ic",
        )
        result = search.run(tds)
    """

    def __init__(
        self,
        model_type: ModelType,
        param_grid: Dict[str, List[Any]],
        metric: str = "ic",
        is_classifier: bool = False,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
    ) -> None:
        self.model_type = model_type
        self.param_grid = param_grid
        self.metric = metric
        self.is_classifier = is_classifier
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio

    def _generate_combinations(self) -> List[Dict[str, Any]]:
        """生成所有参数组合"""
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        combos = []
        for v in itertools.product(*values):
            combos.append(dict(zip(keys, v)))
        return combos

    def run(self, tds: TrainingDataset) -> SearchResult:
        """执行网格搜索"""
        combos = self._generate_combinations()
        result = SearchResult(
            search_type="grid",
            model_type=self.model_type.value,
            metric=self.metric,
            n_trials=len(combos),
        )

        logger.info(f"GridSearch start: {len(combos)} trials, metric={self.metric}")
        start = time.time()

        best_score = -np.inf
        for i, params in enumerate(combos):
            t_start = time.time()
            metrics_dict, score, status = _evaluate_params(
                self.model_type, params, tds,
                self.is_classifier, self.train_ratio, self.val_ratio,
                self.metric,
            )
            trial = TrialResult(
                trial_id=i,
                params=params,
                metrics=metrics_dict,
                train_time=time.time() - t_start,
                status=status.split(":")[0],
                error=status.split(":", 1)[1] if ":" in status else "",
            )
            result.trials.append(trial)

            if status == "COMPLETED" and score > best_score:
                best_score = score
                result.best_params = params
                result.best_metric = score
                result.best_trial_id = i

            logger.info(
                f"Trial {i}: params={params}, {self.metric}={score:.4f}, "
                f"status={trial.status}"
            )

        result.total_time = time.time() - start
        logger.info(
            f"GridSearch done: best={result.best_metric:.4f}, "
            f"params={result.best_params}, time={result.total_time:.2f}s"
        )
        return result


class RandomSearch:
    """
    随机搜索

    用法：
        search = RandomSearch(
            model_type=ModelType.LIGHTGBM,
            param_space={
                "n_estimators": (100, 500),
                "max_depth": (3, 10),
                "learning_rate": (0.01, 0.3),
            },
            n_trials=20,
            metric="ic",
        )
        result = search.run(tds)
    """

    def __init__(
        self,
        model_type: ModelType,
        param_space: Dict[str, Tuple[Any, Any]],
        n_trials: int = 20,
        metric: str = "ic",
        is_classifier: bool = False,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        seed: int = 42,
    ) -> None:
        self.model_type = model_type
        self.param_space = param_space
        self.n_trials = n_trials
        self.metric = metric
        self.is_classifier = is_classifier
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.seed = seed

    def _sample_params(self) -> Dict[str, Any]:
        """随机采样参数"""
        rng = random.Random(self.seed)
        params = {}
        for k, v in self.param_space.items():
            if isinstance(v, tuple) and len(v) == 2:
                lo, hi = v
                if isinstance(lo, int) and isinstance(hi, int):
                    params[k] = rng.randint(lo, hi)
                else:
                    params[k] = rng.uniform(lo, hi)
            elif isinstance(v, list):
                params[k] = rng.choice(v)
            else:
                params[k] = v
        return params

    def run(self, tds: TrainingDataset) -> SearchResult:
        """执行随机搜索"""
        result = SearchResult(
            search_type="random",
            model_type=self.model_type.value,
            metric=self.metric,
            n_trials=self.n_trials,
        )

        logger.info(f"RandomSearch start: {self.n_trials} trials, metric={self.metric}")
        start = time.time()

        best_score = -np.inf
        for i in range(self.n_trials):
            params = self._sample_params()
            t_start = time.time()
            metrics_dict, score, status = _evaluate_params(
                self.model_type, params, tds,
                self.is_classifier, self.train_ratio, self.val_ratio,
                self.metric,
            )
            trial = TrialResult(
                trial_id=i,
                params=params,
                metrics=metrics_dict,
                train_time=time.time() - t_start,
                status=status.split(":")[0],
                error=status.split(":", 1)[1] if ":" in status else "",
            )
            result.trials.append(trial)

            if status == "COMPLETED" and score > best_score:
                best_score = score
                result.best_params = params
                result.best_metric = score
                result.best_trial_id = i

            logger.info(
                f"Trial {i}: params={params}, {self.metric}={score:.4f}"
            )

        result.total_time = time.time() - start
        logger.info(
            f"RandomSearch done: best={result.best_metric:.4f}, "
            f"params={result.best_params}, time={result.total_time:.2f}s"
        )
        return result


def run_grid_search(
    model_type: ModelType,
    param_grid: Dict[str, List[Any]],
    tds: TrainingDataset,
    metric: str = "ic",
    is_classifier: bool = False,
) -> SearchResult:
    """快捷函数：网格搜索"""
    search = GridSearch(
        model_type=model_type,
        param_grid=param_grid,
        metric=metric,
        is_classifier=is_classifier,
    )
    return search.run(tds)


def run_random_search(
    model_type: ModelType,
    param_space: Dict[str, Tuple[Any, Any]],
    tds: TrainingDataset,
    n_trials: int = 20,
    metric: str = "ic",
    is_classifier: bool = False,
) -> SearchResult:
    """快捷函数：随机搜索"""
    search = RandomSearch(
        model_type=model_type,
        param_space=param_space,
        n_trials=n_trials,
        metric=metric,
        is_classifier=is_classifier,
    )
    return search.run(tds)
