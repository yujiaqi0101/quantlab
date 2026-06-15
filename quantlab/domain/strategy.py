"""
Domain — StrategyDefinition

策略的"对外定义"，与 Python 类解耦。
前端用 StrategyDefinition.parameters_schema 自动生成表单。

为什么：
  前端不应该知道 "class MACrossStrategy"，
  前端只需要："有一个 fast 参数，默认 20，范围 5~100"。
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ParamSchema:
    """
    单个参数 schema（前端表单生成用）

    type        int / float / bool / str / choice
    default     默认值
    min / max   数值范围（int / float 用）
    choices     枚举选项（choice 用）
    description 描述
    """
    name: str
    type: str = "int"
    default: Any = None
    min: Any = None
    max: Any = None
    choices: List[Any] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StrategyDefinition:
    """
    策略的对外定义

    id                   短 ID（前端用："ma_cross"）
    name                 显示名
    class_path           实际 Python 类路径（"quantlab.signals.MACrossStrategy"）
    description          描述
    parameters_schema    List[ParamSchema]（前端按这个生成表单）
    default_parameters   Dict[str, Any]（默认值）
    param_space          网格 / 优化空间
    tags                 标签列表
    """
    id: str
    name: str = ""
    class_path: str = ""
    description: str = ""
    parameters_schema: List[ParamSchema] = field(
        default_factory=list
    )
    default_parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    param_space: Dict[str, Any] = field(
        default_factory=dict
    )
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "class_path": self.class_path,
            "description": self.description,
            "parameters_schema": [
                p.to_dict() for p in self.parameters_schema
            ],
            "default_parameters": dict(
                self.default_parameters
            ),
            "param_space": dict(self.param_space),
            "tags": list(self.tags),
        }

    def schema_dict(self) -> Dict[str, Dict[str, Any]]:
        """把 parameters_schema 收成 {name: schema_dict}"""
        return {
            p.name: {
                "type": p.type,
                "default": p.default,
                "min": p.min,
                "max": p.max,
                "choices": list(p.choices),
                "description": p.description,
            }
            for p in self.parameters_schema
        }


def make_ma_cross_definition() -> StrategyDefinition:
    """内置：MA Cross 策略定义"""
    return StrategyDefinition(
        id="ma_cross",
        name="MA Cross",
        class_path="quantlab.signals.MACrossStrategy",
        description="双均线交叉策略（多标的）",
        parameters_schema=[
            ParamSchema(
                name="fast",
                type="int",
                default=20,
                min=2,
                max=200,
                description="快线周期",
            ),
            ParamSchema(
                name="slow",
                type="int",
                default=60,
                min=2,
                max=400,
                description="慢线周期",
            ),
        ],
        default_parameters={"fast": 20, "slow": 60},
        param_space={
            "fast": [5, 10, 20, 30, 50],
            "slow": [30, 60, 90, 120],
        },
        tags=["classic", "trend"],
    )


def make_rsi_definition() -> StrategyDefinition:
    """内置：RSI 策略定义"""
    return StrategyDefinition(
        id="rsi",
        name="RSI",
        class_path="quantlab.signals.RSIStrategy",
        description="RSI 均值回归 / 趋势跟随",
        parameters_schema=[
            ParamSchema(
                name="period", type="int",
                default=14, min=2, max=100,
                description="RSI 周期",
            ),
            ParamSchema(
                name="oversold", type="float",
                default=30.0, min=1, max=50,
                description="超卖阈值",
            ),
            ParamSchema(
                name="overbought", type="float",
                default=70.0, min=50, max=99,
                description="超买阈值",
            ),
            ParamSchema(
                name="use_trend_filter", type="bool",
                default=False,
                description="是否启用趋势过滤",
            ),
            ParamSchema(
                name="trend_period", type="int",
                default=200, min=10, max=500,
                description="趋势均线周期",
            ),
        ],
        default_parameters={
            "period": 14,
            "oversold": 30.0,
            "overbought": 70.0,
            "use_trend_filter": False,
            "trend_period": 200,
        },
        param_space={
            "period": [7, 14, 21],
            "oversold": [20.0, 30.0],
            "overbought": [70.0, 80.0],
        },
        tags=["mean_reversion", "oscillator"],
    )
