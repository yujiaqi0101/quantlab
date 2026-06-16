"""
Alpha Correlation — Alpha 间相关性分析

功能：
  - 计算候选 Alpha 之间的相关性矩阵
  - 识别高度相关的 Alpha（冗余）
  - 生成 Heatmap 数据
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .alpha import Alpha
from .store import AlphaStore

logger = logging.getLogger("quantlab.alpha.correlation")


class AlphaCorrelation:
    """
    Alpha 相关性分析

    用法：
        corr = AlphaCorrelation(store)
        matrix = corr.compute_correlation(signal_data)
        redundant = corr.find_redundant(matrix, threshold=0.8)
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()

    def compute_correlation(
        self,
        signal_data: Dict[str, pd.Series],
        method: str = "spearman",
    ) -> pd.DataFrame:
        """
        计算 Alpha 间相关性矩阵

        参数:
            signal_data  {alpha_name: signal_series}
            method       "spearman" 或 "pearson"

        返回:
            DataFrame(index=alpha_name, columns=alpha_name)
        """
        if not signal_data:
            return pd.DataFrame()

        df = pd.DataFrame(signal_data)
        corr_matrix = df.corr(method=method)
        return corr_matrix

    def compute_from_alphas(
        self,
        alphas: List[Alpha],
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        从 Alpha 列表计算相关性

        先生成每个 Alpha 的信号，再计算相关性矩阵
        """
        from .evaluator import AlphaEvaluator

        evaluator = AlphaEvaluator()
        signal_data: Dict[str, pd.Series] = {}

        for alpha in alphas:
            fv = factor_data.get(alpha.factor_name)
            if fv is None:
                continue
            signals = evaluator._generate_signals(alpha, fv)
            if signals is not None and not signals.empty:
                signal_data[alpha.name] = signals

        return self.compute_correlation(signal_data)

    def find_redundant(
        self,
        corr_matrix: pd.DataFrame,
        threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        找出高度相关的 Alpha 对

        参数:
            corr_matrix  相关性矩阵
            threshold    相关性阈值

        返回:
            [{"alpha_1": "RSI14_LT_30", "alpha_2": "Stoch_LT_20", "correlation": 0.92}, ...]
        """
        redundant = []
        names = corr_matrix.columns.tolist()

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                val = corr_matrix.iloc[i, j]
                if abs(val) >= threshold:
                    redundant.append({
                        "alpha_1": names[i],
                        "alpha_2": names[j],
                        "correlation": round(float(val), 4),
                    })

        redundant.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        return redundant

    def get_heatmap_data(
        self,
        corr_matrix: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        生成 Heatmap 可视化数据

        返回:
            {"labels": [...], "matrix": [[...], ...]}
        """
        labels = corr_matrix.columns.tolist()
        matrix = corr_matrix.values.tolist()

        # 转 float 并处理 NaN
        clean_matrix = []
        for row in matrix:
            clean_row = []
            for val in row:
                if np.isnan(val):
                    clean_row.append  (0.0)
                else:
                    clean_row.append(round(float(val), 4))
            clean_matrix.append(clean_row)

        return {
            "labels": labels,
            "matrix": clean_matrix,
        }

    def deduplicate(
        self,
        alphas: List[Alpha],
        corr_matrix: pd.DataFrame,
        threshold: float = 0.8,
        keep_metric: str = "score",
    ) -> List[Alpha]:
        """
        去重：高度相关的 Alpha 只保留评分更高的那个

        参数:
            alphas       Alpha 列表
            corr_matrix  相关性矩阵
            threshold    相关性阈值
            keep_metric  保留指标（score/ic/ir）

        返回:
            去重后的 Alpha 列表
        """
        redundant = self.find_redundant(corr_matrix, threshold)
        remove_ids = set()

        alpha_map = {a.name: a for a in alphas}

        for pair in redundant:
            a1_name, a2_name = pair["alpha_1"], pair["alpha_2"]
            a1 = alpha_map.get(a1_name)
            a2 = alpha_map.get(a2_name)

            if a1 is None or a2 is None:
                continue

            # 保留评分更高的
            s1 = getattr(a1.metrics, keep_metric, 0)
            s2 = getattr(a2.metrics, keep_metric, 0)

            if s1 >= s2:
                remove_ids.add(a2.alpha_id)
            else:
                remove_ids.add(a1.alpha_id)

        result = [a for a in alphas if a.alpha_id not in remove_ids]
        logger.info(f"deduplicated: {len(alphas)} → {len(result)} alphas (removed {len(remove_ids)})")
        return result
