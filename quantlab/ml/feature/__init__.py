"""
Feature Lab — 特征实验室

ML Lab 第二部分：特征工程

  Feature
    - feature.compute(df) → pd.Series / pd.DataFrame

  FeatureSet (L2 升级)
    - 特征集合，可命名、版本化、复用
    - 例如：momentum_v1 = [RSI14, RSI21, Momentum20, ATR14]

  内置特征：
    RSI / MACD / ATR / Momentum / VolumeZScore / BollingerBands
"""

from .base import Feature, FeatureRegistry, get_feature_registry
from .set import FeatureSet, FeatureSetRegistry, get_feature_set_registry
from .builtin import register_all_builtin

__all__ = [
    "Feature",
    "FeatureRegistry",
    "get_feature_registry",
    "FeatureSet",
    "FeatureSetRegistry",
    "get_feature_set_registry",
    "register_all_builtin",
]
