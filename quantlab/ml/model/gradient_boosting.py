"""
Gradient Boosting — 梯度提升模型

ML Lab 第五部分：XGBoost / LightGBM
"""

from __future__ import annotations

import logging

from .base import Model, ModelType

logger = logging.getLogger("quantlab.ml.model.gb")


class XGBoostModel(Model):
    """XGBoost"""

    def __init__(
        self,
        params: dict = None,
        is_classifier: bool = False,
    ) -> None:
        default = {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "random_state": 42,
            "n_jobs": -1,
        }
        default.update(params or {})
        super().__init__(
            model_type=ModelType.XGBOOST,
            params=default,
            is_classifier=is_classifier,
        )

    def _build_model(self):
        try:
            from xgboost import XGBClassifier, XGBRegressor
        except ImportError as e:
            raise ImportError("xgboost not installed. Install with: pip install xgboost") from e

        if self.is_classifier:
            return XGBClassifier(**self.params)
        return XGBRegressor(**self.params)


class LightGBMModel(Model):
    """LightGBM"""

    def __init__(
        self,
        params: dict = None,
        is_classifier: bool = False,
    ) -> None:
        default = {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.05,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        default.update(params or {})
        super().__init__(
            model_type=ModelType.LIGHTGBM,
            params=default,
            is_classifier=is_classifier,
        )

    def _build_model(self):
        try:
            from lightgbm import LGBMClassifier, LGBMRegressor
        except ImportError as e:
            raise ImportError("lightgbm not installed. Install with: pip install lightgbm") from e

        if self.is_classifier:
            return LGBMClassifier(**self.params)
        return LGBMRegressor(**self.params)
