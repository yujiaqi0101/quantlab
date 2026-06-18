"""
Regime Validator — 市场状态验证

ML Lab M3 第四部分：专业量化才做的事

  市场状态：
    Bull     牛市
    Bear     熊市
    Sideways 震荡

  验证模型在不同市场状态下的表现：
    Bull Sharpe
    Bear Sharpe
    Sideways Sharpe

  发现：模型适用于什么市场
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.validation.regime")


class MarketRegime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"


@dataclass
class RegimeStat:
    """单一市场状态统计"""
    regime: str
    n_samples: int = 0
    ic: float = 0.0
    rank_ic: float = 0.0
    sharpe: float = 0.0
    return_mean: float = 0.0
    return_std: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "n_samples": self.n_samples,
            "ic": round(self.ic, 6),
            "rank_ic": round(self.rank_ic, 6),
            "sharpe": round(self.sharpe, 6),
            "return_mean": round(self.return_mean, 6),
            "return_std": round(self.return_std, 6),
        }


@dataclass
class RegimeResult:
    """市场状态验证结果"""
    stats: List[RegimeStat] = field(default_factory=list)
    bull_sharpe: float = 0.0
    bear_sharpe: float = 0.0
    sideways_sharpe: float = 0.0
    # 模型适用市场
    best_regime: str = ""
    worst_regime: str = ""
    # 一致性：各市场 IC 是否同号
    consistent: bool = False
    # 评级
    grade: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats": [s.to_dict() for s in self.stats],
            "bull_sharpe": round(self.bull_sharpe, 6),
            "bear_sharpe": round(self.bear_sharpe, 6),
            "sideways_sharpe": round(self.sideways_sharpe, 6),
            "best_regime": self.best_regime,
            "worst_regime": self.worst_regime,
            "consistent": self.consistent,
            "grade": self.grade,
        }


class RegimeValidator:
    """
    市场状态验证器

  用法：
        validator = RegimeValidator()
        result = validator.validate(predictions, label, price)
        print(f"Bull Sharpe: {result.bull_sharpe}")
    """

    def __init__(
        self,
        bull_threshold: float = 0.05,   # 年化收益 > 5% 视为牛市
        bear_threshold: float = -0.05,  # 年化收益 < -5% 视为熊市
        window: int = 63,               # 识别窗口（约 3 个月）
    ) -> None:
        self.bull_threshold = bull_threshold
        self.bear_threshold = bear_threshold
        self.window = window

    def classify_regime(self, returns: pd.Series) -> pd.Series:
        """
        根据滚动收益分类市场状态

        Args:
            returns: 收益率序列

        Returns:
            市场状态序列（BULL/BEAR/SIDEWAYS）
        """
        if len(returns) < self.window:
            return pd.Series("SIDEWAYS", index=returns.index)

        # 滚动年化收益
        rolling_ret = returns.rolling(self.window).mean() * 252
        regime = pd.Series("SIDEWAYS", index=returns.index)
        regime[rolling_ret > self.bull_threshold] = MarketRegime.BULL.value
        regime[rolling_ret < self.bear_threshold] = MarketRegime.BEAR.value
        return regime

    def validate(
        self,
        predictions: pd.Series,
        label: pd.Series,
        price: Optional[pd.Series] = None,
    ) -> RegimeResult:
        """
        验证不同市场状态下的表现

        Args:
            predictions: 预测信号
            label: 真实收益（或用 price 计算收益）
            price: 价格序列（可选，若提供则用其计算收益分类市场）
        """
        result = RegimeResult()

        common_idx = predictions.index.intersection(label.index)
        if len(common_idx) == 0:
            return result
        preds = predictions.loc[common_idx]
        y = label.loc[common_idx]

        # 分类市场状态
        if price is not None:
            common_p = common_idx.intersection(price.index)
            if len(common_p) > 0:
                returns = price.loc[common_p].pct_change()
                regime = self.classify_regime(returns)
                regime = regime.loc[common_idx]
            else:
                regime = pd.Series("SIDEWAYS", index=common_idx)
        else:
            # 用 label 作为收益代理
            regime = self.classify_regime(y)

        # 按市场状态分组统计
        stats: List[RegimeStat] = []
        for regime_name in [MarketRegime.BULL.value, MarketRegime.BEAR.value, MarketRegime.SIDEWAYS.value]:
            mask = (regime == regime_name) & preds.notna() & y.notna()
            if mask.sum() < 5:
                stats.append(RegimeStat(regime=regime_name, n_samples=int(mask.sum())))
                continue

            yp = preds[mask]
            yl = y[mask]
            strategy_ret = yp * yl

            stat = RegimeStat(
                regime=regime_name,
                n_samples=int(mask.sum()),
                ic=float(yp.corr(yl)) if yp.std() > 0 else 0.0,
                rank_ic=float(yp.corr(yl, method="spearman")) if yp.std() > 0 else 0.0,
                sharpe=float(
                    strategy_ret.mean() / strategy_ret.std() * np.sqrt(252)
                ) if strategy_ret.std() > 0 else 0.0,
                return_mean=float(strategy_ret.mean()),
                return_std=float(strategy_ret.std()),
            )
            stats.append(stat)

        result.stats = stats
        for s in stats:
            if s.regime == MarketRegime.BULL.value:
                result.bull_sharpe = s.sharpe
            elif s.regime == MarketRegime.BEAR.value:
                result.bear_sharpe = s.sharpe
            elif s.regime == MarketRegime.SIDEWAYS.value:
                result.sideways_sharpe = s.sharpe

        # 最优/最差市场
        valid_stats = [s for s in stats if s.n_samples >= 5]
        if valid_stats:
            best = max(valid_stats, key=lambda s: s.sharpe)
            worst = min(valid_stats, key=lambda s: s.sharpe)
            result.best_regime = best.regime
            result.worst_regime = worst.regime

            # 一致性：所有市场 IC 同号
            ics = [s.ic for s in valid_stats]
            if all(i > 0 for i in ics) or all(i < 0 for i in ics):
                result.consistent = True

        result.grade = self._compute_grade(result)
        return result

    def _compute_grade(self, result: RegimeResult) -> str:
        """评级：基于各市场 Sharpe 的一致性"""
        sharpes = [result.bull_sharpe, result.bear_sharpe, result.sideways_sharpe]
        positive_count = sum(1 for s in sharpes if s > 0)

        if positive_count == 3 and result.consistent:
            return "A"
        elif positive_count >= 2:
            return "B"
        elif positive_count == 1:
            return "C"
        else:
            return "F"
