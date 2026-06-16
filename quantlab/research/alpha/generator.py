"""
Alpha Generator — 从因子批量生成 Alpha

核心思路：
  用户提供一个因子（如 RSI14），Generator 自动生成多个 Alpha

  RSI14 →
    RSI14_LT_20  (RSI < 20 → 做多)
    RSI14_LT_25  (RSI < 25 → 做多)
    RSI14_LT_30  (RSI < 30 → 做多)
    RSI14_LT_35  (RSI < 35 → 做多)
    RSI14_LT_40  (RSI < 40 → 做多)

  Momentum20 →
    MOM20_GT_0     (Momentum > 0 → 做多)
    MOM20_GT_0.01  (Momentum > 0.01 → 做多)
    MOM20_GT_0.02  (Momentum > 0.02 → 做多)

生成策略：
  1. ThresholdStrategy: 根据因子类型自动选择阈值范围
  2. CrossoverStrategy: 因子与自身均值交叉
  3. ZeroCrossStrategy: 因子零轴穿越
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .alpha import Alpha, AlphaType

logger = logging.getLogger("quantlab.alpha.generator")


class GenerationTemplate:
    """
    生成模板

    定义如何从一个因子生成多个 Alpha
    """

    def __init__(
        self,
        factor_name: str,
        factor_type: str = "oscillator",  # oscillator / trend / volatility / volume
        custom_lower_values: Optional[List[float]] = None,
        custom_upper_values: Optional[List[float]] = None,
        custom_cross_periods: Optional[List[int]] = None,
    ) -> None:
        self.factor_name = factor_name
        self.factor_type = factor_type
        self.custom_lower_values = custom_lower_values
        self.custom_upper_values = custom_upper_values
        self.custom_cross_periods = custom_cross_periods

    def get_lower_values(self) -> List[float]:
        """获取下限阈值列表"""
        if self.custom_lower_values is not None:
            return self.custom_lower_values

        templates = {
            "oscillator": [20, 25, 30, 35, 40],       # RSI, Stochastic 等
            "trend": [-0.02, -0.01, 0, 0.01, 0.02],   # Momentum 等
            "volatility": [0.01, 0.02, 0.03, 0.05],    # ATR, VOL 等
            "volume": [0.5, 0.8, 1.0, 1.2, 1.5],       # 成交量比等
        }
        return templates.get(self.factor_type, [0])

    def get_upper_values(self) -> List[float]:
        """获取上限阈值列表"""
        if self.custom_upper_values is not None:
            return self.custom_upper_values

        templates = {
            "oscillator": [60, 65, 70, 75, 80],
            "trend": [-0.02, -0.01, 0, 0.01, 0.02],
            "volatility": [0.03, 0.05, 0.08, 0.10],
            "volume": [0.5, 0.8, 1.0, 1.2, 1.5],
        }
        return templates.get(self.factor_type, [0])

    def get_cross_periods(self) -> List[int]:
        """获取交叉均线周期列表"""
        if self.custom_cross_periods is not None:
            return self.custom_cross_periods
        return [5, 10, 20]


class AlphaGenerator:
    """
    Alpha 生成器

    从因子批量生成 Alpha，支持：
      1. 阈值型：factor < lower → 做多, factor > upper → 做空
      2. 交叉型：factor 上穿 SMA(N) → 做多
      3. 零轴型：factor > 0 → 做多, factor < 0 → 做空
    """

    def __init__(self) -> None:
        self._templates: Dict[str, GenerationTemplate] = {}
        self._register_default_templates()

    def _register_default_templates(self) -> None:
        """注册默认因子模板"""
        defaults = {
            "RSI6": ("oscillator", [15, 20, 25, 30], [70, 75, 80, 85]),
            "RSI14": ("oscillator", [20, 25, 30, 35, 40], [60, 65, 70, 75, 80]),
            "RSI28": ("oscillator", [25, 30, 35, 40], [60, 65, 70, 75]),
            "MOM5": ("trend", None, None),
            "MOM10": ("trend", None, None),
            "MOM20": ("trend", None, None),
            "MOM60": ("trend", None, None),
            "ATR14": ("volatility", None, None),
            "ATR28": ("volatility", None, None),
            "VOL5": ("volume", None, None),
            "VOL20": ("volume", None, None),
        }
        for name, (ftype, lowers, uppers) in defaults.items():
            self._templates[name] = GenerationTemplate(
                factor_name=name,
                factor_type=ftype,
                custom_lower_values=lowers,
                custom_upper_values=uppers,
            )

    def register_template(self, template: GenerationTemplate) -> None:
        """注册自定义模板"""
        self._templates[template.factor_name] = template

    def generate(
        self,
        factor_name: str,
        methods: Optional[List[str]] = None,
    ) -> List[Alpha]:
        """
        从因子批量生成 Alpha

        参数:
            factor_name  因子名称（如 "RSI14"）
            methods      生成方法列表，默认 ["threshold"]
                         可选: "threshold", "crossover", "zero_cross"

        返回:
            Alpha 列表
        """
        if methods is None:
            methods = ["threshold"]

        alphas: List[Alpha] = []

        template = self._templates.get(factor_name)
        if template is None:
            # 自动推断因子类型
            template = GenerationTemplate(factor_name, "oscillator")

        for method in methods:
            if method == "threshold":
                alphas.extend(self._generate_threshold(template))
            elif method == "crossover":
                alphas.extend(self._generate_crossover(template))
            elif method == "zero_cross":
                alphas.extend(self._generate_zero_cross(template))

        logger.info(f"generated {len(alphas)} alphas from factor '{factor_name}'")
        return alphas

    def generate_batch(
        self,
        factor_names: List[str],
        methods: Optional[List[str]] = None,
    ) -> Dict[str, List[Alpha]]:
        """
        批量生成：多个因子各生成一组 Alpha

        返回:
            {factor_name: [Alpha, ...]}
        """
        result: Dict[str, List[Alpha]] = {}
        for name in factor_names:
            result[name] = self.generate(name, methods)
        return result

    def _generate_threshold(self, template: GenerationTemplate) -> List[Alpha]:
        """
        阈值型 Alpha

        oscillator: lower 做多, upper 做空
        trend: factor > 0 做多, factor < 0 做空
        """
        alphas: List[Alpha] = []
        lower_values = template.get_lower_values()
        upper_values = template.get_upper_values()

        # 单边阈值（做多信号）
        for lv in lower_values:
            alphas.append(Alpha(
                alpha_type=AlphaType.THRESHOLD,
                factor_name=template.factor_name,
                signal_expr=f"LT_{lv}",
                lower=lv,
                upper=None,
            ))

        # 双边阈值（做多 + 做空）
        for lv, uv in zip(lower_values, upper_values):
            alphas.append(Alpha(
                alpha_type=AlphaType.THRESHOLD,
                factor_name=template.factor_name,
                signal_expr=f"LT_{lv}_GT_{uv}",
                lower=lv,
                upper=uv,
            ))

        return alphas

    def _generate_crossover(self, template: GenerationTemplate) -> List[Alpha]:
        """
        交叉型 Alpha

        factor 上穿 SMA(N) → 做多
        """
        alphas: List[Alpha] = []
        for period in template.get_cross_periods():
            alphas.append(Alpha(
                alpha_type=AlphaType.CROSSOVER,
                factor_name=template.factor_name,
                signal_expr=f"CROSS_SMA{period}",
                factor_name_2=f"SMA{period}",
            ))
        return alphas

    def _generate_zero_cross(self, template: GenerationTemplate) -> List[Alpha]:
        """
        零轴穿越型 Alpha

        factor > 0 → 做多, factor < 0 → 做空
        """
        return [Alpha(
            alpha_type=AlphaType.ZERO_CROSS,
            factor_name=template.factor_name,
            signal_expr="ZERO_CROSS",
        )]
