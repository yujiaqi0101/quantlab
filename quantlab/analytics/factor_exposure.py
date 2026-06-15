"""
Factor Exposure Analyzer — V4.6 因子暴露分析

Portfolio + Factor Values → Momentum/Volatility/Size Exposure

例如：Momentum +0.82 表示策略严重偏向动量
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class FactorExposureAnalyzer:
    """
    因子暴露分析器

    用法：
        analyzer = FactorExposureAnalyzer()
        result = analyzer.analyze(weights, factor_values)
        # weights: {symbol: weight}
        # factor_values: {factor_name: {symbol: value}}
    """

    def analyze(
        self,
        weights: Dict[str, float],
        factor_values: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        """
        分析组合的因子暴露

        weights: 当前持仓权重 {symbol: weight}
        factor_values: 因子值 {factor_name: {symbol: value}}

        返回：每个因子的加权暴露
        """
        if not weights or not factor_values:
            return self._empty_result()

        exposures = {}
        for factor_name, sym_values in factor_values.items():
            exposure = self._compute_factor_exposure(weights, sym_values)
            exposures[factor_name] = round(exposure, 4)

        # 排序：绝对值最大的排前面
        sorted_exposures = sorted(
            exposures.items(), key=lambda x: abs(x[1]), reverse=True
        )

        # 分类：高暴露因子
        high_exposure = [(f, v) for f, v in sorted_exposures if abs(v) > 0.5]
        neutral_exposure = [(f, v) for f, v in sorted_exposures if 0.2 < abs(v) <= 0.5]
        low_exposure = [(f, v) for f, v in sorted_exposures if abs(v) <= 0.2]

        return {
            "factor_exposures": exposures,
            "sorted_exposures": sorted_exposures,
            "high_exposure": high_exposure,
            "neutral_exposure": neutral_exposure,
            "low_exposure": low_exposure,
            "dominant_factor": sorted_exposures[0][0] if sorted_exposures else None,
            "dominant_exposure": sorted_exposures[0][1] if sorted_exposures else 0,
        }

    def analyze_series(
        self,
        weights_history: Any,
        factor_values_series: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析时间序列的因子暴露

        weights_history: DataFrame(index=时间, columns=symbols)
        factor_values_series: {factor_name: DataFrame(index=时间, columns=symbols)}
        """
        if isinstance(weights_history, list):
            weights_history = pd.DataFrame(weights_history).fillna(0)

        if not isinstance(weights_history, pd.DataFrame):
            raise TypeError("weights_history must be DataFrame or list")

        results = {}
        for factor_name, fv_df in factor_values_series.items():
            if isinstance(fv_df, dict):
                fv_df = pd.DataFrame(fv_df).fillna(0)

            exposures = []
            for i in range(len(weights_history)):
                w = weights_history.iloc[i].to_dict()
                if i < len(fv_df):
                    fv = fv_df.iloc[i].to_dict()
                else:
                    fv = {}
                exp = self._compute_factor_exposure(w, fv)
                exposures.append(exp)

            results[factor_name] = {
                "mean": round(float(np.mean(exposures)), 4),
                "std": round(float(np.std(exposures)), 4),
                "min": round(float(min(exposures)), 4),
                "max": round(float(max(exposures)), 4),
                "current": round(exposures[-1], 4) if exposures else 0,
                "series": exposures,
            }

        return results

    def _compute_factor_exposure(
        self,
        weights: Dict[str, float],
        factor_values: Dict[str, float],
    ) -> float:
        """
        计算单个因子的加权暴露

        exposure = sum(weight_i * factor_value_i) / sum(|weight_i|)
        """
        total_weight = sum(abs(v) for v in weights.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for sym, w in weights.items():
            fv = factor_values.get(sym, 0)
            weighted_sum += w * fv

        return weighted_sum / total_weight

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "factor_exposures": {},
            "sorted_exposures": [],
            "high_exposure": [],
            "neutral_exposure": [],
            "low_exposure": [],
            "dominant_factor": None,
            "dominant_exposure": 0,
        }
