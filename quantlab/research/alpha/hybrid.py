"""
Hybrid Alpha — 选股 + 择时混合 Alpha

流程：
  1. 截面选股（Cross Section）：MomentumRank Top 100
  2. 时序择时（Time Series）：RSI < 30
  3. 组合信号：选出的股票 + 择时信号 → 最终交易

这是很多机构实际在做的：
  先选股 → 再择时 → 最终交易

用法：
    hybrid = HybridAlpha()
    result = hybrid.evaluate(
        cross_section_signal=cs_df,   # DataFrame(date × symbol): 截面排序信号
        time_series_signal=ts_df,     # DataFrame(date × symbol): 时序择时信号
        forward_returns=ret_df,       # DataFrame(date × symbol): 前瞻收益
        top_n=50,                     # 截面选 Top N
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha, AlphaMetrics, ResearchMode

logger = logging.getLogger("quantlab.alpha.hybrid")


class HybridAlpha:
    """
    混合 Alpha 评估器

    选股 + 择时 = 最终信号
    """

    def __init__(self) -> None:
        pass

    def evaluate(
        self,
        cross_section_signal: pd.DataFrame,
        time_series_signal: pd.DataFrame,
        forward_returns: pd.DataFrame,
        top_n: int = 50,
        top_pct: Optional[float] = None,
        combine_method: str = "and",
    ) -> Dict[str, Any]:
        """
        混合评估

        参数:
            cross_section_signal  截面信号 (date × symbol)，值越大越好
            time_series_signal    时序信号 (date × symbol)，1=做多, -1=做空, 0=无
            forward_returns       前瞻收益 (date × symbol)
            top_n                 截面选 Top N
            top_pct               截面选 Top %（与 top_n 二选一）
            combine_method        组合方法: "and" / "or"

        返回:
            {
                "final_signal": DataFrame,
                "metrics": AlphaMetrics,
                "cross_section_stats": {...},
                "time_series_stats": {...},
            }
        """
        # 对齐
        common_idx = cross_section_signal.index.intersection(
            time_series_signal.index
        ).intersection(forward_returns.index)
        common_cols = cross_section_signal.columns.intersection(
            time_series_signal.columns
        ).intersection(forward_returns.columns)

        cs = cross_section_signal.loc[common_idx, common_cols]
        ts = time_series_signal.loc[common_idx, common_cols]
        ret = forward_returns.loc[common_idx, common_cols]

        if cs.empty:
            return {"error": "No overlapping data"}

        # 1. 截面选股
        selected = self._select_top(cs, top_n, top_pct)

        # 2. 组合信号
        if combine_method == "and":
            # 选中的 AND 择时做多
            final = selected & (ts > 0)
        elif combine_method == "or":
            # 选中的 OR 择时做多
            final = selected | (ts > 0)
        else:
            final = selected & (ts > 0)

        final_signal = final.astype(int)

        # 3. 计算收益
        strategy_returns = self._compute_strategy_returns(final_signal, ret)

        # 4. 计算指标
        metrics = self._compute_metrics(final_signal, ret, strategy_returns)

        # 5. 分阶段统计
        cs_stats = self._compute_selection_stats(selected, ret)
        ts_stats = self._compute_timing_stats(ts, ret)

        return {
            "final_signal_shape": final_signal.shape,
            "metrics": metrics.to_dict(),
            "cross_section_stats": cs_stats,
            "time_series_stats": ts_stats,
            "strategy_returns": {
                "mean": float(strategy_returns.mean()),
                "sharpe": float(strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)) if strategy_returns.std() > 1e-9 else 0.0,
                "win_rate": float((strategy_returns > 0).mean()),
            },
        }

    def _select_top(
        self,
        cs: pd.DataFrame,
        top_n: int = 50,
        top_pct: Optional[float] = None,
    ) -> pd.DataFrame:
        """截面选股：选 Top N 或 Top %"""
        selected = pd.DataFrame(False, index=cs.index, columns=cs.columns)

        for date in cs.index:
            row = cs.loc[date].dropna()
            if len(row) == 0:
                continue

            if top_pct is not None:
                n = max(1, int(len(row) * top_pct))
            else:
                n = min(top_n, len(row))

            top_symbols = row.nlargest(n).index
            selected.loc[date, top_symbols] = True

        return selected

    def _compute_strategy_returns(
        self,
        signal: pd.DataFrame,
        ret: pd.DataFrame,
    ) -> pd.Series:
        """计算策略收益"""
        daily_rets = []
        for date in signal.index:
            s = signal.loc[date]
            r = ret.loc[date]
            held = s[s > 0].index
            if len(held) > 0:
                daily_rets.append(float(r[held].mean()))
            else:
                daily_rets.append(0.0)

        return pd.Series(daily_rets, index=signal.index)

    def _compute_metrics(
        self,
        signal: pd.DataFrame,
        ret: pd.DataFrame,
        strategy_returns: pd.Series,
    ) -> AlphaMetrics:
        """计算综合指标"""
        metrics = AlphaMetrics()

        # 覆盖率
        metrics.coverage = float((signal > 0).any(axis=1).mean())

        # 收益
        metrics.forward_ret_1d = float(strategy_returns.mean())

        # Sharpe
        if strategy_returns.std() > 1e-9:
            metrics.sharpe = float(strategy_returns.mean() / strategy_returns.std() * np.sqrt(252))

        # 胜率
        metrics.win_rate = float((strategy_returns > 0).mean())

        # IC（简化：用信号与收益的相关性）
        ic_list = []
        for date in signal.index:
            s = signal.loc[date]
            r = ret.loc[date]
            common = s[s > 0].index.intersection(r.dropna().index)
            if len(common) > 2:
                # 选中股票的平均收益 vs 全市场平均收益
                selected_ret = r[common].mean()
                all_ret = r.dropna().mean()
                ic_list.append(1.0 if selected_ret > all_ret else -1.0)

        if ic_list:
            metrics.ic = float(np.mean(ic_list))
            metrics.ic_positive_ratio = float(np.mean([x > 0 for x in ic_list]))

        # 评分
        metrics.score = self._compute_score(metrics)

        return metrics

    def _compute_selection_stats(
        self,
        selected: pd.DataFrame,
        ret: pd.DataFrame,
    ) -> Dict[str, Any]:
        """截面选股统计"""
        rets = []
        for date in selected.index:
            s = selected.loc[date]
            held = s[s].index
            if len(held) > 0:
                rets.append(float(ret.loc[date, held].mean()))

        return {
            "avg_selected": int(selected.sum(axis=1).mean()),
            "avg_return": float(np.mean(rets)) if rets else 0.0,
        }

    def _compute_timing_stats(
        self,
        ts: pd.DataFrame,
        ret: pd.DataFrame,
    ) -> Dict[str, Any]:
        """时序择时统计"""
        long_rets = []
        for date in ts.index:
            t = ts.loc[date]
            r = ret.loc[date]
            long = t[t > 0].index.intersection(r.dropna().index)
            if len(long) > 0:
                long_rets.append(float(r[long].mean()))

        return {
            "avg_long_pct": float((ts > 0).sum().sum() / (ts.shape[0] * ts.shape[1])),
            "avg_long_return": float(np.mean(long_rets)) if long_rets else 0.0,
        }

    def _compute_score(self, metrics: AlphaMetrics) -> float:
        score = (
            0.3 * min(abs(metrics.sharpe) / 2.0, 1.0)
            + 0.3 * min(abs(metrics.ic) / 0.05, 1.0)
            + 0.2 * min(metrics.win_rate / 0.55, 1.0)
            + 0.2 * min(abs(metrics.forward_ret_1d) / 0.01, 1.0)
        )
        return round(score, 4)
