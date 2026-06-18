"""
Random Forest — 随机森林

ML Lab 第五部分：Random Forest（回归 + 分类）
"""

from __future__ import annotations

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from .base import Model, ModelType


class RandomForestModel(Model):
    """随机森林"""

    def __init__(
        self,
        params: dict = None,
        is_classifier: bool = False,
    ) -> None:
        default = {
            "n_estimators": 100,
            "max_depth": 6,
            "random_state": 42,
            "n_jobs": -1,
        }
        default.update(params or {})
        super().__init__(
            model_type=ModelType.RANDOM_FOREST,
            params=default,
            is_classifier=is_classifier,
        )

    def _build_model(self):
        if self.is_classifier:
            return RandomForestClassifier(**self.params)
        return RandomForestRegressor(**self.params)
