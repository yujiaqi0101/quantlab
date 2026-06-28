"""
模块 10: Signal Templates

预配置 pipeline，用户直接套用。
内置 8 个模板：TopK / LongShort / Probability / MeanReversion / Momentum /
              Breakout / TripleBarrier / MetaLabeling。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.signal_engine.templates")


@dataclass
class SignalTemplate:
    """信号模板"""

    name: str
    description: str
    pipeline_config: Dict[str, Any] = field(default_factory=dict)
    required_model_type: str = "any"  # regression / classification / any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "pipeline_config": self.pipeline_config,
            "required_model_type": self.required_model_type,
        }


TEMPLATES: Dict[str, SignalTemplate] = {
    "topk": SignalTemplate(
        name="topk",
        description="TopK 截面多头 — 取收益预测最高的 K 个标的做多",
        pipeline_config={
            "generator": {"method": "regression", "use_short": False},
            "ranker": {"method": "topk", "k": 50},
            "scorer": {"method": "rank"},
            "allocator": {"method": "equal_weight"},
            "holding_period": 5,
        },
        required_model_type="regression",
    ),
    "long_short": SignalTemplate(
        name="long_short",
        description="多空对冲 — TopK 多 + BottomK 空",
        pipeline_config={
            "generator": {"method": "regression", "use_short": True},
            "ranker": {"method": "topbottomk", "k_long": 50, "k_short": 50},
            "scorer": {"method": "rank"},
            "allocator": {"method": "equal_weight"},
            "holding_period": 5,
        },
        required_model_type="regression",
    ),
    "probability": SignalTemplate(
        name="probability",
        description="概率阈值 — 分类模型按概率阈值生成信号",
        pipeline_config={
            "generator": {"method": "probability", "long_threshold": 0.6, "short_threshold": 0.4},
            "scorer": {"method": "tanh"},
            "allocator": {"method": "confidence_weight"},
            "holding_period": 3,
        },
        required_model_type="classification",
    ),
    "mean_reversion": SignalTemplate(
        name="mean_reversion",
        description="均值回归 — 预测收益为负时做多（逆向）",
        pipeline_config={
            "generator": {"method": "threshold", "long_threshold": -0.02, "short_threshold": 0.02, "use_short": True},
            "scorer": {"method": "tanh"},
            "allocator": {"method": "equal_weight"},
            "holding_period": 10,
        },
        required_model_type="regression",
    ),
    "momentum": SignalTemplate(
        name="momentum",
        description="动量 — 预测收益为正时做多，追涨",
        pipeline_config={
            "generator": {"method": "threshold", "long_threshold": 0.01, "use_short": False},
            "ranker": {"method": "topk", "k": 30},
            "scorer": {"method": "rank"},
            "allocator": {"method": "confidence_weight"},
            "holding_period": 20,
        },
        required_model_type="regression",
    ),
    "breakout": SignalTemplate(
        name="breakout",
        description="突破 — 高置信度时进场",
        pipeline_config={
            "generator": {"method": "probability", "long_threshold": 0.7, "short_threshold": 0.3},
            "scorer": {"method": "tanh", "scale": 80},
            "allocator": {"method": "kelly", "max_weight": 0.2},
            "holding_period": 7,
        },
        required_model_type="classification",
    ),
    "triple_barrier": SignalTemplate(
        name="triple_barrier",
        description="三重屏障 — 取上下分位，中长期持仓",
        pipeline_config={
            "generator": {"method": "quantile", "long_quantile": 0.9, "short_quantile": 0.1, "use_short": True},
            "scorer": {"method": "zscore"},
            "allocator": {"method": "volatility_scaling"},
            "holding_period": 20,
        },
        required_model_type="regression",
    ),
    "meta_labeling": SignalTemplate(
        name="meta_labeling",
        description="Meta-Labeling — 仅在高置信度时下单，过滤低质量信号",
        pipeline_config={
            "generator": {"method": "classification", "use_short": True},
            "ranker": {"method": "topk", "k": 20},
            "scorer": {"method": "quantile"},
            "allocator": {"method": "kelly", "max_weight": 0.15},
            "holding_period": 5,
        },
        required_model_type="classification",
    ),
}


def get_template(name: str) -> Optional[SignalTemplate]:
    """获取模板"""
    return TEMPLATES.get(name.lower())


def list_templates() -> List[SignalTemplate]:
    """列出所有模板"""
    return list(TEMPLATES.values())


def list_template_names() -> List[str]:
    return list(TEMPLATES.keys())
