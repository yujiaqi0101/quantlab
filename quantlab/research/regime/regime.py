"""
Regime Analysis — 市场状态识别 + Alpha 环境适应性

核心思想：
  Alpha 死掉往往不是因为 Alpha 错了，而是市场环境变了。

功能：
  1. 市场状态识别（Bull / Bear / Sideways）
  2. Alpha 在不同环境下的表现
  3. Alpha 适用环境判断

用法：
    regime = RegimeAnalyzer()
    # 识别市场状态
    states = regime.identify_regimes(price_df)
    # 分析 Alpha 在不同环境下的表现
    result = regime.analyze_alpha_performance(alpha, price_df, factor_values)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha, AlphaMetrics
from ..alpha.store import AlphaStore

logger = logging.getLogger("quantlab.regime")


class MarketRegime:
    """市场状态枚举"""
    BULL = "bull"         # 牛市
    BEAR = "bear"         # 熊市
    SIDEWAYS = "sideways" # 震荡
    CRISIS = "crisis"     # 危机


class RegimeAnalyzer:
    """
    市场状态分析器

    1. 识别市场状态
    2. 分析 Alpha 在不同环境下的表现
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()

    # ---- 1. 市场状态识别 ----

    def identify_regimes(
        self,
        price_df: pd.DataFrame,
        window: int = 60,
        method: str = "trend_volatility",
    ) -> Dict[str, Any]:
        """
        识别市场状态

        参数:
            price_df  价格数据 (date × close) 或 (date × [open, high, low, close, volume])
            window    滚动窗口
            method    识别方法

        返回:
            {
                "regimes": [{"date": "2024-01-01", "regime": "bull", "confidence": 0.8}, ...],
                "summary": {"bull": 120, "bear": 80, "sideways": 65},
                "current": "bull",
            }
        """
        if isinstance(price_df, pd.DataFrame):
            if "close" in price_df.columns:
                close = price_df["close"]
            else:
                close = price_df.iloc[:, 0]
        else:
            close = price_df

        # 计算收益
        returns = close.pct_change().dropna()

        # 滚动统计
        rolling_ret = returns.rolling(window, min_periods=20).mean() * 252  # 年化
        rolling_vol = returns.rolling(window, min_periods=20).std() * np.sqrt(252)  # 年化

        # 识别状态
        regimes = []
        for date in rolling_ret.index:
            ret = rolling_ret.loc[date]
            vol = rolling_vol.loc[date]

            if np.isnan(ret) or np.isnan(vol):
                continue

            regime, confidence = self._classify_regime(ret, vol)
            regimes.append({
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "regime": regime,
                "confidence": round(confidence, 4),
                "annualized_return": round(ret, 6),
                "annualized_volatility": round(vol, 6),
            })

        # 统计
        summary: Dict[str, int] = {}
        for r in regimes:
            key = r["regime"]
            summary[key] = summary.get(key, 0) + 1

        # 当前状态
        current = regimes[-1]["regime"] if regimes else "unknown"

        return {
            "regimes": regimes,
            "summary": summary,
            "current": current,
            "window": window,
        }

    def _classify_regime(self, annualized_return: float, annualized_vol: float) -> Tuple[str, float]:
        """
        分类市场状态

        规则:
          - Bull:   年化收益 > 10%, 波动率 < 30%
          - Bear:   年化收益 < -10%
          - Crisis: 年化收益 < -10% 且 波动率 > 40%
          - Sideways: 其他
        """
        if annualized_return > 0.10 and annualized_vol < 0.30:
            confidence = min((annualized_return - 0.10) / 0.20 + (0.30 - annualized_vol) / 0.15, 1.0)
            return (MarketRegime.BULL, max(0.5, confidence))

        elif annualized_return < -0.10 and annualized_vol > 0.40:
            confidence = min((abs(annualized_return) - 0.10) / 0.20 + (annualized_vol - 0.40) / 0.20, 1.0)
            return (MarketRegime.CRISIS, max(0.5, confidence))

        elif annualized_return < -0.10:
            confidence = min(abs(annualized_return) / 0.30, 1.0)
            return (MarketRegime.BEAR, max(0.5, confidence))

        else:
            # 震荡
            if abs(annualized_return) < 0.05:
                confidence = min((0.05 - abs(annualized_return)) / 0.05, 1.0)
            else:
                confidence = 0.5
            return (MarketRegime.SIDEWAYS, max(0.3, confidence))

    # ---- 2. Alpha 环境适应性 ----

    def analyze_alpha_performance(
        self,
        alpha: Alpha,
        price_df: pd.DataFrame,
        factor_values: Optional[pd.Series] = None,
        window: int = 60,
    ) -> Dict[str, Any]:
        """
        分析 Alpha 在不同市场环境下的表现

        返回:
            {
                "alpha_name": "RSI14_LT_30",
                "regime_performance": {
                    "bull": {"sharpe": 2.1, "win_rate": 0.65, "return": 0.15, "days": 120},
                    "bear": {"sharpe": -0.5, "win_rate": 0.40, "return": -0.08, "days": 80},
                    "sideways": {"sharpe": 0.3, "win_rate": 0.52, "return": 0.02, "days": 65},
                },
                "best_regime": "bull",
                "worst_regime": "bear",
                "adaptability_score": 0.6,
            }
        """
        # 1. 识别市场状态
        regime_data = self.identify_regimes(price_df, window)
        regimes = regime_data["regimes"]

        if not regimes:
            return {"error": "Could not identify regimes"}

        # 2. 生成信号
        if factor_values is not None:
            signals = self._generate_signals(alpha, factor_values)
        else:
            # 无因子数据时，用简化信号
            signals = pd.Series(0, index=price_df.index[:len(regimes)])

        # 3. 计算收益
        if isinstance(price_df, pd.DataFrame):
            if "close" in price_df.columns:
                close = price_df["close"]
            else:
                close = price_df.iloc[:, 0]
        else:
            close = price_df

        returns = close.pct_change().dropna()

        # 4. 按环境分组统计
        regime_perf: Dict[str, Dict[str, Any]] = {}

        for r in regimes:
            date_str = r["date"]
            regime = r["regime"]

            # 找到对应日期的收益
            try:
                if isinstance(returns.index, pd.DatetimeIndex):
                    date_ts = pd.Timestamp(date_str)
                    if date_ts not in returns.index:
                        continue
                    daily_ret = returns.loc[date_ts]
                    signal = signals.get(date_ts, 0) if date_ts in signals.index else 0
                else:
                    continue
            except (KeyError, TypeError):
                continue

            if regime not in regime_perf:
                regime_perf[regime] = {
                    "returns": [],
                    "signal_returns": [],
                    "days": 0,
                }

            regime_perf[regime]["returns"].append(float(daily_ret))
            regime_perf[regime]["signal_returns"].append(float(daily_ret) * float(signal))
            regime_perf[regime]["days"] += 1

        # 5. 汇总
        result = {}
        for regime, data in regime_perf.items():
            rets = data["returns"]
            sig_rets = data["signal_returns"]

            if not rets:
                continue

            mean_ret = float(np.mean(rets))
            std_ret = float(np.std(rets))
            sharpe = mean_ret / std_ret * np.sqrt(252) if std_ret > 1e-9 else 0.0
            win_rate = float(np.mean([r > 0 for r in sig_rets])) if sig_rets else 0.0

            result[regime] = {
                "sharpe": round(sharpe, 4),
                "win_rate": round(win_rate, 4),
                "return": round(mean_ret * 252, 6),
                "days": data["days"],
            }

        # 6. 最佳/最差环境
        best_regime = max(result, key=lambda k: result[k].get("sharpe", 0)) if result else "unknown"
        worst_regime = min(result, key=lambda k: result[k].get("sharpe", 0)) if result else "unknown"

        # 7. 适应性评分
        adaptability = self._compute_adaptability(result)

        return {
            "alpha_id": alpha.alpha_id,
            "alpha_name": alpha.name,
            "regime_performance": result,
            "best_regime": best_regime,
            "worst_regime": worst_regime,
            "adaptability_score": round(adaptability, 4),
        }

    def analyze_alpha_batch(
        self,
        alpha_ids: List[str],
        price_df: pd.DataFrame,
        factor_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """批量分析 Alpha 环境适应性"""
        results = []
        for aid in alpha_ids:
            alpha = self._store.get(aid)
            if alpha is None:
                continue

            fv = None
            if factor_data:
                fv = factor_data.get(alpha.factor_name)

            result = self.analyze_alpha_performance(alpha, price_df, fv)
            if "error" not in result:
                results.append(result)

        # 排序：适应性评分最高的在前
        results.sort(key=lambda x: x.get("adaptability_score", 0), reverse=True)

        return {
            "total": len(results),
            "results": results,
        }

    def get_regime_summary(
        self,
        price_df: pd.DataFrame,
        window: int = 60,
    ) -> Dict[str, Any]:
        """获取市场状态摘要"""
        return self.identify_regimes(price_df, window)

    # ---- 内部方法 ----

    def _generate_signals(self, alpha: Alpha, factor_values: pd.Series) -> pd.Series:
        """生成信号"""
        signals = pd.Series(0.0, index=factor_values.index)

        if alpha.alpha_type.value == "threshold":
            if alpha.lower is not None:
                signals[factor_values < alpha.lower] = 1.0
            if alpha.upper is not None:
                signals[factor_values > alpha.upper] = -1.0

        elif alpha.alpha_type.value == "zero_cross":
            signals[factor_values > 0] = 1.0
            signals[factor_values < 0] = -1.0

        return signals

    def _compute_adaptability(self, regime_perf: Dict[str, Dict[str, Any]]) -> float:
        """
        计算适应性评分

        评分逻辑：
          - 在所有环境下都能盈利 → 高适应性
          - 只在特定环境盈利 → 低适应性
        """
        if not regime_perf:
            return 0.0

        sharpes = [v.get("sharpe", 0) for v in regime_perf.values()]
        if not sharpes:
            return 0.0

        # 正 Sharpe 比例
        positive_ratio = sum(1 for s in sharpes if s > 0) / len(sharpes)

        # Sharpe 方差（越小越稳定）
        sharpe_std = float(np.std(sharpes))
        sharpe_range = max(sharpes) - min(sharpes) if sharpes else 0

        # 综合评分
        score = positive_ratio * 0.6 + (1 - min(sharpe_range / 3.0, 1.0)) * 0.4

        return max(0, min(1, score))
