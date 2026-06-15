"""
Exposure Analyzer — V4.6 暴露分析

Long Exposure / Short Exposure / Gross Exposure / Net Exposure
"""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd


class ExposureAnalyzer:
    """
    暴露分析器

    用法：
        analyzer = ExposureAnalyzer()
        result = analyzer.analyze(weights_history)
    """

    def analyze(
        self,
        weights_history: Any,
    ) -> Dict[str, Any]:
        """
        分析暴露

        weights_history: DataFrame(index=时间, columns=symbols) 或 List[Dict]
        """
        if isinstance(weights_history, pd.DataFrame):
            return self._analyze_df(weights_history)
        elif isinstance(weights_history, list):
            return self._analyze_list(weights_history)
        raise TypeError(f"unsupported type: {type(weights_history)}")

    def _analyze_df(self, df: pd.DataFrame) -> Dict[str, Any]:
        long_exp = []
        short_exp = []
        gross_exp = []
        net_exp = []

        for i in range(len(df)):
            row = df.iloc[i].fillna(0)
            longs = row[row > 0].sum()
            shorts = row[row < 0].abs().sum()
            long_exp.append(longs)
            short_exp.append(shorts)
            gross_exp.append(longs + shorts)
            net_exp.append(longs - shorts)

        return {
            "long_exposure_avg": round(float(np.mean(long_exp)), 4),
            "long_exposure_max": round(float(max(long_exp)) if long_exp else 0, 4),
            "short_exposure_avg": round(float(np.mean(short_exp)), 4),
            "short_exposure_max": round(float(max(short_exp)) if short_exp else 0, 4),
            "gross_exposure_avg": round(float(np.mean(gross_exp)), 4),
            "gross_exposure_max": round(float(max(gross_exp)) if gross_exp else 0, 4),
            "net_exposure_avg": round(float(np.mean(net_exp)), 4),
            "net_exposure_min": round(float(min(net_exp)) if net_exp else 0, 4),
        }

    def _analyze_list(self, weights_list: List[Dict[str, float]]) -> Dict[str, Any]:
        long_exp = []
        short_exp = []
        gross_exp = []
        net_exp = []

        for w in weights_list:
            longs = sum(v for v in w.values() if v > 0)
            shorts = sum(abs(v) for v in w.values() if v < 0)
            long_exp.append(longs)
            short_exp.append(shorts)
            gross_exp.append(longs + shorts)
            net_exp.append(longs - shorts)

        return {
            "long_exposure_avg": round(float(np.mean(long_exp)), 4),
            "long_exposure_max": round(float(max(long_exp)) if long_exp else 0, 4),
            "short_exposure_avg": round(float(np.mean(short_exp)), 4),
            "short_exposure_max": round(float(max(short_exp)) if short_exp else 0, 4),
            "gross_exposure_avg": round(float(np.mean(gross_exp)), 4),
            "gross_exposure_max": round(float(max(gross_exp)) if gross_exp else 0, 4),
            "net_exposure_avg": round(float(np.mean(net_exp)), 4),
            "net_exposure_min": round(float(min(net_exp)) if net_exp else 0, 4),
        }

    def analyze_single(self, weights: Dict[str, float]) -> Dict[str, float]:
        """分析单根 bar 的暴露"""
        longs = sum(v for v in weights.values() if v > 0)
        shorts = sum(abs(v) for v in weights.values() if v < 0)
        return {
            "long_exposure": round(longs, 4),
            "short_exposure": round(shorts, 4),
            "gross_exposure": round(longs + shorts, 4),
            "net_exposure": round(longs - shorts, 4),
        }
