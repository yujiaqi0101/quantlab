"""
Model Comparator — 基于 Registry 的跨版本对比

ML Lab M4 第六部分：前端重要页面

  比较：
    LGBM_v1
    LGBM_v2
    LGBM_v3
    RF_v7
    XGB_v5

  展示：
    Model       IC      Sharpe    MaxDD
    LGBM_v1     0.08    1.2       -12%
    LGBM_v2     0.10    1.4       -9%
    LGBM_v3     0.11    1.5       -8%

  支持：
    排序
    筛选
    收藏
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from .registry import ModelVersion, ModelRegistry, LifecycleStatus

logger = logging.getLogger("quantlab.ml.registry.compare")


@dataclass
class ComparisonRow:
    """对比行"""
    version_id: str = ""
    name: str = ""
    family: str = ""
    version_number: int = 0
    model_type: str = ""
    lifecycle: str = ""
    is_champion: bool = False
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "name": self.name,
            "family": self.family,
            "version_number": self.version_number,
            "model_type": self.model_type,
            "lifecycle": self.lifecycle,
            "is_champion": self.is_champion,
            "metrics": self.metrics,
            "created_at": self.created_at,
            "tags": self.tags,
        }


@dataclass
class ComparisonReport:
    """对比报告"""
    rows: List[ComparisonRow] = field(default_factory=list)
    sort_by: str = ""
    sort_ascending: bool = False
    filter_family: Optional[str] = None
    filter_lifecycle: Optional[str] = None
    favorites: List[str] = field(default_factory=list)
    # 统计
    total: int = 0
    best_metric: Dict[str, str] = field(default_factory=dict)  # metric → version_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "sort_by": self.sort_by,
            "sort_ascending": self.sort_ascending,
            "filter_family": self.filter_family,
            "filter_lifecycle": self.filter_lifecycle,
            "favorites": self.favorites,
            "total": self.total,
            "best_metric": self.best_metric,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame（便于前端展示）"""
        data = []
        for r in self.rows:
            row = {
                "version_id": r.version_id,
                "name": r.name,
                "family": r.family,
                "version_number": r.version_number,
                "model_type": r.model_type,
                "lifecycle": r.lifecycle,
                "is_champion": r.is_champion,
                "is_favorite": r.version_id in self.favorites,
                "created_at": r.created_at,
            }
            # 展平 metrics
            for k, v in r.metrics.items():
                row[f"metric_{k}"] = v
            data.append(row)
        return pd.DataFrame(data)


class ModelComparator:
    """
    模型对比器（基于 Registry）

    用法：
        comp = ModelComparator(registry)
        report = comp.compare(
            version_ids=["MV-1", "MV-2", "MV-3"],
            sort_by="sharpe",
        )
        df = report.to_dataframe()
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self._favorites: set = set()

    def compare(
        self,
        version_ids: Optional[List[str]] = None,
        family: Optional[str] = None,
        lifecycle: Optional[LifecycleStatus] = None,
        sort_by: str = "sharpe",
        ascending: bool = False,
    ) -> ComparisonReport:
        """
        对比模型版本

        Args:
            version_ids: 指定版本 ID 列表（None 表示所有）
            family: 按族过滤
            lifecycle: 按状态过滤
            sort_by: 排序指标（如 "sharpe", "ic"）
            ascending: 是否升序

        Returns:
            ComparisonReport
        """
        # 获取版本列表
        if version_ids:
            versions = [
                self.registry.get_version(vid)
                for vid in version_ids
            ]
            versions = [v for v in versions if v is not None]
        else:
            versions = self.registry.list_versions(
                family=family,
                lifecycle=lifecycle,
            )

        # 构建 rows
        champions = self.registry.get_all_champions()
        rows: List[ComparisonRow] = []
        for v in versions:
            champion = champions.get(v.family)
            rows.append(ComparisonRow(
                version_id=v.version_id,
                name=v.name,
                family=v.family,
                version_number=v.version_number,
                model_type=v.model_type.value,
                lifecycle=v.lifecycle.value,
                is_champion=(champion is not None and champion.version_id == v.version_id),
                metrics=v.metrics,
                created_at=v.created_at,
                tags=v.tags,
            ))

        # 排序
        if sort_by:
            rows.sort(
                key=lambda r: r.metrics.get(sort_by, 0),
                reverse=not ascending,
            )

        # 找出各指标最优
        best_metric: Dict[str, str] = {}
        for metric in ["ic", "sharpe", "rmse", "accuracy"]:
            if not rows:
                continue
            if metric == "rmse":
                # rmse 越小越好
                best = min(rows, key=lambda r: r.metrics.get(metric, float("inf")))
            else:
                best = max(rows, key=lambda r: r.metrics.get(metric, float("-inf")))
            best_metric[metric] = best.version_id

        return ComparisonReport(
            rows=rows,
            sort_by=sort_by,
            sort_ascending=ascending,
            filter_family=family,
            filter_lifecycle=lifecycle.value if lifecycle else None,
            favorites=list(self._favorites),
            total=len(rows),
            best_metric=best_metric,
        )

    def get_leaderboard(
        self,
        metric: str = "sharpe",
        family: Optional[str] = None,
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取排行榜

        Args:
            metric: 排序指标
            family: 按族过滤
            top_n: 返回前 N 个

        Returns:
            [{"rank": 1, "name": ..., "metric_value": ...}, ...]
        """
        report = self.compare(family=family, sort_by=metric, ascending=(metric == "rmse"))
        leaderboard = []
        for rank, row in enumerate(report.rows, 1):
            leaderboard.append({
                "rank": rank,
                "version_id": row.version_id,
                "name": row.name,
                "family": row.family,
                "version_number": row.version_number,
                "lifecycle": row.lifecycle,
                "is_champion": row.is_champion,
                "metric_value": row.metrics.get(metric, 0),
                "metrics": row.metrics,
            })
            if top_n and rank >= top_n:
                break
        return leaderboard

    # ------------------------------------------------------------------
    # 收藏
    # ------------------------------------------------------------------

    def add_favorite(self, version_id: str) -> None:
        """收藏版本"""
        self._favorites.add(version_id)

    def remove_favorite(self, version_id: str) -> None:
        """取消收藏"""
        self._favorites.discard(version_id)

    def get_favorites(self) -> List[ModelVersion]:
        """获取收藏的版本"""
        return [
            self.registry.get_version(vid)
            for vid in self._favorites
            if self.registry.get_version(vid) is not None
        ]

    def is_favorite(self, version_id: str) -> bool:
        return version_id in self._favorites

    # ------------------------------------------------------------------
    # 跨族对比
    # ------------------------------------------------------------------

    def compare_families(
        self,
        families: Optional[List[str]] = None,
        metric: str = "sharpe",
    ) -> ComparisonReport:
        """
        跨族对比（每族取 Champion）

        Args:
            families: 指定族列表（None 表示所有）
            metric: 排序指标
        """
        if families is None:
            families = self.registry.list_families()

        champion_ids: List[str] = []
        for fam in families:
            champ = self.registry.get_champion(fam)
            if champ:
                champion_ids.append(champ.version_id)

        return self.compare(
            version_ids=champion_ids,
            sort_by=metric,
        )
