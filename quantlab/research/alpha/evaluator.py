"""
Alpha Evaluator — Alpha 评估核心

自动计算每个 Alpha 的：
  IC / Rank IC / IR
  Coverage（覆盖率）
  Turnover（换手率）
  Forward Return（前瞻收益 1D/5D/10D/20D）
  Win Rate（胜率）
  Sharpe（夏普比率）
  Score（综合评分）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import Alpha, AlphaMetrics, AlphaType

logger = logging.getLogger("quantlab.alpha.evaluator")


class AlphaEvaluator:
    """
    Alpha 评估器

    输入：Alpha + 数据集
    输出：AlphaMetrics

    用法：
        evaluator = AlphaEvaluator()
        metrics = evaluator.evaluate(alpha, factor_df, price_df)
    """

    # 综合评分权重
    DEFAULT_WEIGHTS = {
        "ic": 0.30,
        "ir": 0.30,
        "sharpe": 0.20,
        "stability": 0.20,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()

    def evaluate(
        self,
        alpha: Alpha,
        factor_values: pd.Series,
        price_df: pd.DataFrame,
    ) -> AlphaMetrics:
        """
        评估单个 Alpha

        参数:
            alpha         Alpha 对象
            factor_values 因子值 Series (index=时间)
            price_df      价格 DataFrame (columns: close 等)

        返回:
            AlphaMetrics
        """
        # 1. 生成信号
        signals = self._generate_signals(alpha, factor_values)

        if signals is None or signals.empty:
            return AlphaMetrics()

        # 2. 计算前瞻收益
        close = price_df["close"] if "close" in price_df.columns else price_df.iloc[:, 0]
        forward_rets = self._compute_forward_returns(close)

        # 3. 计算各项指标
        metrics = AlphaMetrics()

        # Coverage
        metrics.coverage = float((signals != 0).mean())

        # Forward Return
        metrics.forward_ret_1d = self._signal_forward_return(signals, forward_rets.get(1))
        metrics.forward_ret_5d = self._signal_forward_return(signals, forward_rets.get(5))
        metrics.forward_ret_10d = self._signal_forward_return(signals, forward_rets.get(10))
        metrics.forward_ret_20d = self._signal_forward_return(signals, forward_rets.get(20))

        # IC / Rank IC
        ic_data = self._compute_ic(factor_values, forward_rets.get(1))
        metrics.ic = ic_data["ic"]
        metrics.rank_ic = ic_data["rank_ic"]
        metrics.ir = ic_data["ir"]
        metrics.ic_std = ic_data["ic_std"]
        metrics.ic_positive_ratio = ic_data["ic_positive_ratio"]
        metrics.ic_t_stat = ic_data["ic_t_stat"]

        # Turnover
        metrics.turnover = self._compute_turnover(signals)

        # Win Rate
        metrics.win_rate = self._compute_win_rate(signals, forward_rets.get(1))

        # Sharpe
        metrics.sharpe = self._compute_sharpe(signals, forward_rets.get(1))

        # Trade Count
        metrics.trade_count = self._count_trades(signals)

        # Score
        metrics.score = self._compute_score(metrics)

        return metrics

    def evaluate_batch(
        self,
        alphas: List[Alpha],
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
    ) -> Dict[str, AlphaMetrics]:
        """
        批量评估

        参数:
            alphas       Alpha 列表
            factor_data  {factor_name: Series}
            price_df     价格 DataFrame

        返回:
            {alpha_id: AlphaMetrics}
        """
        results: Dict[str, AlphaMetrics] = {}
        for alpha in alphas:
            fv = factor_data.get(alpha.factor_name)
            if fv is None:
                logger.warning(f"factor '{alpha.factor_name}' not in factor_data, skip alpha '{alpha.name}'")
                results[alpha.alpha_id] = AlphaMetrics()
                continue
            results[alpha.alpha_id] = self.evaluate(alpha, fv, price_df)
        logger.info(f"evaluated {len(results)} alphas")
        return results

    # ---- 信号生成 ----

    def _generate_signals(
        self,
        alpha: Alpha,
        factor_values: pd.Series,
    ) -> Optional[pd.Series]:
        """根据 Alpha 规则生成信号"""
        if alpha.alpha_type == AlphaType.THRESHOLD:
            return self._threshold_signal(factor_values, alpha.lower, alpha.upper)
        elif alpha.alpha_type == AlphaType.ZERO_CROSS:
            return self._zero_cross_signal(factor_values)
        elif alpha.alpha_type == AlphaType.CROSSOVER:
            # 交叉型需要第二个因子，这里简化为零轴
            return self._zero_cross_signal(factor_values)
        elif alpha.alpha_type == AlphaType.COMPOSITE:
            # 组合型需要多个因子值，返回空
            return None
        return None

    def _threshold_signal(
        self,
        factor_values: pd.Series,
        lower: Optional[float],
        upper: Optional[float],
    ) -> pd.Series:
        """阈值信号"""
        signal = pd.Series(0, index=factor_values.index, dtype=float)

        if lower is not None:
            signal[factor_values < lower] = 1
        if upper is not None:
            signal[factor_values > upper] = -1

        return signal

    def _zero_cross_signal(self, factor_values: pd.Series) -> pd.Series:
        """零轴穿越信号"""
        signal = pd.Series(0, index=factor_values.index, dtype=float)
        signal[factor_values > 0] = 1
        signal[factor_values < 0] = -1
        return signal

    # ---- 前瞻收益 ----

    def _compute_forward_returns(
        self,
        close: pd.Series,
        periods: Optional[List[int]] = None,
    ) -> Dict[int, pd.Series]:
        """计算前瞻收益"""
        if periods is None:
            periods = [1, 5, 10, 20]

        result: Dict[int, pd.Series] = {}
        for p in periods:
            result[p] = close.shift(-p) / close - 1
        return result

    def _signal_forward_return(
        self,
        signals: pd.Series,
        forward_ret: Optional[pd.Series],
    ) -> float:
        """信号触发时的平均前瞻收益"""
        if forward_ret is None or signals.empty:
            return 0.0

        long_mask = signals == 1
        if long_mask.sum() == 0:
            return 0.0

        aligned = forward_ret.reindex(signals.index)
        rets = aligned[long_mask].dropna()
        if rets.empty:
            return 0.0

        return round(float(rets.mean()), 6)

    # ---- IC ----

    def _compute_ic(
        self,
        factor_values: pd.Series,
        forward_ret: Optional[pd.Series],
    ) -> Dict[str, float]:
        """计算 IC / Rank IC / IR"""
        result = {
            "ic": 0.0, "rank_ic": 0.0, "ir": 0.0,
            "ic_std": 0.0, "ic_positive_ratio": 0.0, "ic_t_stat": 0.0,
        }

        if forward_ret is None:
            return result

        # 逐期 IC（滚动窗口）
        window = 20
        aligned_factor = factor_values.reindex(forward_ret.index).dropna()
        aligned_ret = forward_ret.reindex(aligned_factor.index).dropna()

        if len(aligned_factor) < window + 1:
            return result

        ic_list = []
        rank_ic_list = []
        for i in range(window, len(aligned_factor)):
            f_window = aligned_factor.iloc[i - window:i]
            r_window = aligned_ret.iloc[i - window:i]
            if len(f_window) < 5:
                continue
            try:
                ic_val = f_window.corr(r_window, method="pearson")
                ric_val = f_window.corr(r_window, method="spearman")
                if not np.isnan(ic_val):
                    ic_list.append(ic_val)
                if not np.isnan(ric_val):
                    rank_ic_list.append(ric_val)
            except Exception:
                continue

        if ic_list:
            ic_arr = np.array(ic_list)
            result["ic"] = round(float(np.mean(ic_arr)), 4)
            result["ic_std"] = round(float(np.std(ic_arr)), 4)
            result["ic_positive_ratio"] = round(float((ic_arr > 0).mean()), 4)
            if result["ic_std"] > 1e-9:
                result["ir"] = round(result["ic"] / result["ic_std"], 4)
                result["ic_t_stat"] = round(result["ic"] / (result["ic_std"] / np.sqrt(len(ic_arr))), 4)

        if rank_ic_list:
            result["rank_ic"] = round(float(np.mean(rank_ic_list)), 4)

        return result

    # ---- Turnover ----

    def _compute_turnover(self, signals: pd.Series) -> float:
        """信号换手率"""
        if len(signals) < 2:
            return 0.0
        changes = (signals.diff().abs() > 0).sum()
        return round(float(changes / (len(signals) - 1)), 4)

    # ---- Win Rate ----

    def _compute_win_rate(
        self,
        signals: pd.Series,
        forward_ret: Optional[pd.Series],
    ) -> float:
        """胜率（信号触发后盈利的比例）"""
        if forward_ret is None:
            return 0.0

        aligned = forward_ret.reindex(signals.index)
        long_mask = signals == 1
        rets = aligned[long_mask].dropna()
        if rets.empty:
            return 0.0

        return round(float((rets > 0).mean()), 4)

    # ---- Sharpe ----

    def _compute_sharpe(
        self,
        signals: pd.Series,
        forward_ret: Optional[pd.Series],
    ) -> float:
        """信号策略 Sharpe"""
        if forward_ret is None:
            return 0.0

        aligned = forward_ret.reindex(signals.index)
        strategy_ret = aligned * signals.reindex(aligned.index)
        strategy_ret = strategy_ret.dropna()
        if strategy_ret.empty or strategy_ret.std() < 1e-9:
            return 0.0

        return round(float(strategy_ret.mean() / strategy_ret.std() * np.sqrt(252)), 3)

    # ---- Trade Count ----

    def _count_trades(self, signals: pd.Series) -> int:
        """交易次数"""
        if signals.empty:
            return 0
        entries = ((signals == 1) & (signals.shift(1) != 1)).sum()
        return int(entries)

    # ---- Score ----

    def _compute_score(self, metrics: AlphaMetrics) -> float:
        """
        综合评分

        score = w_ic * normalize(ic) + w_ir * normalize(ir) + w_sharpe * normalize(sharpe) + w_stability * normalize(stability)
        """
        w = self._weights

        # 归一化到 [0, 1] 区间
        ic_score = min(max(metrics.ic / 0.1, 0), 1)       # IC=0.1 → 满分
        ir_score = min(max(metrics.ir / 1.0, 0), 1)       # IR=1.0 → 满分
        sharpe_score = min(max(metrics.sharpe / 2.0, 0), 1)  # Sharpe=2.0 → 满分
        # stability = ic_positive_ratio
        stability_score = metrics.ic_positive_ratio

        score = (
            w.get("ic", 0.3) * ic_score
            + w.get("ir", 0.3) * ir_score
            + w.get("sharpe", 0.2) * sharpe_score
            + w.get("stability", 0.2) * stability_score
        )

        return round(float(score), 4)
