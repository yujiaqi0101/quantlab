"""
Signal Generator — 信号生成器

ML Lab M5 第二部分：Prediction → Signal

  模型只负责预测：
    y_pred = model.predict(X)  →  0.83 或 +2.4%

  但预测 ≠ 交易，中间还需要一层信号生成：
    pred > 0.02  →  BUY
    pred < -0.02 →  SELL
    中间          →  HOLD

  Signal 结构：
    symbol
    side       (BUY/SELL/HOLD)
    score      (置信度 0~1)
    timestamp
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.strategy.signal")


# ------------------------------------------------------------------
# 信号类型
# ------------------------------------------------------------------

class SignalSide(str, Enum):
    """信号方向"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """交易信号"""
    symbol: str = ""
    side: SignalSide = SignalSide.HOLD
    score: float = 0.0           # 置信度 0~1（|score| 越大越强）
    prediction: float = 0.0      # 原始预测值
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """是否为有效信号（非 HOLD）"""
        return self.side != SignalSide.HOLD

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side.value,
            "score": float(self.score),
            "prediction": float(self.prediction),
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


# ------------------------------------------------------------------
# 信号生成规则
# ------------------------------------------------------------------

@dataclass
class SignalRule:
    """
    信号生成规则

    回归模型：
        pred > long_threshold  → BUY
        pred < short_threshold → SELL (if use_short)
        中间                    → HOLD

    分类模型：
        pred == 2 (Up)    → BUY
        pred == 0 (Down)  → SELL (if use_short)
        else              → HOLD
    """
    long_threshold: float = 0.02       # 多头阈值
    short_threshold: float = -0.02     # 空头阈值
    use_short: bool = False            # 是否允许做空
    is_classifier: bool = False        # 是否分类模型
    # 置信度计算
    score_mode: str = "tanh"           # tanh / linear / softmax
    score_scale: float = 1.0           # 置信度缩放

    def to_dict(self) -> Dict[str, Any]:
        return {
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
            "is_classifier": self.is_classifier,
            "score_mode": self.score_mode,
            "score_scale": self.score_scale,
        }


# ------------------------------------------------------------------
# Signal Generator
# ------------------------------------------------------------------

class SignalGenerator:
    """
    信号生成器

    用法：
        gen = SignalGenerator(rule=SignalRule(long_threshold=0.02))
        signal = gen.generate(symbol="BTC", prediction=0.05)
        # → Signal(side=BUY, score=0.95)

        # 批量生成
        signals = gen.generate_batch(symbol="BTC", predictions=pred_series)
    """

    def __init__(self, rule: Optional[SignalRule] = None) -> None:
        self.rule = rule or SignalRule()

    def set_rule(self, rule: SignalRule) -> None:
        self.rule = rule

    # ------------------------------------------------------------------
    # 单条信号
    # ------------------------------------------------------------------

    def generate(
        self,
        symbol: str,
        prediction: float,
        timestamp: str = "",
        metadata: Optional[Dict] = None,
    ) -> Signal:
        """生成单条信号"""
        side = self._decide_side(prediction)
        score = self._compute_score(prediction, side)

        return Signal(
            symbol=symbol,
            side=side,
            score=score,
            prediction=float(prediction),
            timestamp=timestamp,
            metadata=metadata or {},
        )

    # ------------------------------------------------------------------
    # 批量信号
    # ------------------------------------------------------------------

    def generate_batch(
        self,
        symbol: str,
        predictions: pd.Series,
        timestamps: Optional[pd.Series] = None,
    ) -> List[Signal]:
        """批量生成信号"""
        signals: List[Signal] = []
        for i, pred in enumerate(predictions):
            ts = ""
            if timestamps is not None and i < len(timestamps):
                ts = str(timestamps.iloc[i])
            signals.append(self.generate(symbol, float(pred), ts))
        return signals

    def generate_series(
        self,
        symbol: str,
        predictions: pd.Series,
    ) -> pd.DataFrame:
        """
        生成信号 DataFrame

        返回：
            timestamp  side  score  prediction
        """
        rows = []
        for idx, pred in predictions.items():
            sig = self.generate(symbol, float(pred), str(idx))
            rows.append({
                "timestamp": idx,
                "side": sig.side.value,
                "score": sig.score,
                "prediction": sig.prediction,
            })
        return pd.DataFrame(rows).set_index("timestamp")

    def to_signal_series(self, predictions: pd.Series) -> pd.Series:
        """转为信号序列（1/0/-1）"""
        if self.rule.is_classifier:
            signals = pd.Series(0, index=predictions.index, dtype=int)
            signals[predictions == 2] = 1
            if self.rule.use_short:
                signals[predictions == 0] = -1
            return signals

        signals = pd.Series(0, index=predictions.index, dtype=int)
        signals[predictions > self.rule.long_threshold] = 1
        if self.rule.use_short:
            signals[predictions < self.rule.short_threshold] = -1
        return signals

    # ------------------------------------------------------------------
    # 内部：决策与打分
    # ------------------------------------------------------------------

    def _decide_side(self, prediction: float) -> SignalSide:
        """根据预测值决定方向"""
        if self.rule.is_classifier:
            # 分类：2=Up, 0=Down, 1=Neutral
            if prediction == 2:
                return SignalSide.BUY
            if prediction == 0 and self.rule.use_short:
                return SignalSide.SELL
            return SignalSide.HOLD

        # 回归
        if prediction > self.rule.long_threshold:
            return SignalSide.BUY
        if prediction < self.rule.short_threshold and self.rule.use_short:
            return SignalSide.SELL
        return SignalSide.HOLD

    def _compute_score(self, prediction: float, side: SignalSide) -> float:
        """计算置信度（0~1）"""
        if side == SignalSide.HOLD:
            return 0.0

        if self.rule.score_mode == "tanh":
            # tanh 平滑映射
            val = abs(prediction) * self.rule.score_scale
            return float(np.tanh(val))

        if self.rule.score_mode == "linear":
            # 线性映射，截断到 [0, 1]
            threshold = (
                self.rule.long_threshold if side == SignalSide.BUY
                else abs(self.rule.short_threshold)
            )
            val = (abs(prediction) - threshold) * self.rule.score_scale
            return float(max(0.0, min(1.0, val)))

        if self.rule.score_mode == "softmax":
            # 简化 softmax：|pred| / (1 + |pred|)
            val = abs(prediction) * self.rule.score_scale
            return float(val / (1.0 + val))

        # 默认 tanh
        return float(np.tanh(abs(prediction) * self.rule.score_scale))


# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def signals_to_dataframe(signals: List[Signal]) -> pd.DataFrame:
    """信号列表转 DataFrame"""
    return pd.DataFrame([s.to_dict() for s in signals])


def summarize_signals(signals: List[Signal]) -> Dict[str, Any]:
    """信号统计"""
    total = len(signals)
    buys = sum(1 for s in signals if s.side == SignalSide.BUY)
    sells = sum(1 for s in signals if s.side == SignalSide.SELL)
    holds = sum(1 for s in signals if s.side == SignalSide.HOLD)
    active = buys + sells
    return {
        "total": total,
        "buy": buys,
        "sell": sells,
        "hold": holds,
        "active": active,
        "active_ratio": float(active / total) if total > 0 else 0.0,
        "avg_score": float(np.mean([s.score for s in signals])) if signals else 0.0,
    }
