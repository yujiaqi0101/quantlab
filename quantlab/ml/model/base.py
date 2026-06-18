"""
Model — 模型抽象基类

ML Lab 第五部分：统一模型接口

  class MyModel(Model):
      def fit(self, X, y): ...
      def predict(self, X): ...

  model = MyModel(params={...})
  model.fit(X_train, y_train)
  preds = model.predict(X_test)
  metrics = model.evaluate(X_test, y_test)
"""

from __future__ import annotations

import logging
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.model")


class ModelType(str, Enum):
    """模型类型"""
    LINEAR_REGRESSION = "LINEAR_REGRESSION"
    LOGISTIC_REGRESSION = "LOGISTIC_REGRESSION"
    RANDOM_FOREST = "RANDOM_FOREST"
    XGBOOST = "XGBOOST"
    LIGHTGBM = "LIGHTGBM"


@dataclass
class ModelMetrics:
    """模型评估指标（M2 升级：集成 Sharpe/Precision/Recall/AUC）"""
    # 回归指标
    mae: float = 0.0
    mse: float = 0.0
    rmse: float = 0.0
    r2: float = 0.0
    ic: float = 0.0           # Information Coefficient
    rank_ic: float = 0.0      # Rank IC
    sharpe: float = 0.0       # 年化夏普比率（M2 新增）
    # 分类指标
    accuracy: float = 0.0     # 分类准确率
    precision: float = 0.0    # 精确率（M2 新增）
    recall: float = 0.0       # 召回率（M2 新增）
    auc: float = 0.0          # ROC AUC（M2 新增）
    # 元信息
    n_samples: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "mae": round(self.mae, 6),
            "mse": round(self.mse, 6),
            "rmse": round(self.rmse, 6),
            "r2": round(self.r2, 6),
            "ic": round(self.ic, 6),
            "rank_ic": round(self.rank_ic, 6),
            "sharpe": round(self.sharpe, 6),
            "accuracy": round(self.accuracy, 6),
            "precision": round(self.precision, 6),
            "recall": round(self.recall, 6),
            "auc": round(self.auc, 6),
            "n_samples": self.n_samples,
            "extra": self.extra,
        }


class Model(ABC):
    """
    模型抽象基类

    用法：
        model = LinearRegressionModel(params={})
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        metrics = model.evaluate(X_test, y_test)
    """

    def __init__(
        self,
        model_type: ModelType,
        params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> None:
        self.model_type = model_type
        self.params = params or {}
        self.is_classifier = is_classifier
        self._model = None
        self._fitted = False
        self._feature_names: List[str] = []
        self._train_time: float = 0.0

    @abstractmethod
    def _build_model(self) -> Any:
        """构建底层模型（子类实现）"""
        ...

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def feature_names(self) -> List[str]:
        return self._feature_names

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """训练模型"""
        start = time.time()
        self._feature_names = list(X.columns)
        self._model = self._build_model()

        # 去掉 NaN
        mask = X.notna().all(axis=1) & y.notna()
        X_clean = X[mask]
        y_clean = y[mask]

        if len(X_clean) == 0:
            raise ValueError("No valid samples after removing NaN")

        self._model.fit(X_clean.values, y_clean.values)
        self._fitted = True
        self._train_time = time.time() - start
        logger.info(
            f"Model {self.model_type} fitted: {len(X_clean)} samples, "
            f"{self._train_time:.2f}s"
        )

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """预测"""
        if not self._fitted:
            raise RuntimeError("Model not fitted")
        # 填充 NaN（用前向填充或 0）
        X_filled = X[self._feature_names].fillna(0) if hasattr(X, "fillna") else X
        preds = self._model.predict(X_filled.values)
        return pd.Series(preds, index=X.index, name="prediction")

    def predict_proba(self, X: pd.DataFrame) -> Optional[pd.DataFrame]:
        """分类模型：预测概率"""
        if not self._fitted or not self.is_classifier:
            return None
        if not hasattr(self._model, "predict_proba"):
            return None
        X_filled = X[self._feature_names].fillna(0)
        proba = self._model.predict_proba(X_filled.values)
        return pd.DataFrame(proba, index=X.index, columns=self._get_classes())

    def _get_classes(self) -> List[str]:
        if hasattr(self._model, "classes_"):
            return [str(c) for c in self._model.classes_]
        return []

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> ModelMetrics:
        """
        评估模型（M2 升级：集成 Sharpe/Precision/Recall/AUC）

        使用 quantlab.ml.metrics 模块计算完整指标。
        """
        if not self._fitted:
            raise RuntimeError("Model not fitted")

        mask = X.notna().all(axis=1) & y.notna()
        X_clean = X[mask]
        y_clean = y[mask]

        if len(X_clean) == 0:
            return ModelMetrics()

        preds = self.predict(X_clean)

        # 使用 M2 Metrics Engine 计算完整指标
        from ..metrics import compute_all_metrics

        # 分类问题尝试获取概率
        y_proba = None
        if self.is_classifier:
            proba_df = self.predict_proba(X_clean)
            if proba_df is not None and len(proba_df.columns) > 0:
                # 取正类概率（最后一列）
                y_proba = proba_df.iloc[:, -1]

        result = compute_all_metrics(
            y_true=y_clean,
            y_pred=preds,
            is_classifier=self.is_classifier,
            y_proba=y_proba,
        )

        # 转换为 ModelMetrics
        return ModelMetrics(
            mae=result.mae,
            mse=result.mse,
            rmse=result.rmse,
            r2=result.r2,
            ic=result.ic,
            rank_ic=result.rank_ic,
            sharpe=result.sharpe,
            accuracy=result.accuracy,
            precision=result.precision,
            recall=result.recall,
            auc=result.auc,
            n_samples=result.n_samples,
            extra=result.extra,
        )

    def feature_importance(self) -> Optional[pd.Series]:
        """特征重要性"""
        if not self._fitted:
            return None
        if hasattr(self._model, "feature_importances_"):
            return pd.Series(
                self._model.feature_importances_,
                index=self._feature_names,
                name="importance",
            ).sort_values(ascending=False)
        if hasattr(self._model, "coef_"):
            return pd.Series(
                np.abs(self._model.coef_).ravel(),
                index=self._feature_names,
                name="importance",
            ).sort_values(ascending=False)
        return None

    def save(self, filepath: str) -> bool:
        """保存模型"""
        try:
            with open(filepath, "wb") as f:
                pickle.dump({
                    "model_type": self.model_type,
                    "params": self.params,
                    "is_classifier": self.is_classifier,
                    "feature_names": self._feature_names,
                    "model": self._model,
                    "fitted": self._fitted,
                }, f)
            return True
        except Exception as e:
            logger.error(f"Save model failed: {e}")
            return False

    def load(self, filepath: str) -> bool:
        """加载模型"""
        try:
            with open(filepath, "rb") as f:
                data = pickle.load(f)
            self._model = data["model"]
            self._fitted = data["fitted"]
            self._feature_names = data["feature_names"]
            return True
        except Exception as e:
            logger.error(f"Load model failed: {e}")
            return False

    def to_dict(self) -> Dict:
        return {
            "model_type": self.model_type.value,
            "params": self.params,
            "is_classifier": self.is_classifier,
            "is_fitted": self._fitted,
            "feature_names": self._feature_names,
            "train_time": round(self._train_time, 4),
        }
