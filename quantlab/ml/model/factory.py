"""
Model Factory — 模型工厂

ML Lab 第五部分：统一创建模型

  model = create_model(ModelType.LIGHTGBM, params={...}, is_classifier=False)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .base import Model, ModelType
from .linear import LinearRegressionModel, LogisticRegressionModel
from .ensemble import RandomForestModel
from .gradient_boosting import XGBoostModel, LightGBMModel


def create_model(
    model_type: ModelType,
    params: Optional[Dict] = None,
    is_classifier: bool = False,
) -> Model:
    """创建模型"""
    if model_type == ModelType.LINEAR_REGRESSION:
        return LinearRegressionModel(params=params)
    elif model_type == ModelType.LOGISTIC_REGRESSION:
        return LogisticRegressionModel(params=params)
    elif model_type == ModelType.RANDOM_FOREST:
        return RandomForestModel(params=params, is_classifier=is_classifier)
    elif model_type == ModelType.XGBOOST:
        return XGBoostModel(params=params, is_classifier=is_classifier)
    elif model_type == ModelType.LIGHTGBM:
        return LightGBMModel(params=params, is_classifier=is_classifier)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def list_supported_models() -> List[Dict]:
    """列出支持的模型"""
    return [
        {
            "type": ModelType.LINEAR_REGRESSION.value,
            "name": "Linear Regression",
            "is_classifier": False,
            "description": "线性回归（基准模型）",
        },
        {
            "type": ModelType.LOGISTIC_REGRESSION.value,
            "name": "Logistic Regression",
            "is_classifier": True,
            "description": "逻辑回归（分类基准）",
        },
        {
            "type": ModelType.RANDOM_FOREST.value,
            "name": "Random Forest",
            "is_classifier": False,
            "description": "随机森林（非线性，可解释）",
        },
        {
            "type": ModelType.XGBOOST.value,
            "name": "XGBoost",
            "is_classifier": False,
            "description": "XGBoost（梯度提升，强预测力）",
        },
        {
            "type": ModelType.LIGHTGBM.value,
            "name": "LightGBM",
            "is_classifier": False,
            "description": "LightGBM（梯度提升，快速高效）",
        },
    ]
