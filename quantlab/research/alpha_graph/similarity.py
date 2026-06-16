"""
Alpha Similarity — 多维相似度

计算 Alpha 之间的相似度，支持：
  - 信号相似度（信号序列相关性）
  - 收益相似度（前瞻收益相关性）
  - IC 相似度（IC 序列相关性）
  - 基因组相似度（结构相似度）

综合相似度 = 加权平均
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha
from ..alpha.store import AlphaStore
from .genome import AlphaGenome

logger = logging.getLogger("quantlab.alpha_graph.similarity")


class AlphaSimilarity:
    """
    Alpha 相似度计算

    用法：
        sim = AlphaSimilarity(store)
        result = sim.compute(alpha1, alpha2, signal_data)
        # result = {"signal_sim": 0.94, "ic_sim": 0.88, "genome_sim": 0.85, "overall": 0.90}
    """

    DEFAULT_WEIGHTS = {
        "signal": 0.4,
        "ic": 0.3,
        "genome": 0.3,
    }

    def __init__(
        self,
        store: Optional[AlphaStore] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self._store = store or AlphaStore()
        self._weights = weights or self.DEFAULT_WEIGHTS.copy()

    def compute(
        self,
        alpha1: Alpha,
        alpha2: Alpha,
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """
        计算两个 Alpha 的多维相似度

        参数:
            alpha1, alpha2  Alpha 对象
            signal_data     {alpha_name: signal_series}（可选，用于信号相似度）

        返回:
            {"signal_sim": 0.94, "ic_sim": 0.88, "genome_sim": 0.85, "overall": 0.90}
        """
        result: Dict[str, Any] = {}

        # 1. 信号相似度
        signal_sim = 0.0
        if signal_data:
            s1 = signal_data.get(alpha1.name)
            s2 = signal_data.get(alpha2.name)
            if s1 is not None and s2 is not None:
                signal_sim = self._series_similarity(s1, s2)
        result["signal_sim"] = round(signal_sim, 4)

        # 2. IC 相似度
        ic_sim = 0.0
        m1, m2 = alpha1.metrics, alpha2.metrics
        if m1.ic != 0 or m2.ic != 0:
            # 用 IC 绝对差值归一化
            ic_diff = abs(m1.ic - m2.ic)
            ic_sim = max(0, 1 - ic_diff / 0.1)  # IC 差 0.1 → 相似度 0
        result["ic_sim"] = round(ic_sim, 4)

        # 3. 基因组相似度
        g1 = AlphaGenome.from_alpha(alpha1)
        g2 = AlphaGenome.from_alpha(alpha2)
        genome_diff = g1.diff(g2)
        genome_sim = genome_diff["similarity"]
        result["genome_sim"] = round(genome_sim, 4)
        result["genome_diff"] = genome_diff

        # 4. 综合相似度
        w = self._weights
        overall = (
            w.get("signal", 0.4) * signal_sim
            + w.get("ic", 0.3) * ic_sim
            + w.get("genome", 0.3) * genome_sim
        )
        result["overall"] = round(overall, 4)

        result["alpha_1"] = alpha1.name
        result["alpha_2"] = alpha2.name

        return result

    def compute_matrix(
        self,
        alphas: List[Alpha],
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> pd.DataFrame:
        """
        计算相似度矩阵

        返回:
            DataFrame(index=alpha_name, columns=alpha_name)
        """
        n = len(alphas)
        names = [a.name for a in alphas]
        matrix = np.zeros((n, n))

        for i in range(n):
            matrix[i, i] = 1.0
            for j in range(i + 1, n):
                sim = self.compute(alphas[i], alphas[j], signal_data)
                val = sim["overall"]
                matrix[i, j] = val
                matrix[j, i] = val

        return pd.DataFrame(matrix, index=names, columns=names)

    def find_similar(
        self,
        target_alpha: Alpha,
        alphas: List[Alpha],
        threshold: float = 0.8,
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> List[Dict[str, Any]]:
        """
        找出与目标 Alpha 相似的其他 Alpha

        参数:
            target_alpha  目标 Alpha
            alphas        候选 Alpha 列表
            threshold     相似度阈值

        返回:
            [{"alpha_name": "RSI21_LT_25", "similarity": 0.94}, ...]
        """
        similar = []
        for alpha in alphas:
            if alpha.alpha_id == target_alpha.alpha_id:
                continue
            sim = self.compute(target_alpha, alpha, signal_data)
            if sim["overall"] >= threshold:
                similar.append({
                    "alpha_id": alpha.alpha_id,
                    "alpha_name": alpha.name,
                    "similarity": sim["overall"],
                    "signal_sim": sim["signal_sim"],
                    "genome_sim": sim["genome_sim"],
                })

        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar

    def _series_similarity(self, s1: pd.Series, s2: pd.Series) -> float:
        """计算两个信号序列的相似度"""
        # 对齐索引
        common_idx = s1.index.intersection(s2.index)
        if len(common_idx) < 5:
            return 0.0

        a = s1.reindex(common_idx).fillna(0)
        b = s2.reindex(common_idx).fillna(0)

        # 用相关系数作为相似度
        corr = a.corr(b)
        if np.isnan(corr):
            return 0.0

        # 相关系数 [-1, 1] → 相似度 [0, 1]
        return (corr + 1) / 2
