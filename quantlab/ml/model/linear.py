"""
Linear Models — 线性模型

ML Lab 第五部分：Linear Regression / Logistic Regression
"""

from __future__ import annotations

from sklearn.linear_model import LinearRegression, LogisticRegression

from .base import Model, ModelType


class LinearRegressionModel(Model):
    """线性回归"""

    def __init__(self, params: dict = None) -> None:
        super().__init__(
            model_type=ModelType.LINEAR_REGRESSION,
            params=params or {},
            is_classifier=False,
        )

    def _build_model(self) -> LinearRegression:
        return LinearRegression(**self.params)


class LogisticRegressionModel(Model):
    """逻辑回归（分类）"""

    def __init__(self, params: dict = None) -> None:
        default = {"max_iter": 1000, "random_state": 42}
        default.update(params or {})
        super().__init__(
            model_type=ModelType.LOGISTIC_REGRESSION,
            params=default,
            is_classifier=True,
        )

    def _build_model(self) -> LogisticRegression:
        return LogisticRegression(**self.params)
