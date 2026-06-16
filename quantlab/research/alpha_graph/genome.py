"""
Alpha Genome — Alpha 基因组表示

任何 Alpha 都能转成 Genome，支持：
  - Diff：两个 Alpha 的差异
  - Similarity：基因组层面的相似度
  - Mutation：自动变异生成新 Alpha
  - Evolution：进化体系的基础

Genome 结构：
  {
      "factor": "RSI",
      "window": 14,
      "operator": "<",
      "threshold": 30,
      "type": "threshold"
  }

  {
      "factor": "Momentum",
      "window": 20,
      "operator": ">",
      "threshold": 0,
      "type": "threshold"
  }

  {
      "factors": ["MA5", "MA20"],
      "operator": "crossover",
      "type": "crossover"
  }

  {
      "components": ["alpha_id_1", "alpha_id_2"],
      "weights": [0.5, 0.5],
      "operator": "weighted",
      "type": "composite"
  }
"""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from ..alpha.alpha import Alpha, AlphaType


@dataclass
class AlphaGenome:
    """
    Alpha 基因组

    将 Alpha 的核心逻辑抽象为可比较、可变异的基因组
    """
    # 因子基因
    factor: str = ""                    # 因子名（如 RSI, Momentum）
    window: Optional[int] = None        # 因子窗口（如 14, 20）
    factor_2: Optional[str] = None      # 第二个因子（交叉型）
    window_2: Optional[int] = None      # 第二个因子窗口

    # 信号基因
    operator: str = ""                  # 操作符: <, >, crossover, zero_cross, and, or, weighted
    threshold: Optional[float] = None   # 阈值
    threshold_2: Optional[float] = None # 第二个阈值（双边）

    # 组合基因
    components: List[str] = field(default_factory=list)  # 组成 Alpha ID
    weights: List[float] = field(default_factory=list)    # 权重

    # 类型
    genome_type: str = "threshold"      # threshold / crossover / zero_cross / composite

    # 来源
    parent_ids: List[str] = field(default_factory=list)  # 父 Alpha ID（用于 Lineage）
    mutation_type: Optional[str] = None                   # 变异类型

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AlphaGenome":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_alpha(cls, alpha: Alpha) -> "AlphaGenome":
        """从 Alpha 对象提取基因组"""
        genome = AlphaGenome(genome_type=alpha.alpha_type.value)

        if alpha.alpha_type == AlphaType.THRESHOLD:
            # 解析因子名和窗口
            factor, window = _parse_factor_name(alpha.factor_name)
            genome.factor = factor
            genome.window = window
            genome.operator = "<" if alpha.lower is not None else ">"
            genome.threshold = alpha.lower if alpha.lower is not None else alpha.upper
            genome.threshold_2 = alpha.upper if alpha.lower is not None and alpha.upper is not None else None

        elif alpha.alpha_type == AlphaType.ZERO_CROSS:
            factor, window = _parse_factor_name(alpha.factor_name)
            genome.factor = factor
            genome.window = window
            genome.operator = "zero_cross"

        elif alpha.alpha_type == AlphaType.CROSSOVER:
            factor, window = _parse_factor_name(alpha.factor_name)
            factor_2, window_2 = _parse_factor_name(alpha.factor_name_2 or "")
            genome.factor = factor
            genome.window = window
            genome.factor_2 = factor_2
            genome.window_2 = window_2
            genome.operator = "crossover"

        elif alpha.alpha_type == AlphaType.COMPOSITE:
            genome.operator = alpha.combine_method or "weighted"
            genome.components = [c.get("alpha_id", "") for c in (alpha.components or [])]
            genome.weights = [c.get("weight", 0) for c in (alpha.components or [])]

        return genome

    # ---- Diff ----

    def diff(self, other: "AlphaGenome") -> Dict[str, Any]:
        """
        比较两个基因组的差异

        返回:
            {"same": [...], "different": [...], "similarity": 0.85}
        """
        same = []
        different = []

        fields = ["factor", "window", "operator", "threshold", "threshold_2",
                   "factor_2", "window_2", "genome_type"]

        for f in fields:
            v1 = getattr(self, f, None)
            v2 = getattr(other, f, None)
            if v1 == v2:
                if v1 is not None:
                    same.append({"field": f, "value": v1})
            else:
                different.append({"field": f, "value_a": v1, "value_b": v2})

        similarity = len(same) / max(len(same) + len(different), 1)

        return {
            "same": same,
            "different": different,
            "similarity": round(similarity, 4),
        }

    # ---- Mutation ----

    def mutate_threshold(self, step: float = 5.0) -> List["AlphaGenome"]:
        """
        阈值变异

        例如 RSI < 30 → RSI < 25, RSI < 35
        """
        mutations = []
        if self.threshold is not None:
            # 降阈值
            m1 = copy.deepcopy(self)
            m1.threshold = self.threshold - step
            m1.mutation_type = "threshold_down"
            m1.parent_ids = []
            mutations.append(m1)

            # 升阈值
            m2 = copy.deepcopy(self)
            m2.threshold = self.threshold + step
            m2.mutation_type = "threshold_up"
            m2.parent_ids = []
            mutations.append(m2)

        return mutations

    def mutate_window(self, steps: List[int] = None) -> List["AlphaGenome"]:
        """
        窗口变异

        例如 RSI(14) → RSI(10), RSI(21)
        """
        if steps is None:
            steps = [-4, -2, 2, 4, 7]

        mutations = []
        if self.window is not None:
            for delta in steps:
                new_window = self.window + delta
                if new_window < 2:
                    continue
                m = copy.deepcopy(self)
                m.window = new_window
                m.mutation_type = "window_change"
                m.parent_ids = []
                mutations.append(m)

        return mutations

    def mutate_operator(self) -> List["AlphaGenome"]:
        """
        操作符变异

        例如 < → >, crossover → zero_cross
        """
        mutations = []
        op_map = {
            "<": [">"],
            ">": ["<"],
            "zero_cross": ["<", ">"],
        }
        alternatives = op_map.get(self.operator, [])
        for alt_op in alternatives:
            m = copy.deepcopy(self)
            m.operator = alt_op
            m.mutation_type = "operator_change"
            m.parent_ids = []
            mutations.append(m)

        return mutations

    def to_alpha(self) -> Alpha:
        """从基因组生成 Alpha 对象"""
        if self.genome_type == "threshold":
            factor_name = _build_factor_name(self.factor, self.window)
            lower = None
            upper = None
            if self.operator == "<" and self.threshold is not None:
                lower = self.threshold
                if self.threshold_2 is not None:
                    upper = self.threshold_2
            elif self.operator == ">" and self.threshold is not None:
                upper = self.threshold

            return Alpha(
                alpha_type=AlphaType.THRESHOLD,
                factor_name=factor_name,
                signal_expr=f"{self.operator}_{self.threshold}",
                lower=lower,
                upper=upper,
            )

        elif self.genome_type == "zero_cross":
            factor_name = _build_factor_name(self.factor, self.window)
            return Alpha(
                alpha_type=AlphaType.ZERO_CROSS,
                factor_name=factor_name,
                signal_expr="ZERO_CROSS",
            )

        elif self.genome_type == "crossover":
            factor_name = _build_factor_name(self.factor, self.window)
            factor_name_2 = _build_factor_name(self.factor_2 or "", self.window_2)
            return Alpha(
                alpha_type=AlphaType.CROSSOVER,
                factor_name=factor_name,
                signal_expr=f"CROSS_{factor_name_2}",
                factor_name_2=factor_name_2,
            )

        elif self.genome_type == "composite":
            components = [
                {"alpha_id": aid, "weight": w}
                for aid, w in zip(self.components, self.weights)
            ]
            return Alpha(
                alpha_type=AlphaType.COMPOSITE,
                signal_expr=f"COMBINE_{self.operator}",
                components=components,
                combine_method=self.operator,
            )

        return Alpha()


# ---- 辅助函数 ----

def _parse_factor_name(name: str) -> Tuple[str, Optional[int]]:
    """
    解析因子名 → (base_name, window)

    "RSI14" → ("RSI", 14)
    "MOM20" → ("MOM", 20)
    "MA5"   → ("MA", 5)
    "VOL20" → ("VOL", 20)
    "ATR14" → ("ATR", 14)
    "BOLLU20" → ("BOLLU", 20)
    "BOLLL20" → ("BOLLL", 20)
    """
    if not name:
        return ("", None)

    # 从末尾提取数字
    i = len(name) - 1
    while i >= 0 and name[i].isdigit():
        i -= 1

    if i < len(name) - 1:
        base = name[:i + 1]
        window = int(name[i + 1:])
        return (base, window)

    return (name, None)


def _build_factor_name(base: str, window: Optional[int]) -> str:
    """构建因子名"""
    if not base:
        return ""
    if window is not None:
        return f"{base}{window}"
    return base
