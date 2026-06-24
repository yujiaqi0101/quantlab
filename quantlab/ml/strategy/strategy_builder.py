"""
Strategy Builder — ML 策略构建器

ML Lab M5 第六部分：M5 核心

  输入：
    Champion Model
    FeatureSet
    Signal Rule
    Position Rule

  自动生成：
    MLStrategy

  例如：
    Model:        LGBM_v3
    FeatureSet:   Momentum_v2
    Signal:       Pred > 0.02 BUY
    生成：        LGBM_Momentum_Strategy

  无需写代码。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

import pandas as pd

from ..feature import (
    FeatureRegistry, FeatureSetRegistry,
    get_feature_registry, get_feature_set_registry,
)
from ..model import Model, ModelType
from ..registry import (
    ModelVersion, ModelRegistry, get_model_registry,
    LifecycleStatus,
)
from .ml_strategy import MLStrategyV2, MLStrategyConfigV2
from .signal_generator import SignalRule
from .position_sizer import PositionSizeConfig, SizingMode
from .risk_overlay import RiskConfig

logger = logging.getLogger("quantlab.ml.strategy.builder")


# ------------------------------------------------------------------
# Build Request
# ------------------------------------------------------------------

class StrategyBuildRequest:
    """
    策略构建请求

    用法：
        req = StrategyBuildRequest(
            model_version_id="MV-xxx",       # Champion
            feature_set_id="momentum_v2",
            symbol="BTCUSDT",
            long_threshold=0.02,
            position_mode="confidence",
            max_position=0.3,
        )
        strategy = builder.build(req)
    """

    def __init__(
        self,
        # 模型来源（二选一）
        model_version_id: str = "",
        model: Optional[Model] = None,
        # 特征来源（二选一）
        feature_set_id: str = "",
        feature_ids: Optional[List[str]] = None,
        # 标的
        symbol: str = "BTCUSDT",
        # 信号规则
        long_threshold: float = 0.02,
        short_threshold: float = -0.02,
        use_short: bool = False,
        is_classifier: bool = False,
        score_mode: str = "tanh",
        score_scale: float = 1.0,
        # 仓位规则
        position_mode: str = "confidence",     # fixed / confidence / volatility / kelly
        base_size: float = 0.2,
        max_size: float = 1.0,
        confidence_scale: float = 1.0,
        target_volatility: float = 0.15,
        kelly_fraction: float = 0.5,
        # 风控
        max_position: float = 0.3,
        max_portfolio: float = 1.0,
        max_drawdown: float = 0.20,
        max_daily_loss: float = 0.05,
        # 元信息
        name: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        author: str = "",
    ) -> None:
        self.model_version_id = model_version_id
        self.model = model
        self.feature_set_id = feature_set_id
        self.feature_ids = feature_ids or []
        self.symbol = symbol

        # 信号
        self.long_threshold = long_threshold
        self.short_threshold = short_threshold
        self.use_short = use_short
        self.is_classifier = is_classifier
        self.score_mode = score_mode
        self.score_scale = score_scale

        # 仓位
        self.position_mode = position_mode
        self.base_size = base_size
        self.max_size = max_size
        self.confidence_scale = confidence_scale
        self.target_volatility = target_volatility
        self.kelly_fraction = kelly_fraction

        # 风控
        self.max_position = max_position
        self.max_portfolio = max_portfolio
        self.max_drawdown = max_drawdown
        self.max_daily_loss = max_daily_loss

        # 元信息
        self.name = name
        self.description = description
        self.tags = tags or []
        self.author = author

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_version_id": self.model_version_id,
            "has_model": self.model is not None,
            "feature_set_id": self.feature_set_id,
            "feature_ids": self.feature_ids,
            "symbol": self.symbol,
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
            "is_classifier": self.is_classifier,
            "position_mode": self.position_mode,
            "base_size": self.base_size,
            "max_size": self.max_size,
            "max_position": self.max_position,
            "max_drawdown": self.max_drawdown,
            "name": self.name,
            "tags": self.tags,
        }


# ------------------------------------------------------------------
# Strategy Builder
# ------------------------------------------------------------------

class StrategyBuilder:
    """
    ML 策略构建器

    用法：
        builder = StrategyBuilder()
        builder.set_registries(feature_set_registry=fs_reg)

        # 从 Champion 构建
        strategy = builder.build_from_champion(
            family="LGBM_Momentum",
            feature_set_id="momentum_v2",
            symbol="BTCUSDT",
        )

        # 从 ModelVersion 构建
        strategy = builder.build_from_version(
            version_id="MV-xxx",
            feature_set_id="momentum_v2",
        )

        # 自定义构建
        req = StrategyBuildRequest(...)
        strategy = builder.build(req)
    """

    def __init__(self) -> None:
        self._feature_registry: Optional[FeatureRegistry] = None
        self._feature_set_registry: Optional[FeatureSetRegistry] = None
        self._model_registry: Optional[ModelRegistry] = None
        # 已构建的策略
        self._strategies: Dict[str, MLStrategyV2] = {}

    def set_registries(
        self,
        feature_registry: Optional[FeatureRegistry] = None,
        feature_set_registry: Optional[FeatureSetRegistry] = None,
        model_registry: Optional[ModelRegistry] = None,
    ) -> None:
        if feature_registry:
            self._feature_registry = feature_registry
        if feature_set_registry:
            self._feature_set_registry = feature_set_registry
        if model_registry:
            self._model_registry = model_registry

    # ------------------------------------------------------------------
    # 主入口：build
    # ------------------------------------------------------------------

    def build(self, req: StrategyBuildRequest) -> MLStrategyV2:
        """
        根据请求构建 ML 策略

        Args:
            req: 构建请求

        Returns:
            MLStrategyV2 实例
        """
        # 1. 解析模型
        model, model_version = self._resolve_model(req)
        if model is None:
            raise ValueError(
                "No model available. "
                "Provide model_version_id or model."
            )

        # 2. 解析特征来源
        feature_set_id = req.feature_set_id
        feature_ids = req.feature_ids
        if not feature_set_id and not feature_ids and model_version:
            # 从 ModelVersion 继承
            feature_ids = list(model_version.feature_ids)
            logger.info(
                f"Builder: inherited feature_ids from {model_version.name}: {feature_ids}"
            )

        # 3. 构建子配置
        signal_rule = SignalRule(
            long_threshold=req.long_threshold,
            short_threshold=req.short_threshold,
            use_short=req.use_short,
            is_classifier=req.is_classifier,
            score_mode=req.score_mode,
            score_scale=req.score_scale,
        )

        position_config = PositionSizeConfig(
            mode=SizingMode(req.position_mode),
            base_size=req.base_size,
            max_size=req.max_size,
            confidence_scale=req.confidence_scale,
            target_volatility=req.target_volatility,
            kelly_fraction=req.kelly_fraction,
        )

        risk_config = RiskConfig(
            max_position=req.max_position,
            max_portfolio=req.max_portfolio,
            max_drawdown=req.max_drawdown,
            max_daily_loss=req.max_daily_loss,
        )

        # 4. 生成策略名
        name = req.name
        if not name:
            if model_version:
                name = f"{model_version.family}_Strategy" if model_version.family else f"{model_version.name}_Strategy"
            else:
                name = f"MLStrategy_{req.symbol}"

        # 5. 构建配置
        config = MLStrategyConfigV2(
            name=name,
            description=req.description or f"ML Strategy for {req.symbol}",
            symbol=req.symbol,
            feature_set_id=feature_set_id,
            feature_ids=feature_ids,
            model_version_id=req.model_version_id or (model_version.version_id if model_version else ""),
            model=model,
            signal_rule=signal_rule,
            position_config=position_config,
            risk_config=risk_config,
            tags=req.tags,
            author=req.author,
        )

        # 6. 创建策略
        strategy = MLStrategyV2(
            config=config,
            model=model,
            model_version=model_version,
        )

        # 7. 注入注册表
        if self._feature_registry:
            strategy.set_feature_registry(self._feature_registry)
        if self._feature_set_registry:
            strategy.set_feature_set_registry(self._feature_set_registry)
        elif feature_set_id:
            strategy.set_feature_set_registry(get_feature_set_registry())

        # 8. 注册到本地
        self._strategies[strategy.config.strategy_id] = strategy

        logger.info(
            f"Strategy built: {strategy.config.strategy_id} "
            f"({strategy.config.name}) model={req.model_version_id or 'inline'} "
            f"fs={feature_set_id or 'inherited'}"
        )

        # 9. 自动注册到 AssetRegistry + 建立血缘
        try:
            from ...asset import (
                register_strategy_asset, add_strategy_lineage,
                register_model_asset, AssetType,
            )
            # 查找关联的 Model 资产
            model_asset_id = ""
            if model_version:
                # 通过 model_package_id 查找
                from ...asset import get_asset_registry
                reg = get_asset_registry()
                for asset in reg.list_assets(asset_type=AssetType.MODEL_PACKAGE):
                    if getattr(asset, "model_package_id", "") == model_version.version_id:
                        model_asset_id = asset.asset_id
                        break

            strategy_asset_id = register_strategy_asset(strategy.config, model_asset_id)
            if strategy_asset_id and model_asset_id:
                add_strategy_lineage(strategy_asset_id, model_asset_id)
        except Exception as e:
            logger.warning(f"Failed to auto-register Strategy asset: {e}")

        return strategy

    # ------------------------------------------------------------------
    # 便捷方法：从 Champion 构建
    # ------------------------------------------------------------------

    def build_from_champion(
        self,
        family: str,
        feature_set_id: str = "",
        symbol: str = "BTCUSDT",
        long_threshold: float = 0.02,
        position_mode: str = "confidence",
        max_position: float = 0.3,
        name: str = "",
        **kwargs,
    ) -> MLStrategyV2:
        """
        从 Champion 构建（推荐入口）

        Args:
            family: 模型族名（如 LGBM_Momentum）
            feature_set_id: FeatureSet ID
            symbol: 标的
            ...
        """
        registry = self._model_registry or get_model_registry()
        champion = registry.get_champion(family)
        if champion is None:
            raise ValueError(f"No champion for family: {family}")

        req = StrategyBuildRequest(
            model_version_id=champion.version_id,
            feature_set_id=feature_set_id,
            symbol=symbol,
            long_threshold=long_threshold,
            position_mode=position_mode,
            max_position=max_position,
            name=name or f"{family}_Strategy",
            tags=["ml", "champion", family.lower()],
            **kwargs,
        )
        return self.build(req)

    def build_from_version(
        self,
        version_id: str,
        feature_set_id: str = "",
        symbol: str = "BTCUSDT",
        **kwargs,
    ) -> MLStrategyV2:
        """从指定 ModelVersion 构建"""
        registry = self._model_registry or get_model_registry()
        version = registry.get_version(version_id)
        if version is None:
            raise ValueError(f"ModelVersion not found: {version_id}")

        req = StrategyBuildRequest(
            model_version_id=version_id,
            feature_set_id=feature_set_id,
            symbol=symbol,
            is_classifier=version.is_classifier,
            name=kwargs.pop("name", f"{version.name}_Strategy"),
            tags=["ml", version.family.lower()] if version.family else ["ml"],
            **kwargs,
        )
        return self.build(req)

    # ------------------------------------------------------------------
    # 管理
    # ------------------------------------------------------------------

    def get_strategy(self, strategy_id: str) -> Optional[MLStrategyV2]:
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> List[MLStrategyV2]:
        return list(self._strategies.values())

    def remove_strategy(self, strategy_id: str) -> bool:
        if strategy_id in self._strategies:
            self._strategies.pop(strategy_id)
            return True
        return False

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _resolve_model(
        self,
        req: StrategyBuildRequest,
    ):
        """解析模型来源"""
        # 1. 直接传入
        if req.model is not None:
            return req.model, None

        # 2. 从 ModelVersion 加载
        if req.model_version_id:
            registry = self._model_registry or get_model_registry()
            version = registry.get_version(req.model_version_id)
            if version is None:
                raise ValueError(f"ModelVersion not found: {req.model_version_id}")
            model = version.get_model()
            if model is None:
                logger.warning(
                    f"ModelVersion {req.model_version_id} has no model object, "
                    "strategy will predict zeros"
                )
            return model, version

        return None, None


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_builder: Optional[StrategyBuilder] = None


def get_strategy_builder() -> StrategyBuilder:
    """获取全局 StrategyBuilder 单例"""
    global _builder
    if _builder is None:
        _builder = StrategyBuilder()
    return _builder
