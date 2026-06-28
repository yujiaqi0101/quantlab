"""
模块 1: Prediction Adapter

统一所有模型输出为 Prediction 对象。
不同模型输出差异很大，本模块负责把它们全部转成统一格式。

分类模型类别映射固定为：0=Down, 1=Neutral, 2=Up
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from .signal import Prediction

logger = logging.getLogger("quantlab.ml.signal_engine.adapter")


class PredictionAdapter:
    """模型输出 → 统一 Prediction"""

    # 分类模型类别映射：0=Down, 1=Neutral, 2=Up
    CLASS_MAP = {0: ("down", 0.0), 1: ("neutral", 0.5), 2: ("up", 1.0)}

    def adapt_regression(
        self,
        symbol: str,
        datetime: str,
        y_pred: float,
        model_type: str = "lightgbm",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """回归模型: y_pred 是收益率"""
        # 回归值用 sigmoid 转成 [0,1] 概率（仅作置信度参考）
        prob = float(1.0 / (1.0 + np.exp(-y_pred))) if y_pred != 0 else 0.5
        return Prediction(
            symbol=symbol,
            datetime=datetime,
            value=float(y_pred),
            probability=prob,
            model_type=model_type,
            metadata=metadata or {},
        )

    def adapt_classifier(
        self,
        symbol: str,
        datetime: str,
        y_pred: int,
        y_proba: Optional[List[float]] = None,
        model_type: str = "lightgbm",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """分类模型: y_pred 是类别 (0/1/2), y_proba 是概率向量"""
        label, default_prob = self.CLASS_MAP.get(int(y_pred), ("neutral", 0.5))
        # 取该类别的概率作为 confidence
        if y_proba and len(y_proba) > int(y_pred):
            prob = float(y_proba[int(y_pred)])
        else:
            prob = default_prob
        # value 用类别标签，metadata 保存原始概率向量
        meta = dict(metadata or {})
        meta["class_label"] = label
        meta["y_proba"] = list(y_proba) if y_proba is not None else []
        return Prediction(
            symbol=symbol,
            datetime=datetime,
            value=float(y_pred),
            probability=prob,
            model_type=model_type,
            metadata=meta,
        )

    def adapt_proba(
        self,
        symbol: str,
        datetime: str,
        proba: float,
        model_type: str = "lightgbm",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """概率输出: proba 是 [0,1] 标量"""
        proba = float(max(0.0, min(1.0, proba)))
        return Prediction(
            symbol=symbol,
            datetime=datetime,
            value=proba,
            probability=proba,
            model_type=model_type,
            metadata=metadata or {},
        )

    def adapt_sequence(
        self,
        symbol: str,
        datetime: str,
        sequence: List[float],
        model_type: str = "transformer",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """序列模型 (Transformer): 取最后一项"""
        if not sequence:
            value, prob = 0.0, 0.5
        else:
            value = float(sequence[-1])
            prob = float(1.0 / (1.0 + np.exp(-value))) if value != 0 else 0.5
        meta = dict(metadata or {})
        meta["sequence_length"] = len(sequence)
        return Prediction(
            symbol=symbol,
            datetime=datetime,
            value=value,
            probability=prob,
            model_type=model_type,
            metadata=meta,
        )

    def adapt_action(
        self,
        symbol: str,
        datetime: str,
        action: int,
        model_type: str = "rl",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """RL 模型: action (0=short, 1=hold, 2=long) → 类似分类"""
        # RL action 映射：0=Down, 1=Neutral, 2=Up
        return self.adapt_classifier(
            symbol, datetime, int(action), None, model_type, metadata
        )

    def adapt_batch(self, predictions: List[Prediction]) -> List[Prediction]:
        """批量适配（已经适配过的直接返回）"""
        return list(predictions)

    def adapt_auto(
        self,
        symbol: str,
        datetime: str,
        output: Any,
        model_type: str = "lightgbm",
        y_proba: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """
        自动判断输出类型并适配。

        - model_type 含 "class" 或 output 是 int 且 y_proba 非空 → 分类
        - model_type == "rl" → action
        - model_type == "transformer" 且 output 是 list → sequence
        - output 是 float → 回归
        """
        if model_type == "rl" or (isinstance(output, int) and model_type == "rl"):
            return self.adapt_action(symbol, datetime, int(output), model_type, metadata)
        if isinstance(output, (list, np.ndarray)) and model_type == "transformer":
            return self.adapt_sequence(
                symbol, datetime, list(output), model_type, metadata
            )
        if isinstance(output, (int, np.integer)) and y_proba is not None:
            return self.adapt_classifier(
                symbol, datetime, int(output), y_proba, model_type, metadata
            )
        if isinstance(output, (int, np.integer)) and model_type and "class" in model_type.lower():
            return self.adapt_classifier(
                symbol, datetime, int(output), y_proba, model_type, metadata
            )
        if isinstance(output, (float, np.floating)):
            return self.adapt_regression(
                symbol, datetime, float(output), model_type, metadata
            )
        # 兜底
        return self.adapt_regression(symbol, datetime, float(output) if output else 0.0, model_type, metadata)
