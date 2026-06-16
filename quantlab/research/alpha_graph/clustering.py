"""
Alpha Cluster — Alpha 聚类

将 Alpha 聚类为家族：
  Cluster 1: RSI Family
  Cluster 2: Momentum Family
  Cluster 3: Volume Family

支持：
  - KMeans 聚类
  - 层次聚类
  - 自动确定簇数
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha, AlphaMetrics
from ..alpha.store import AlphaStore
from .genome import AlphaGenome

logger = logging.getLogger("quantlab.alpha_graph.clustering")


class AlphaCluster:
    """
    Alpha 聚类器

    用法：
        cluster = AlphaCluster(store)
        result = cluster.cluster(alphas, n_clusters=5)
        # result = {"clusters": [{"name": "RSI Family", "alphas": [...], "centroid": {...}}, ...]}
    """

    def __init__(self, store: Optional[AlphaStore] = None) -> None:
        self._store = store or AlphaStore()

    def cluster(
        self,
        alphas: Optional[List[Alpha]] = None,
        n_clusters: Optional[int] = None,
        method: str = "kmeans",
    ) -> Dict[str, Any]:
        """
        聚类 Alpha

        参数:
            alphas      Alpha 列表，None 则从 store 加载候选
            n_clusters  簇数，None 则自动确定
            method      聚类方法: "kmeans" / "hierarchical" / "genome"

        返回:
            {"clusters": [...], "n_clusters": 5, "method": "kmeans"}
        """
        if alphas is None:
            alphas = self._store.list_alphas(status="candidate", limit=1000)

        if not alphas:
            return {"clusters": [], "n_clusters": 0, "method": method}

        # 特征矩阵
        feature_matrix, alpha_names = self._build_feature_matrix(alphas)

        if feature_matrix.shape[0] < 2:
            return {
                "clusters": [{"name": "Single", "alphas": [a.to_dict() for a in alphas], "size": len(alphas)}],
                "n_clusters": 1,
                "method": method,
            }

        # 自动确定簇数
        if n_clusters is None:
            n_clusters = self._estimate_n_clusters(feature_matrix)

        n_clusters = min(n_clusters, len(alphas))

        if method == "genome":
            return self._cluster_by_genome(alphas, n_clusters)
        elif method == "hierarchical":
            return self._cluster_hierarchical(alphas, feature_matrix, n_clusters)
        else:
            return self._cluster_kmeans(alphas, feature_matrix, n_clusters)

    def _build_feature_matrix(
        self,
        alphas: List[Alpha],
    ) -> Tuple[np.ndarray, List[str]]:
        """
        构建特征矩阵

        特征: ic, rank_ic, ir, coverage, turnover, win_rate, sharpe, score
        """
        names = []
        features = []

        for alpha in alphas:
            m = alpha.metrics
            names.append(alpha.name)
            features.append([
                m.ic, m.rank_ic, m.ir, m.coverage,
                m.turnover, m.win_rate, m.sharpe, m.score,
            ])

        matrix = np.array(features, dtype=float)

        # 标准化
        std = matrix.std(axis=0)
        std[std < 1e-9] = 1.0
        matrix = (matrix - matrix.mean(axis=0)) / std

        # 处理 NaN
        matrix = np.nan_to_num(matrix, nan=0.0)

        return matrix, names

    def _cluster_kmeans(
        self,
        alphas: List[Alpha],
        feature_matrix: np.ndarray,
        n_clusters: int,
    ) -> Dict[str, Any]:
        """KMeans 聚类"""
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            # sklearn 不可用时退化为基因组聚类
            return self._cluster_by_genome(alphas, n_clusters)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(feature_matrix)

        return self._build_cluster_result(alphas, labels, n_clusters, "kmeans")

    def _cluster_hierarchical(
        self,
        alphas: List[Alpha],
        feature_matrix: np.ndarray,
        n_clusters: int,
    ) -> Dict[str, Any]:
        """层次聚类"""
        try:
            from sklearn.cluster import AgglomerativeClustering
        except ImportError:
            return self._cluster_by_genome(alphas, n_clusters)

        model = AgglomerativeClustering(n_clusters=n_clusters)
        labels = model.fit_predict(feature_matrix)

        return self._build_cluster_result(alphas, labels, n_clusters, "hierarchical")

    def _cluster_by_genome(
        self,
        alphas: List[Alpha],
        n_clusters: int,
    ) -> Dict[str, Any]:
        """
        基因组聚类（按因子名分组）

        不依赖 sklearn，直接按因子名分组
        """
        groups: Dict[str, List[Alpha]] = {}
        for alpha in alphas:
            genome = AlphaGenome.from_alpha(alpha)
            key = genome.factor or "unknown"
            if key not in groups:
                groups[key] = []
            groups[key].append(alpha)

        clusters = []
        for i, (factor, group) in enumerate(sorted(groups.items(), key=lambda x: -len(x[1]))):
            clusters.append({
                "name": f"{factor} Family",
                "factor": factor,
                "alphas": [a.to_dict() for a in group],
                "size": len(group),
                "alpha_ids": [a.alpha_id for a in group],
            })

        return {
            "clusters": clusters,
            "n_clusters": len(clusters),
            "method": "genome",
        }

    def _build_cluster_result(
        self,
        alphas: List[Alpha],
        labels: np.ndarray,
        n_clusters: int,
        method: str,
    ) -> Dict[str, Any]:
        """构建聚类结果"""
        clusters = []
        for i in range(n_clusters):
            mask = labels == i
            group = [a for a, m in zip(alphas, mask) if m]
            if not group:
                continue

            # 确定家族名（取最常见的因子名）
            factor_counts: Dict[str, int] = {}
            for a in group:
                genome = AlphaGenome.from_alpha(a)
                f = genome.factor or "unknown"
                factor_counts[f] = factor_counts.get(f, 0) + 1

            dominant_factor = max(factor_counts, key=factor_counts.get)

            clusters.append({
                "name": f"{dominant_factor} Family",
                "factor": dominant_factor,
                "alphas": [a.to_dict() for a in group],
                "size": len(group),
                "alpha_ids": [a.alpha_id for a in group],
            })

        return {
            "clusters": clusters,
            "n_clusters": len(clusters),
            "method": method,
        }

    def _estimate_n_clusters(self, feature_matrix: np.ndarray) -> int:
        """自动估算簇数（肘部法则简化版）"""
        n = feature_matrix.shape[0]
        # 简单规则：每 10-20 个 Alpha 一个簇
        return max(2, min(n // 10, 10))
