"""
V4.3 Dataset Registry — Validator

数据集校验器。
注册前必须通过校验，否则拒绝注册。

检查项：
  - 时间是否递增
  - 缺失值
  - 重复值
  - OHLC 合法性（high >= low, open/close <= high, open/close >= low）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


logger = logging.getLogger("quantlab.dataset.validator")


@dataclass(slots=True)
class ValidationResult:
    """校验结果"""
    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "stats": dict(self.stats),
        }


class DatasetValidator:
    """
    数据集校验器

    用法：
        validator = DatasetValidator()
        result = validator.validate(df)
        if not result.ok:
            print(result.errors)
    """

    def validate(
        self,
        df: pd.DataFrame,
        *,
        check_timestamp: bool = True,
        check_missing: bool = True,
        check_duplicates: bool = True,
        check_ohlcv: bool = True,
    ) -> ValidationResult:
        """
        校验 DataFrame

        参数：
          df               DataFrame
          check_timestamp  检查时间是否递增
          check_missing    检查缺失值
          check_duplicates 检查重复值
          check_ohlcv      检查 OHLC 合法性
        """
        result = ValidationResult()

        if df is None or df.empty:
            result.ok = False
            result.errors.append("DataFrame is empty or None")
            return result

        # 基础统计
        result.stats["rows"] = len(df)
        result.stats["columns"] = list(df.columns)

        # 1) 时间递增
        if check_timestamp:
            self._check_timestamp(df, result)

        # 2) 缺失值
        if check_missing:
            self._check_missing(df, result)

        # 3) 重复值
        if check_duplicates:
            self._check_duplicates(df, result)

        # 4) OHLC 合法性
        if check_ohlcv:
            self._check_ohlcv(df, result)

        return result

    def _check_timestamp(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> None:
        """检查索引是否递增"""
        try:
            if isinstance(df.index, pd.DatetimeIndex):
                if not df.index.is_monotonic_increasing:
                    n_desc = sum(
                        1 for i in range(1, len(df.index))
                        if df.index[i] < df.index[i - 1]
                    )
                    result.errors.append(
                        f"timestamp not monotonically increasing: "
                        f"{n_desc} descents"
                    )
                    result.ok = False
        except Exception as exc:
            result.warnings.append(
                f"timestamp check skipped: {exc}"
            )

    def _check_missing(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> None:
        """检查缺失值"""
        total_missing = int(df.isnull().sum().sum())
        result.stats["missing"] = total_missing

        if total_missing > 0:
            # 按列统计
            missing_by_col = df.isnull().sum()
            missing_cols = missing_by_col[missing_by_col > 0]
            detail = ", ".join(
                f"{col}={cnt}" for col, cnt in missing_cols.items()
            )
            result.warnings.append(
                f"missing values found: {total_missing} total ({detail})"
            )

    def _check_duplicates(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> None:
        """检查重复索引"""
        n_dup = int(df.index.duplicated().sum())
        result.stats["duplicates"] = n_dup

        if n_dup > 0:
            result.errors.append(
                f"duplicate index found: {n_dup} rows"
            )
            result.ok = False

    def _check_ohlcv(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> None:
        """检查 OHLC 合法性"""
        cols_lower = {c.lower(): c for c in df.columns}

        high_col = cols_lower.get("high")
        low_col = cols_lower.get("low")
        open_col = cols_lower.get("open")
        close_col = cols_lower.get("close")

        if high_col is None or low_col is None:
            # 不是 OHLCV 数据，跳过
            return

        high = df[high_col]
        low = df[low_col]

        # high >= low
        n_high_lt_low = int((high < low).sum())
        if n_high_lt_low > 0:
            result.errors.append(
                f"high < low in {n_high_lt_low} rows"
            )
            result.ok = False

        # open <= high
        if open_col is not None:
            n_open_gt_high = int((df[open_col] > high).sum())
            if n_open_gt_high > 0:
                result.errors.append(
                    f"open > high in {n_open_gt_high} rows"
                )
                result.ok = False

        # close <= high
        if close_col is not None:
            n_close_gt_high = int((df[close_col] > high).sum())
            if n_close_gt_high > 0:
                result.errors.append(
                    f"close > high in {n_close_gt_high} rows"
                )
                result.ok = False

        # open >= low
        if open_col is not None:
            n_open_lt_low = int((df[open_col] < low).sum())
            if n_open_lt_low > 0:
                result.errors.append(
                    f"open < low in {n_open_lt_low} rows"
                )
                result.ok = False

        # close >= low
        if close_col is not None:
            n_close_lt_low = int((df[close_col] < low).sum())
            if n_close_lt_low > 0:
                result.errors.append(
                    f"close < low in {n_close_lt_low} rows"
                )
                result.ok = False
