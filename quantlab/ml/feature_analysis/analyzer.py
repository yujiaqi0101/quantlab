"""
Feature Analyzer — 特征分析器

ML Lab 第四部分：发现哪些特征有预测能力

  统计：
    - IC (Information Coefficient)       — Pearson 相关
    - Rank IC                            — Spearman 秩相关
    - Mutual Information                 — 互信息
    - Correlation Matrix                 — 特征间相关性

  输出示例：
      RSI14       IC=0.08  RankIC=0.10  MI=0.05
      Momentum20  IC=0.12  RankIC=0.15  MI=0.08
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.feature_analysis")


@dataclass
class FeatureAnalysisResult:
    """特征分析结果"""
    feature_name: str = ""
    ic: float = 0.0           # Information Coefficient (Pearson)
    rank_ic: float = 0.0      # Rank IC (Spearman)
    mutual_info: float = 0.0  # Mutual Information
    n_samples: int = 0
    ic_std: float = 0.0       # IC 标准差（滚动 IC 的波动）
    ic_ir: float = 0.0        # IC Information Ratio = mean / std

    def to_dict(self) -> Dict:
        return {
            "feature_name": self.feature_name,
            "ic": round(self.ic, 4),
            "rank_ic": round(self.rank_ic, 4),
            "mutual_info": round(self.mutual_info, 4),
            "n_samples": self.n_samples,
            "ic_std": round(self.ic_std, 4),
            "ic_ir": round(self.ic_ir, 4),
        }


class FeatureAnalyzer:
    """
    特征分析器

    用法：
        analyzer = FeatureAnalyzer()
        results = analyzer.analyze(features_df, label_series)
        # results: List[FeatureAnalysisResult]

        # 特征间相关性矩阵
        corr = analyzer.correlation_matrix(features_df)

        # 滚动 IC
        rolling_ic = analyzer.rolling_ic(features_df["rsi14"], label_series, window=60)
    """

    def analyze(
        self,
        features: pd.DataFrame,
        label: pd.Series,
    ) -> List[FeatureAnalysisResult]:
        """
        分析所有特征对标签的预测能力

        Args:
            features: 特征 DataFrame（每列一个特征）
            label: 标签 Series

        Returns:
            List[FeatureAnalysisResult]，按 |IC| 降序
        """
        # 对齐索引
        common_idx = features.index.intersection(label.index)
        features = features.loc[common_idx].copy()
        label = label.loc[common_idx].copy()

        # 去掉标签为 NaN 的行
        valid_mask = label.notna()
        features = features[valid_mask]
        label = label[valid_mask]

        results: List[FeatureAnalysisResult] = []
        for col in features.columns:
            feat = features[col]
            result = self._analyze_single(feat, label)
            result.feature_name = col
            results.append(result)

        # 按 |IC| 降序
        results.sort(key=lambda r: abs(r.ic), reverse=True)
        return results

    def _analyze_single(
        self,
        feature: pd.Series,
        label: pd.Series,
    ) -> FeatureAnalysisResult:
        """分析单个特征"""
        # 去掉 NaN
        mask = feature.notna() & label.notna()
        f = feature[mask]
        l = label[mask]

        if len(f) < 10:
            return FeatureAnalysisResult(n_samples=len(f))

        # IC (Pearson)
        ic = self._safe_corr(f, l, method="pearson")

        # Rank IC (Spearman)
        rank_ic = self._safe_corr(f, l, method="spearman")

        # Mutual Information
        mi = self._mutual_info(f, l)

        # 滚动 IC 的标准差和 IR
        rolling_ics = self.rolling_ic(feature, label, window=60)
        ic_std = rolling_ics.std() if len(rolling_ics) > 0 else 0.0
        ic_ir = ic / ic_std if ic_std > 0 else 0.0

        return FeatureAnalysisResult(
            ic=ic,
            rank_ic=rank_ic,
            mutual_info=mi,
            n_samples=len(f),
            ic_std=ic_std,
            ic_ir=ic_ir,
        )

    def _safe_corr(self, a: pd.Series, b: pd.Series, method: str = "pearson") -> float:
        """安全计算相关系数"""
        try:
            if method == "pearson":
                return float(a.corr(b))
            else:
                return float(a.corr(b, method="spearman"))
        except Exception:
            return 0.0

    def _mutual_info(self, feature: pd.Series, label: pd.Series) -> float:
        """计算互信息"""
        try:
            from sklearn.feature_selection import mutual_info_regression
            f = feature.values.reshape(-1, 1)
            l = label.values
            mi = mutual_info_regression(f, l, random_state=42)
            return float(mi[0])
        except Exception:
            return 0.0

    def correlation_matrix(self, features: pd.DataFrame) -> pd.DataFrame:
        """特征间相关性矩阵"""
        return features.corr()

    def rolling_ic(
        self,
        feature: pd.Series,
        label: pd.Series,
        window: int = 60,
    ) -> pd.Series:
        """
        滚动 IC

        Args:
            feature: 特征 Series
            label: 标签 Series
            window: 滚动窗口

        Returns:
            滚动 IC Series
        """
        common_idx = feature.index.intersection(label.index)
        f = feature.loc[common_idx]
        l = label.loc[common_idx]

        ics = []
        for i in range(window, len(f)):
            f_window = f.iloc[i - window:i]
            l_window = l.iloc[i - window:i]
            mask = f_window.notna() & l_window.notna()
            if mask.sum() < 10:
                ics.append(np.nan)
                continue
            ic = self._safe_corr(f_window[mask], l_window[mask])
            ics.append(ic)

        return pd.Series(ics, index=f.index[window:], name="rolling_ic")

    def rank_features(self, results: List[FeatureAnalysisResult]) -> pd.DataFrame:
        """将分析结果排序为 DataFrame"""
        df = pd.DataFrame([r.to_dict() for r in results])
        if len(df) > 0:
            df["abs_ic"] = df["ic"].abs()
            df = df.sort_values("abs_ic", ascending=False).drop(columns=["abs_ic"])
        return df
