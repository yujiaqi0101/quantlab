"""
ML Strategy Builder — ML 策略构建器（L10 升级版）

ML Lab 第十层：ML Lab 的最终目标

  输入：
    FeatureSet (RSI, Momentum, Volume)
    LabelSet (FutureReturn10)
    Model (LightGBM)

  输出：
    MLStrategy
      - predict(df) → 预测值
      - signal(df) → 交易信号 (1/0/-1)
      - position(df) → 目标持仓

  支持两种模式：
    1. 传统：feature_ids + label_id
    2. 集合（推荐）：feature_set_id + label_set_id

  直接进入：Research Studio 或 Deploy
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..feature import FeatureRegistry, get_feature_registry
from ..feature import FeatureSetRegistry, get_feature_set_registry
from ..label import LabelRegistry, get_label_registry
from ..label import LabelSetRegistry, get_label_set_registry
from ..model import Model, ModelType

logger = logging.getLogger("quantlab.ml.strategy_builder")


@dataclass
class MLStrategyConfig:
    """ML 策略配置"""
    # 模式1：传统
    feature_ids: List[str] = field(default_factory=list)
    label_id: str = ""

    # 模式2：集合（推荐）
    feature_set_id: str = ""
    label_set_id: str = ""

    # 模型
    model_type: ModelType = ModelType.LIGHTGBM
    model_params: Dict[str, Any] = field(default_factory=dict)
    is_classifier: bool = False

    # 信号生成参数
    long_threshold: float = 0.0       # 预测值 > 此值 → 多
    short_threshold: float = 0.0      # 预测值 < 此值 → 空
    use_short: bool = False           # 是否允许做空
    position_scale: float = 1.0       # 持仓缩放

    def to_dict(self) -> Dict:
        return {
            "feature_ids": self.feature_ids,
            "label_id": self.label_id,
            "feature_set_id": self.feature_set_id,
            "label_set_id": self.label_set_id,
            "model_type": self.model_type.value,
            "model_params": self.model_params,
            "is_classifier": self.is_classifier,
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
            "position_scale": self.position_scale,
        }


class MLStrategy:
    """
    ML 策略

    用法：
        strategy = MLStrategy(
            config=config,
            model=trained_model,
        )

        # 预测
        preds = strategy.predict(df)

        # 生成信号
        signals = strategy.signal(df)

        # 生成目标持仓
        positions = strategy.position(df)
    """

    def __init__(
        self,
        config: MLStrategyConfig,
        model: Model,
        strategy_id: str = "",
        name: str = "",
    ) -> None:
        self.config = config
        self.model = model
        self.strategy_id = strategy_id or f"MLS-{uuid.uuid4().hex[:8]}"
        self.name = name or f"MLStrategy_{self.strategy_id}"
        self._feature_registry: Optional[FeatureRegistry] = None
        self._feature_set_registry: Optional[FeatureSetRegistry] = None

    def set_feature_registry(self, registry: FeatureRegistry) -> None:
        self._feature_registry = registry

    def set_feature_set_registry(self, registry: FeatureSetRegistry) -> None:
        self._feature_set_registry = registry

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算特征"""
        if self.config.feature_set_id and self._feature_set_registry:
            # 模式2：使用 FeatureSet
            fs = self._feature_set_registry.get(self.config.feature_set_id)
            if fs:
                return fs.compute(df)

        # 模式1：使用 feature_ids
        reg = self._feature_registry or get_feature_registry()
        return reg.compute_many(self.config.feature_ids, df)

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """预测"""
        features = self._compute_features(df)
        if features.empty:
            return pd.Series(dtype=float, index=df.index, name="prediction")
        return self.model.predict(features)

    def signal(self, df: pd.DataFrame) -> pd.Series:
        """
        生成交易信号

        回归模型：
            pred > long_threshold  → 1
            pred < short_threshold → -1 (if use_short)
            else                   → 0

        分类模型：
            pred == 2 (Up)    → 1
            pred == 0 (Down)  → -1 (if use_short)
            else              → 0
        """
        preds = self.predict(df)
        signals = pd.Series(0, index=df.index, name="signal", dtype=int)

        if self.config.is_classifier:
            # 分类：2=Up, 0=Down, 1=Neutral
            signals[preds == 2] = 1
            if self.config.use_short:
                signals[preds == 0] = -1
        else:
            # 回归
            signals[preds > self.config.long_threshold] = 1
            if self.config.use_short:
                signals[preds < self.config.short_threshold] = -1

        return signals

    def position(self, df: pd.DataFrame) -> pd.Series:
        """
        生成目标持仓

        简单版：信号 × position_scale
        后续可接入风控模块做仓位优化
        """
        signals = self.signal(df)
        return (signals * self.config.position_scale).rename("position")

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "config": self.config.to_dict(),
            "model": self.model.to_dict() if self.model else None,
        }


class MLStrategyBuilder:
    """
    ML 策略构建器（L10 升级版）

    用法1（传统）：
        builder = MLStrategyBuilder()
        model = builder.train(df, feature_ids=[...], label_id="...", model_type=...)
        strategy = builder.build(feature_ids=[...], label_id="...", model=model)

    用法2（集合，推荐）：
        strategy = builder.build_from_sets(
            feature_set_id="momentum_v1",
            label_set_id="return_10d",
            model=trained_model,
        )
    """

    def __init__(self) -> None:
        self._feature_registry: Optional[FeatureRegistry] = None
        self._label_registry: Optional[LabelRegistry] = None
        self._feature_set_registry: Optional[FeatureSetRegistry] = None
        self._label_set_registry: Optional[LabelSetRegistry] = None

    def set_registries(
        self,
        feature_registry: FeatureRegistry,
        label_registry: LabelRegistry,
        feature_set_registry: Optional[FeatureSetRegistry] = None,
        label_set_registry: Optional[LabelSetRegistry] = None,
    ) -> None:
        self._feature_registry = feature_registry
        self._label_registry = label_registry
        self._feature_set_registry = feature_set_registry
        self._label_set_registry = label_set_registry

    def train(
        self,
        df: pd.DataFrame,
        feature_ids: List[str],
        label_id: str,
        model_type: ModelType,
        model_params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> Model:
        """训练模型"""
        from ..model import create_model

        feat_reg = self._feature_registry or get_feature_registry()
        label_reg = self._label_registry or get_label_registry()

        # 计算特征
        features = feat_reg.compute_many(feature_ids, df)
        if features.empty:
            raise ValueError("No features computed")

        # 生成标签
        label = label_reg.generate(label_id, df)
        if label is None:
            raise ValueError(f"Label not found: {label_id}")

        # 训练
        model = create_model(
            model_type=model_type,
            params=model_params,
            is_classifier=is_classifier,
        )
        model.fit(features, label)
        return model

    def train_with_sets(
        self,
        df: pd.DataFrame,
        feature_set_id: str,
        label_set_id: str,
        model_type: ModelType,
        model_params: Optional[Dict] = None,
        is_classifier: bool = False,
    ) -> Model:
        """使用 FeatureSet + LabelSet 训练"""
        fs_reg = self._feature_set_registry or get_feature_set_registry()
        ls_reg = self._label_set_registry or get_label_set_registry()

        fs = fs_reg.get(feature_set_id)
        ls = ls_reg.get(label_set_id)
        if fs is None:
            raise ValueError(f"FeatureSet not found: {feature_set_id}")
        if ls is None:
            raise ValueError(f"LabelSet not found: {label_set_id}")

        features = fs.compute(df)
        label = ls.generate(df)

        from ..model import create_model
        model = create_model(
            model_type=model_type,
            params=model_params,
            is_classifier=is_classifier,
        )
        model.fit(features, label)
        return model

    def build(
        self,
        feature_ids: List[str],
        label_id: str,
        model: Model,
        model_type: ModelType = ModelType.LIGHTGBM,
        is_classifier: bool = False,
        long_threshold: float = 0.0,
        short_threshold: float = 0.0,
        use_short: bool = False,
        position_scale: float = 1.0,
        name: str = "",
    ) -> MLStrategy:
        """构建 ML 策略（传统接口）"""
        config = MLStrategyConfig(
            feature_ids=feature_ids,
            label_id=label_id,
            model_type=model_type,
            model_params=model.params if model else {},
            is_classifier=is_classifier,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            use_short=use_short,
            position_scale=position_scale,
        )
        strategy = MLStrategy(
            config=config,
            model=model,
            name=name,
        )
        if self._feature_registry:
            strategy.set_feature_registry(self._feature_registry)
        logger.info(f"ML Strategy built: {strategy.strategy_id} ({strategy.name})")
        return strategy

    def build_from_sets(
        self,
        feature_set_id: str,
        label_set_id: str,
        model: Model,
        model_type: ModelType = ModelType.LIGHTGBM,
        is_classifier: bool = False,
        long_threshold: float = 0.0,
        short_threshold: float = 0.0,
        use_short: bool = False,
        position_scale: float = 1.0,
        name: str = "",
    ) -> MLStrategy:
        """从 FeatureSet + LabelSet 构建 ML 策略（推荐）"""
        config = MLStrategyConfig(
            feature_set_id=feature_set_id,
            label_set_id=label_set_id,
            model_type=model_type,
            model_params=model.params if model else {},
            is_classifier=is_classifier,
            long_threshold=long_threshold,
            short_threshold=short_threshold,
            use_short=use_short,
            position_scale=position_scale,
        )
        strategy = MLStrategy(
            config=config,
            model=model,
            name=name,
        )
        # 注入 registries
        if self._feature_registry:
            strategy.set_feature_registry(self._feature_registry)
        if self._feature_set_registry:
            strategy.set_feature_set_registry(self._feature_set_registry)
        else:
            strategy.set_feature_set_registry(get_feature_set_registry())

        logger.info(
            f"ML Strategy built from sets: {strategy.strategy_id} "
            f"(fs={feature_set_id}, ls={label_set_id})"
        )
        return strategy

    def build_from_version(
        self,
        version,
        model: Optional[Model] = None,
    ) -> MLStrategy:
        """
        从 ModelVersion 构建策略

        Args:
            version: ModelVersion 对象
            model: 已训练的模型（如果 version 中没有保存）
        """
        used_model = model or version.get_model()
        if used_model is None:
            raise ValueError("No model available. Train a model first.")

        return self.build(
            feature_ids=version.feature_ids,
            label_id=version.label_id,
            model=used_model,
            model_type=version.model_type,
            is_classifier=version.is_classifier,
            name=f"MLStrategy_{version.name}",
        )
