"""
Turnover Analyzer — V4.6 换手率分析

换手率 = |weight_t - weight_{t-1}| 之和 / 2

为什么重要：Sharpe 2.0 + 年换手 3000% = 实盘跑不了
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class TurnoverAnalyzer:
    """
    换手率分析器

    用法：
        analyzer = TurnoverAnalyzer()
        result = analyzer.analyze(weights_history)
        # weights_history: List[Dict[symbol, weight]] 或 DataFrame
    """

    def analyze(
        self,
        weights_history: Any,
        prices: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """
        分析换手率

        weights_history:
          - List[Dict[symbol, weight]]: 每 bar 的权重
          - DataFrame(index=时间, columns=symbols): 权重矩阵
        """
        if isinstance(weights_history, pd.DataFrame):
            return self._analyze_df(weights_history, prices)
        elif isinstance(weights_history, list):
            return self._analyze_list(weights_history, prices)
        else:
            raise TypeError(f"unsupported type: {type(weights_history)}")

    def _analyze_df(
        self,
        df: pd.DataFrame,
        prices: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        turnovers = []
        for i in range(1, len(df)):
            prev = df.iloc[i - 1].fillna(0)
            curr = df.iloc[i].fillna(0)
            turnover = (curr - prev).abs().sum() / 2
            turnovers.append(turnover)

        if not turnovers:
            return self._empty_result()

        daily_avg = np.mean(turnovers)
        annual = daily_avg * 252

        return {
            "daily_turnover_avg": round(float(daily_avg), 4),
            "daily_turnover_max": round(float(max(turnovers)), 4),
            "daily_turnover_min": round(float(min(turnovers)), 4),
            "annual_turnover": round(float(annual), 2),
            "total_turnover": round(float(sum(turnovers)), 4),
            "n_rebalances": sum(1 for t in turnovers if t > 0.001),
            "turnover_series": turnovers,
        }

    def _analyze_list(
        self,
        weights_list: List[Dict[str, float]],
        prices: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        turnovers = []
        for i in range(1, len(weights_list)):
            prev = weights_list[i - 1]
            curr = weights_list[i]
            all_syms = set(list(prev.keys()) + list(curr.keys()))
            turnover = sum(abs(curr.get(s, 0) - prev.get(s, 0)) for s in all_syms) / 2
            turnovers.append(turnover)

        if not turnovers:
            return self._empty_result()

        daily_avg = np.mean(turnovers)
        annual = daily_avg * 252

        return {
            "daily_turnover_avg": round(float(daily_avg), 4),
            "daily_turnover_max": round(float(max(turnovers)), 4),
            "daily_turnover_min": round(float(min(turnovers)), 4),
            "annual_turnover": round(float(annual), 2),
            "total_turnover": round(float(sum(turnovers)), 4),
            "n_rebalances": sum(1 for t in turnovers if t > 0.001),
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "daily_turnover_avg": 0.0,
            "daily_turnover_max": 0.0,
            "daily_turnover_min": 0.0,
            "annual_turnover": 0.0,
            "total_turnover": 0.0,
            "n_rebalances": 0,
        }
