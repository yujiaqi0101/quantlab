"""
Model Lab — 模型实验室

ML Lab 第五部分：统一模型接口

  Model.fit(X, y)
  Model.predict(X)

  支持模型：
    - Linear Regression
    - Random Forest
    - XGBoost
    - LightGBM
"""

from .base import Model, ModelType, ModelMetrics
from .linear import LinearRegressionModel, LogisticRegressionModel
from .ensemble import RandomForestModel
from .gradient_boosting import XGBoostModel, LightGBMModel
from .factory import create_model, list_supported_models

__all__ = [
    "Model",
    "ModelType",
    "ModelMetrics",
    "LinearRegressionModel",
    "LogisticRegressionModel",
    "RandomForestModel",
    "XGBoostModel",
    "LightGBMModel",
    "create_model",
    "list_supported_models",
]
