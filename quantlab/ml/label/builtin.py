"""
Builtin Labels — 内置标签

ML Lab 第三部分：内置标签

  FutureReturn5 / 10 / 20     — 未来 N 期收益率（回归）
  UpDownLabel                  — 三分类（Up / Neutral / Down）
  DirectionLabel               — 二分类（Up / Down）
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Label


# ==================================================================
# FutureReturn — 未来收益率（回归标签）
# ==================================================================

class FutureReturn(Label):
    """未来 N 期收益率"""
    name: str = "FutureReturn"
    description: str = "Future N-period return"
    label_type: str = "regression"
    required_columns: list = ["close"]

    def __init__(self, period: int = 10) -> None:
        self.params = {"period": period}
        self.label_id = f"future_return_{period}"
        self.name = f"FutureReturn{period}"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        # shift(-period) 表示未来第 period 期的价格
        future_price = df["close"].shift(-period)
        label = (future_price - df["close"]) / df["close"]
        return label.rename(self.label_id)


# ==================================================================
# UpDownLabel — 三分类（Up / Neutral / Down）
# ==================================================================

class UpDownLabel(Label):
    """三分类标签：Up / Neutral / Down"""
    name: str = "UpDownLabel"
    description: str = "3-class label: Up / Neutral / Down"
    label_type: str = "classification"
    classes: list = ["Down", "Neutral", "Up"]
    required_columns: list = ["close"]

    def __init__(self, period: int = 10, threshold: float = 0.01) -> None:
        self.params = {"period": period, "threshold": threshold}
        self.label_id = f"updown_{period}_{threshold}"
        self.name = f"UpDown({period},{threshold})"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        threshold = self.params["threshold"]
        future_price = df["close"].shift(-period)
        ret = (future_price - df["close"]) / df["close"]

        # 0=Down, 1=Neutral, 2=Up
        label = pd.Series(1, index=df.index, name=self.label_id)
        label[ret < -threshold] = 0      # Down
        label[ret > threshold] = 2       # Up
        # 最后 period 期为 NaN（无未来数据）
        label[ret.isna()] = np.nan
        return label


# ==================================================================
# DirectionLabel — 二分类（Up / Down）
# ==================================================================

class DirectionLabel(Label):
    """二分类标签：Up / Down"""
    name: str = "DirectionLabel"
    description: str = "Binary label: Up / Down"
    label_type: str = "classification"
    classes: list = ["Down", "Up"]
    required_columns: list = ["close"]

    def __init__(self, period: int = 10) -> None:
        self.params = {"period": period}
        self.label_id = f"direction_{period}"
        self.name = f"Direction({period})"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        period = self.params["period"]
        future_price = df["close"].shift(-period)
        ret = (future_price - df["close"]) / df["close"]
        # 0=Down, 1=Up
        label = (ret > 0).astype(float)
        label[ret.isna()] = np.nan
        return label.rename(self.label_id)


# ==================================================================
# 注册所有内置标签
# ==================================================================

def register_all_builtin(registry) -> int:
    """注册所有内置标签"""
    builtins = [
        FutureReturn(5),
        FutureReturn(10),
        FutureReturn(20),
        UpDownLabel(10, 0.01),
        UpDownLabel(10, 0.02),
        DirectionLabel(10),
    ]
    for l in builtins:
        registry.register(l)
    return len(builtins)
