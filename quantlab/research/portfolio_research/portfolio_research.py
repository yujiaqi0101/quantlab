"""
Portfolio Research — Alpha 组合研究

与 Portfolio Builder 的区别：
  - Portfolio Builder: 多个策略组合
  - Portfolio Research: 多个 Alpha 组合（更底层）

三大核心：
  1. Alpha Weighting — 权重分配（IC Weight / Risk Parity / Equal）
  2. Alpha Contribution — 收益贡献归因
  3. Alpha Stability — IC 时序稳定性分析

用法：
    pr = PortfolioResearch(store)
    # 权重
    weights = pr.compute_weights(alpha_ids, method="ic_weight")
    # 贡献
    contrib = pr.compute_contribution(alpha_ids, returns_df)
    # 稳定性
    stability = pr.analyze_stability(alpha_id, ic_series)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha, AlphaMetrics
from ..alpha.store import AlphaStore

logger = logging.getLogger("quantlab.portfolio_research")


class PortfolioResearch:
    """
    Alpha 组合研究

    统一入口：
      - compute_weights()     权重分配
      - compute_contribution() 收益归因
      - analyze_stability()    稳定性分析
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()

    # ---- 1. Alpha Weighting ----

    def compute_weights(
        self,
        alpha_ids: List[str],
        method: str = "ic_weight",
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """
        计算 Alpha 权重

        方法:
          - "equal"        等权
          - "ic_weight"    IC 加权: w_i = IC_i / sum(IC)
          - "score_weight" 评分加权: w_i = score_i / sum(score)
          - "risk_parity"  风险平价: w_i ∝ 1/σ_i

        返回:
            {"weights": {"alpha_id": 0.3, ...}, "method": "ic_weight"}
        """
        alphas = []
        for aid in alpha_ids:
            a = self._store.get(aid)
            if a is not None:
                alphas.append(a)

        if not alphas:
            return {"weights": {}, "method": method}

        if method == "equal":
            weights = self._weight_equal(alphas)
        elif method == "ic_weight":
            weights = self._weight_ic(alphas)
        elif method == "score_weight":
            weights = self._weight_score(alphas)
        elif method == "risk_parity":
            weights = self._weight_risk_parity(alphas, signal_data)
        else:
            weights = self._weight_equal(alphas)

        return {
            "weights": weights,
            "method": method,
            "alpha_count": len(alphas),
        }

    def _weight_equal(self, alphas: List[Alpha]) -> Dict[str, float]:
        """等权"""
        n = len(alphas)
        w = 1.0 / n
        return {a.alpha_id: round(w, 4) for a in alphas}

    def _weight_ic(self, alphas: List[Alpha]) -> Dict[str, float]:
        """IC 加权"""
        ics = {a.alpha_id: abs(a.metrics.ic) for a in alphas}
        total = sum(ics.values())
        if total < 1e-9:
            return self._weight_equal(alphas)
        return {aid: round(ic / total, 4) for aid, ic in ics.items()}

    def _weight_score(self, alphas: List[Alpha]) -> Dict[str, float]:
        """评分加权"""
        scores = {a.alpha_id: max(a.metrics.score, 0) for a in alphas}
        total = sum(scores.values())
        if total < 1e-9:
            return self._weight_equal(alphas)
        return {aid: round(s / total, 4) for aid, s in scores.items()}

    def _weight_risk_parity(
        self,
        alphas: List[Alpha],
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, float]:
        """风险平价"""
        if signal_data is None:
            # 无信号数据时退化为 IC 加权
            return self._weight_ic(alphas)

        # 用信号波动率作为风险代理
        vols = {}
        for a in alphas:
            sig = signal_data.get(a.name)
            if sig is not None and sig.std() > 1e-9:
                vols[a.alpha_id] = sig.std()
            else:
                vols[a.alpha_id] = 1.0

        # w_i ∝ 1/σ_i
        inv_vols = {aid: 1.0 / v for aid, v in vols.items()}
        total = sum(inv_vols.values())
        return {aid: round(v / total, 4) for aid, v in inv_vols.items()}

    # ---- 2. Alpha Contribution ----

    def compute_contribution(
        self,
        alpha_ids: List[str],
        returns_df: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Alpha 收益贡献归因

        参数:
            alpha_ids    Alpha ID 列表
            returns_df   各 Alpha 的收益序列 (date × alpha_name)
            weights      权重（None 则等权）

        返回:
            {
                "total_return": 0.15,
                "contributions": [
                    {"alpha_id": "xxx", "name": "RSI14", "weight": 0.3, "contribution": 0.045, "pct": 30},
                    ...
                ]
            }
        """
        alphas = []
        for aid in alpha_ids:
            a = self._store.get(aid)
            if a is not None:
                alphas.append(a)

        if not alphas:
            return {"total_return": 0.0, "contributions": []}

        # 权重
        if weights is None:
            w = {a.alpha_id: 1.0 / len(alphas) for a in alphas}
        else:
            w = weights

        # 计算贡献
        contributions = []
        total_return = 0.0

        for alpha in alphas:
            col = alpha.name
            if col in returns_df.columns:
                alpha_ret = float(returns_df[col].sum())
            else:
                alpha_ret = 0.0

            weight = w.get(alpha.alpha_id, 0.0)
            contrib = alpha_ret * weight
            total_return += contrib

            contributions.append({
                "alpha_id": alpha.alpha_id,
                "name": alpha.name,
                "weight": weight,
                "return": round(alpha_ret, 6),
                "contribution": round(contrib, 6),
            })

        # 计算百分比
        for c in contributions:
            if abs(total_return) > 1e-9:
                c["pct"] = round(c["contribution"] / total_return * 100, 1)
            else:
                c["pct"] = 0.0

        # 排序
        contributions.sort(key=lambda x: x["contribution"], reverse=True)

        return {
            "total_return": round(total_return, 6),
            "contributions": contributions,
        }

    # ---- 3. Alpha Stability ----

    def analyze_stability(
        self,
        alpha_id: str,
        ic_series: Optional[pd.Series] = None,
        window: int = 60,
    ) -> Dict[str, Any]:
        """
        Alpha 稳定性分析

        分析 IC 时序的稳定性：
          - 滚动 IC 均值
          - 滚动 IC 标准差
          - IC 衰减检测
          - 稳定性评分

        参数:
            alpha_id   Alpha ID
            ic_series  IC 时序数据（None 则从 store 读取）
            window     滚动窗口

        返回:
            {
                "stability_score": 0.7,
                "ic_trend": "stable",  # stable / declining / improving
                "rolling_ic_mean": [...],
                "ic_by_year": {"2024": 0.08, "2025": -0.01},
                "half_life": 120,
            }
        """
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return {"error": f"Alpha '{alpha_id}' not found"}

        # IC 时序
        if ic_series is None:
            # 从 metrics 构造简化 IC 时序
            ic_series = self._generate_ic_series_from_metrics(alpha)

        if ic_series is None or len(ic_series) < 10:
            return {"error": "Insufficient IC data"}

        # 1. 滚动 IC
        rolling_mean = ic_series.rolling(window, min_periods=10).mean()
        rolling_std = ic_series.rolling(window, min_periods=10).std()

        # 2. IC 趋势
        ic_trend = self._detect_ic_trend(ic_series)

        # 3. 按年统计
        ic_by_year = self._ic_by_year(ic_series)

        # 4. 半衰期
        half_life = self._estimate_half_life(ic_series)

        # 5. 稳定性评分
        stability_score = self._compute_stability_score(ic_series, ic_trend)

        return {
            "alpha_id": alpha_id,
            "alpha_name": alpha.name,
            "stability_score": round(stability_score, 4),
            "ic_trend": ic_trend,
            "ic_mean": round(float(ic_series.mean()), 6),
            "ic_std": round(float(ic_series.std()), 6),
            "ic_positive_ratio": round(float((ic_series > 0).mean()), 4),
            "ic_by_year": {k: round(v, 6) for k, v in ic_by_year.items()},
            "half_life": half_life,
            "rolling_ic_mean": rolling_mean.dropna().to_dict(),
        }

    def _generate_ic_series_from_metrics(self, alpha: Alpha) -> Optional[pd.Series]:
        """从 metrics 生成模拟 IC 时序（简化版）"""
        m = alpha.metrics
        if m.ic == 0 and m.ic_std == 0:
            return None

        # 生成 252 个交易日的模拟 IC
        np.random.seed(hash(alpha.alpha_id) % 2**31)
        n = 252
        ic_values = np.random.normal(m.ic, max(m.ic_std, 0.01), n)
        dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
        return pd.Series(ic_values, index=dates)

    def _detect_ic_trend(self, ic_series: pd.Series) -> str:
        """检测 IC 趋势"""
        if len(ic_series) < 20:
            return "unknown"

        # 前半 vs 后半
        mid = len(ic_series) // 2
        first_half = ic_series.iloc[:mid].mean()
        second_half = ic_series.iloc[mid:].mean()

        diff = second_half - first_half
        ic_std = ic_series.std()

        if ic_std < 1e-9:
            return "stable"

        if diff > 0.5 * ic_std:
            return "improving"
        elif diff < -0.5 * ic_std:
            return "declining"
        else:
            return "stable"

    def _ic_by_year(self, ic_series: pd.Series) -> Dict[str, float]:
        """按年统计 IC"""
        if not isinstance(ic_series.index, pd.DatetimeIndex):
            return {}

        result = {}
        for year, group in ic_series.groupby(ic_series.index.year):
            result[str(year)] = float(group.mean())

        return result

    def _estimate_half_life(self, ic_series: pd.Series) -> Optional[int]:
        """估算 IC 半衰期（简化版）"""
        if len(ic_series) < 30:
            return None

        # 用自相关衰减估算
        autocorr = ic_series.autocorr(lag=1)
        if autocorr <= 0 or autocorr >= 1:
            return None

        # 半衰期 = -ln(2) / ln(autocorr)
        import math
        half_life = int(-math.log(2) / math.log(autocorr))
        return half_life

    def _compute_stability_score(self, ic_series: pd.Series, trend: str) -> float:
        """计算稳定性评分"""
        # 1. IC 正比率
        pos_ratio = float((ic_series > 0).mean())

        # 2. IC 变异系数
        ic_mean = abs(ic_series.mean())
        ic_std = ic_series.std()
        cv = ic_std / ic_mean if ic_mean > 1e-9 else 10.0

        # 3. 趋势惩罚
        trend_penalty = {"stable": 0, "improving": -0.1, "declining": 0.3, "unknown": 0.1}
        penalty = trend_penalty.get(trend, 0)

        # 综合评分
        score = pos_ratio * 0.5 + (1 - min(cv / 3, 1)) * 0.5 - penalty
        return max(0, min(1, score))
