"""
Signal Package — 信号包

把信号生成逻辑从硬编码类升级为可注册、可复用的 Package。

5 种实现：
  - ThresholdSignal: 阈值信号（回归模型，pred > long_threshold → BUY）
  - ProbabilitySignal: 概率信号（分类模型专用）
  - TrendSignal: 趋势信号（MA 交叉）
  - RankingSignal: 排序信号（多品种横截面排序）
  - EnsembleSignal: 集成信号（多模型投票）— 暂未实现，预留

Signal 数据结构：
  Signal(symbol, side, score, prediction, timestamp, metadata)
  side: BUY / SELL / HOLD
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd

from ..base import AssetPackage, PackageType

logger = logging.getLogger("quantlab.asset_package.types.signal")


# ==================================================================
# Signal 数据结构
# ==================================================================

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


# ==================================================================
# SignalPackage 基类
# ==================================================================

@dataclass
class SignalPackage(AssetPackage):
    """信号包基类"""
    package_type: PackageType = PackageType.SIGNAL

    def generate(self, predictions: pd.Series, metadata: Optional[Dict] = None) -> List[Signal]:
        """
        根据模型预测值生成信号

        Args:
            predictions: 预测值序列（index=symbol/timestamp, values=预测值）
            metadata: 额外信息（如 model_id, timestamp）

        Returns:
            信号列表
        """
        raise NotImplementedError("Subclass must implement generate()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })


# ==================================================================
# 1. ThresholdSignal — 阈值信号
# ==================================================================

@dataclass
class ThresholdSignal(SignalPackage):
    """
    阈值信号（回归模型专用）

    pred > long_threshold  → BUY
    pred < short_threshold → SELL (if use_short)
    中间                    → HOLD
    """
    long_threshold: float = 0.02
    short_threshold: float = -0.02
    use_short: bool = True

    def to_config(self) -> Dict[str, Any]:
        return {
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.long_threshold = config.get("long_threshold", 0.02)
        self.short_threshold = config.get("short_threshold", -0.02)
        self.use_short = config.get("use_short", True)

    def generate(self, predictions: pd.Series, metadata: Optional[Dict] = None) -> List[Signal]:
        meta = metadata or {}
        timestamp = meta.get("timestamp", "")
        signals = []
        for symbol, pred in predictions.items():
            if pred > self.long_threshold:
                side = SignalSide.BUY
                score = min(1.0, (pred - self.long_threshold) / (abs(self.long_threshold) + 1e-9))
            elif self.use_short and pred < self.short_threshold:
                side = SignalSide.SELL
                score = min(1.0, (self.short_threshold - pred) / (abs(self.short_threshold) + 1e-9))
            else:
                side = SignalSide.HOLD
                score = 0.0
            signals.append(Signal(
                symbol=str(symbol),
                side=side,
                score=score,
                prediction=float(pred),
                timestamp=timestamp,
                metadata={"signal_type": "threshold", **meta},
            ))
        return signals


# ==================================================================
# 2. ProbabilitySignal — 概率信号
# ==================================================================

@dataclass
class ProbabilitySignal(SignalPackage):
    """
    概率信号（分类模型专用）

    pred >= buy_threshold  → BUY
    pred <= sell_threshold → SELL (if use_short)
    """
    buy_threshold: float = 0.72
    sell_threshold: float = 0.28
    use_short: bool = True

    def to_config(self) -> Dict[str, Any]:
        return {
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "use_short": self.use_short,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.buy_threshold = config.get("buy_threshold", 0.72)
        self.sell_threshold = config.get("sell_threshold", 0.28)
        self.use_short = config.get("use_short", True)

    def generate(self, predictions: pd.Series, metadata: Optional[Dict] = None) -> List[Signal]:
        meta = metadata or {}
        timestamp = meta.get("timestamp", "")
        signals = []
        for symbol, prob in predictions.items():
            if prob >= self.buy_threshold:
                side = SignalSide.BUY
                score = min(1.0, (prob - self.buy_threshold) / (1.0 - self.buy_threshold + 1e-9))
            elif self.use_short and prob <= self.sell_threshold:
                side = SignalSide.SELL
                score = min(1.0, (self.sell_threshold - prob) / (self.sell_threshold + 1e-9))
            else:
                side = SignalSide.HOLD
                score = 0.0
            signals.append(Signal(
                symbol=str(symbol),
                side=side,
                score=score,
                prediction=float(prob),
                timestamp=timestamp,
                metadata={"signal_type": "probability", **meta},
            ))
        return signals


# ==================================================================
# 3. TrendSignal — 趋势信号
# ==================================================================

@dataclass
class TrendSignal(SignalPackage):
    """
    趋势信号（MA 交叉）

    fast_ma > slow_ma → BUY
    fast_ma < slow_ma → SELL (if use_short)
    """
    fast_window: int = 5
    slow_window: int = 20
    use_short: bool = True

    def to_config(self) -> Dict[str, Any]:
        return {
            "fast_window": self.fast_window,
            "slow_window": self.slow_window,
            "use_short": self.use_short,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.fast_window = config.get("fast_window", 5)
        self.slow_window = config.get("slow_window", 20)
        self.use_short = config.get("use_short", True)

    def generate(self, predictions: pd.Series, metadata: Optional[Dict] = None) -> List[Signal]:
        """
        predictions 这里期望是价格序列（而非模型预测值）
        用于基于价格的 MA 交叉信号
        """
        meta = metadata or {}
        timestamp = meta.get("timestamp", "")
        signals = []
        # 单 symbol 的价格序列
        if isinstance(predictions, pd.DataFrame):
            # 多 symbol
            for symbol in predictions.columns:
                prices = predictions[symbol].dropna()
                if len(prices) < self.slow_window:
                    signals.append(Signal(symbol=str(symbol), side=SignalSide.HOLD,
                                          timestamp=timestamp, metadata={"signal_type": "trend", **meta}))
                    continue
                fast_ma = prices.rolling(self.fast_window).mean().iloc[-1]
                slow_ma = prices.rolling(self.slow_window).mean().iloc[-1]
                if fast_ma > slow_ma:
                    side = SignalSide.BUY
                    score = min(1.0, (fast_ma - slow_ma) / (slow_ma + 1e-9))
                elif self.use_short and fast_ma < slow_ma:
                    side = SignalSide.SELL
                    score = min(1.0, (slow_ma - fast_ma) / (slow_ma + 1e-9))
                else:
                    side = SignalSide.HOLD
                    score = 0.0
                signals.append(Signal(
                    symbol=str(symbol), side=side, score=score,
                    prediction=float(prices.iloc[-1]), timestamp=timestamp,
                    metadata={"signal_type": "trend", "fast_ma": float(fast_ma), "slow_ma": float(slow_ma), **meta},
                ))
        else:
            # 单 symbol
            prices = predictions.dropna()
            if len(prices) >= self.slow_window:
                fast_ma = prices.rolling(self.fast_window).mean().iloc[-1]
                slow_ma = prices.rolling(self.slow_window).mean().iloc[-1]
                if fast_ma > slow_ma:
                    side = SignalSide.BUY
                    score = min(1.0, (fast_ma - slow_ma) / (slow_ma + 1e-9))
                elif self.use_short and fast_ma < slow_ma:
                    side = SignalSide.SELL
                    score = min(1.0, (slow_ma - fast_ma) / (slow_ma + 1e-9))
                else:
                    side = SignalSide.HOLD
                    score = 0.0
                signals.append(Signal(
                    symbol=meta.get("symbol", ""), side=side, score=score,
                    prediction=float(prices.iloc[-1]), timestamp=timestamp,
                    metadata={"signal_type": "trend", **meta},
                ))
        return signals


# ==================================================================
# 4. RankingSignal — 排序信号
# ==================================================================

@dataclass
class RankingSignal(SignalPackage):
    """
    排序信号（多品种横截面排序）

    预测值排名前 top_pct → BUY
    预测值排名后 bottom_pct → SELL (if use_short)
    """
    top_pct: float = 0.2           # 前 20% 做多
    bottom_pct: float = 0.2        # 后 20% 做空
    use_short: bool = True

    def to_config(self) -> Dict[str, Any]:
        return {
            "top_pct": self.top_pct,
            "bottom_pct": self.bottom_pct,
            "use_short": self.use_short,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.top_pct = config.get("top_pct", 0.2)
        self.bottom_pct = config.get("bottom_pct", 0.2)
        self.use_short = config.get("use_short", True)

    def generate(self, predictions: pd.Series, metadata: Optional[Dict] = None) -> List[Signal]:
        meta = metadata or {}
        timestamp = meta.get("timestamp", "")
        if len(predictions) == 0:
            return []
        ranked = predictions.rank(ascending=False, method="min")
        n = len(predictions)
        top_n = max(1, int(n * self.top_pct))
        bottom_n = max(1, int(n * self.bottom_pct))
        signals = []
        for symbol, pred in predictions.items():
            rank = ranked[symbol]
            if rank <= top_n:
                side = SignalSide.BUY
                score = min(1.0, (n - rank + 1) / n)
            elif self.use_short and rank > n - bottom_n:
                side = SignalSide.SELL
                score = min(1.0, rank / n)
            else:
                side = SignalSide.HOLD
                score = 0.0
            signals.append(Signal(
                symbol=str(symbol), side=side, score=score,
                prediction=float(pred), timestamp=timestamp,
                metadata={"signal_type": "ranking", "rank": int(rank), "n": n, **meta},
            ))
        return signals
