"""
ML Strategy — 统一 ML 策略接口

ML Lab M5 第五部分：把 Champion Model 变成可执行的 ML Strategy

  流程：
    on_bar()
        ↓
    FeatureSet         (特征计算)
        ↓
    ChampionModel      (模型预测)
        ↓
    Prediction         (预测值)
        ↓
    SignalGenerator    (信号生成)
        ↓
    PositionSizer      (仓位计算)
        ↓
    RiskOverlay        (风控约束)
        ↓
    Order              (目标仓位)

  这样 ML 策略 和 RSI 策略 在运行时没有区别。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..feature import FeatureRegistry, FeatureSetRegistry, get_feature_registry, get_feature_set_registry
from ..model import Model, ModelType
from ..registry import ModelVersion, ModelRegistry, LifecycleStatus
from .signal_generator import SignalGenerator, SignalRule, Signal, SignalSide
from .position_sizer import PositionSizer, PositionSizeConfig, SizingMode
from .risk_overlay import RiskOverlay, RiskConfig

logger = logging.getLogger("quantlab.ml.strategy.ml_strategy")


# ------------------------------------------------------------------
# ML Strategy Config
# ------------------------------------------------------------------

@dataclass
class MLStrategyConfigV2:
    """
    ML 策略配置（M5 版本）

    包含完整的策略链：
        feature_set_id → model → signal_rule → position_config → risk_config
    """
    # 标识
    strategy_id: str = ""
    name: str = ""
    description: str = ""

    # 数据来源
    symbol: str = "BTCUSDT"
    feature_set_id: str = ""           # FeatureSet ID
    feature_ids: List[str] = field(default_factory=list)  # 兼容：直接指定特征

    # 模型
    model_version_id: str = ""         # ModelVersion ID（从 Registry 加载）
    model: Optional[Model] = None      # 直接传入模型对象

    # 信号规则
    signal_rule: SignalRule = field(default_factory=SignalRule)

    # 仓位配置
    position_config: PositionSizeConfig = field(default_factory=PositionSizeConfig)

    # 风控配置
    risk_config: RiskConfig = field(default_factory=RiskConfig)

    # 元信息
    tags: List[str] = field(default_factory=list)
    author: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "symbol": self.symbol,
            "feature_set_id": self.feature_set_id,
            "feature_ids": self.feature_ids,
            "model_version_id": self.model_version_id,
            "has_model": self.model is not None,
            "signal_rule": self.signal_rule.to_dict(),
            "position_config": self.position_config.to_dict(),
            "risk_config": self.risk_config.to_dict(),
            "tags": self.tags,
            "author": self.author,
            "version": self.version,
        }


# ------------------------------------------------------------------
# ML Strategy
# ------------------------------------------------------------------

class MLStrategyV2:
    """
    ML 策略（M5 版本）

    完整链路：
        on_bar() → FeatureSet → Model → Prediction → Signal → Position → Risk → Order

    用法：
        strategy = MLStrategyV2(
            config=config,
            model=champion_model,
        )
        strategy.set_feature_set_registry(fs_reg)

        # 单 bar
        order = strategy.on_bar(bar_df)

        # 批量回测
        result = strategy.backtest(df)
    """

    def __init__(
        self,
        config: MLStrategyConfigV2,
        model: Optional[Model] = None,
        model_version: Optional[ModelVersion] = None,
    ) -> None:
        self.config = config
        self.config.strategy_id = config.strategy_id or f"MLS-{uuid.uuid4().hex[:8]}"
        self.config.name = config.name or f"MLStrategy_{self.config.strategy_id}"

        # 模型来源：优先直接传入，其次从 version 获取
        self.model = model or (model_version.get_model() if model_version else None) or config.model
        self.model_version = model_version

        # 子组件
        self.signal_generator = SignalGenerator(rule=config.signal_rule)
        self.position_sizer = PositionSizer(config=config.position_config)
        self.risk_overlay = RiskOverlay(config=config.risk_config)

        # 注册表
        self._feature_registry: Optional[FeatureRegistry] = None
        self._feature_set_registry: Optional[FeatureSetRegistry] = None

        # 运行时状态
        self._last_signal: Optional[Signal] = None
        self._last_prediction: float = 0.0
        self._last_position: float = 0.0
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 注入注册表
    # ------------------------------------------------------------------

    def set_feature_registry(self, registry: FeatureRegistry) -> None:
        self._feature_registry = registry

    def set_feature_set_registry(self, registry: FeatureSetRegistry) -> None:
        self._feature_set_registry = registry

    def set_model(self, model: Model) -> None:
        self.model = model

    # ------------------------------------------------------------------
    # on_bar — 单 bar 决策
    # ------------------------------------------------------------------

    def on_bar(self, bar: pd.DataFrame, current_date: str = "") -> Dict[str, Any]:
        """
        单 bar 决策

        Args:
            bar: 单 bar 或多 bar 的 OHLCV 数据
            current_date: 当前日期（用于风控日亏重置）

        Returns:
            {
                "prediction": float,
                "signal": Signal,
                "raw_position": float,
                "final_position": float,
            }
        """
        # 1. 计算特征
        features = self._compute_features(bar)
        if features.empty or self.model is None:
            order = {
                "prediction": 0.0,
                "signal": Signal(symbol=self.config.symbol, side=SignalSide.HOLD),
                "raw_position": 0.0,
                "final_position": 0.0,
                "timestamp": current_date,
            }
            self._last_position = 0.0
            self._history.append(order)
            return order

        # 2. 模型预测
        try:
            pred = self.model.predict(features)
            prediction = float(pred.iloc[-1]) if hasattr(pred, "iloc") else float(pred)
        except Exception as e:
            logger.error(f"Predict failed: {e}")
            prediction = 0.0

        self._last_prediction = prediction

        # 3. 信号生成
        signal = self.signal_generator.generate(
            symbol=self.config.symbol,
            prediction=prediction,
            timestamp=current_date,
        )
        self._last_signal = signal

        # 4. 仓位计算
        raw_position = self.position_sizer.size(
            signal=signal,
            current_position=self._last_position,
        )

        # 5. 风控
        final_position = self.risk_overlay.apply(
            symbol=self.config.symbol,
            target_size=raw_position,
            current_date=current_date,
        )

        # 6. 记录
        self._last_position = final_position
        order = {
            "prediction": prediction,
            "signal": signal,
            "raw_position": raw_position,
            "final_position": final_position,
            "timestamp": current_date,
        }
        self._history.append(order)
        return order

    # ------------------------------------------------------------------
    # 批量回测
    # ------------------------------------------------------------------

    def backtest(
        self,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> Dict[str, Any]:
        """
        批量回测

        Args:
            df: OHLCV 数据
            initial_capital: 初始资金

        Returns:
            {
                "positions": pd.Series,
                "signals": pd.Series,
                "predictions": pd.Series,
                "equity_curve": pd.Series,
                "metrics": {...},
            }
        """
        # 计算特征
        features = self._compute_features(df)
        if features.empty or self.model is None:
            return self._empty_backtest_result(df)

        # 预测
        predictions = self.model.predict(features)
        if not isinstance(predictions, pd.Series):
            predictions = pd.Series(predictions, index=df.index)

        # 信号
        signals = self.signal_generator.to_signal_series(predictions)

        # 仓位（逐 bar 应用风控）
        positions: List[float] = []
        equity = initial_capital
        equity_curve: List[float] = []

        for i, (idx, pred) in enumerate(predictions.items()):
            signal = self.signal_generator.generate(
                symbol=self.config.symbol,
                prediction=float(pred),
                timestamp=str(idx),
            )
            raw_pos = self.position_sizer.size(
                signal=signal,
                current_position=positions[-1] if positions else 0.0,
            )
            final_pos = self.risk_overlay.apply(
                symbol=self.config.symbol,
                target_size=raw_pos,
                current_date=str(idx),
            )
            positions.append(final_pos)

            # 简单 PnL 计算
            if i > 0 and "close" in df.columns:
                ret = float(df["close"].iloc[i] / df["close"].iloc[i - 1] - 1.0)
                pnl = positions[-2] * ret * equity if i >= 1 else 0.0
                equity += pnl
                self.risk_overlay.record_pnl(pnl)
            equity_curve.append(equity)
            self.risk_overlay.update_equity(equity, current_date=str(idx))

        positions_series = pd.Series(positions, index=df.index, name="position")
        equity_series = pd.Series(equity_curve, index=df.index, name="equity")

        # 计算指标
        metrics = self._compute_metrics(positions_series, equity_series, df)

        return {
            "positions": positions_series,
            "signals": signals,
            "predictions": predictions,
            "equity_curve": equity_series,
            "metrics": metrics,
            "risk_status": self.risk_overlay.get_status(),
        }

    # ------------------------------------------------------------------
    # 内部：特征计算
    # ------------------------------------------------------------------

    def _compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算特征"""
        # 优先使用 FeatureSet
        if self.config.feature_set_id and self._feature_set_registry:
            fs = self._feature_set_registry.get(self.config.feature_set_id)
            if fs:
                try:
                    return fs.compute(df)
                except Exception as e:
                    logger.error(f"FeatureSet compute failed: {e}")

        # 兼容：直接指定 feature_ids
        if self.config.feature_ids:
            reg = self._feature_registry or get_feature_registry()
            try:
                feats = reg.compute_many(self.config.feature_ids, df)
                if not feats.empty:
                    return feats
                logger.warning(
                    f"compute_many returned empty for {self.config.feature_ids}, "
                    "falling back to derived features"
                )
            except Exception as e:
                logger.error(f"Feature compute failed: {e}")

        # 兜底：直接用原始数据（假设已经是特征）
        if {"open", "high", "low", "close", "volume"}.issubset(df.columns):
            # 用 close 衍生简单特征
            feats = pd.DataFrame(index=df.index)
            feats["returns"] = df["close"].pct_change()
            feats["volatility"] = feats["returns"].rolling(10).std()
            feats["momentum"] = df["close"].pct_change(5)
            feats = feats.fillna(0)
            return feats

        return df.copy()

    def _empty_backtest_result(self, df: pd.DataFrame) -> Dict[str, Any]:
        return {
            "positions": pd.Series(0, index=df.index, name="position"),
            "signals": pd.Series(0, index=df.index, name="signal"),
            "predictions": pd.Series(0, index=df.index, name="prediction"),
            "equity_curve": pd.Series(0, index=df.index, name="equity"),
            "metrics": {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0},
            "risk_status": self.risk_overlay.get_status(),
        }

    def _compute_metrics(
        self,
        positions: pd.Series,
        equity: pd.Series,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """计算回测指标"""
        if equity.empty or len(equity) < 2:
            return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        returns = equity.pct_change().dropna()
        sharpe = 0.0
        if returns.std() > 0:
            sharpe = float(returns.mean() / returns.std() * np.sqrt(252))

        # 最大回撤
        peak = equity.expanding().max()
        drawdown = (equity - peak) / peak
        max_dd = float(drawdown.min())

        # 胜率
        wins = int((returns > 0).sum())
        total = int((returns != 0).sum())
        win_rate = float(wins / total) if total > 0 else 0.0

        return {
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "n_bars": len(equity),
            "n_trades": int((positions.diff().abs() > 0.01).sum()),
            "final_equity": float(equity.iloc[-1]),
        }

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """获取策略状态"""
        return {
            "strategy_id": self.config.strategy_id,
            "name": self.config.name,
            "symbol": self.config.symbol,
            "has_model": self.model is not None,
            "last_prediction": self._last_prediction,
            "last_position": self._last_position,
            "last_signal": self._last_signal.to_dict() if self._last_signal else None,
            "risk_status": self.risk_overlay.get_status(),
            "n_history": len(self._history),
        }

    def get_history(self, n: int = 20) -> List[Dict[str, Any]]:
        """获取最近 N 条决策历史"""
        result = []
        for h in self._history[-n:]:
            item = h.copy()
            if isinstance(item.get("signal"), Signal):
                item["signal"] = item["signal"].to_dict()
            result.append(item)
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "has_model": self.model is not None,
            "model_version_id": self.model_version.version_id if self.model_version else "",
            "state": self.get_state(),
        }
