"""
Strategy Builder — V5.0 可视化策略构建器

核心理念：
  策略不再是 .py 文件，而是 JSON 配置。
  用户通过图形界面选择 Signal + Position + Risk → 编译成 Strategy 对象。

架构：
  StrategySpec（JSON 配置）
      ↓  compiler.compile()
  CompiledStrategy（可运行的 Strategy 子类）

StrategySpec 示例：
  {
    "name": "RSI_Momentum_Strategy",
    "signals": [
      {"type": "threshold", "factor": "RSI14", "op": "<", "value": 30, "direction": "long"},
      {"type": "threshold", "factor": "Momentum20", "op": ">", "value": 0, "direction": "long"}
    ],
    "signal_logic": "AND",
    "position": {"type": "target", "value": 1.0},
    "risk": {"max_position": 1.0, "stop_loss": 0.05}
  }

用法：
    from quantlab.strategy_builder import StrategyBuilder

    builder = StrategyBuilder()
    spec = {...}
    strategy = builder.compile(spec)
    # strategy 是一个可运行的 BaseStrategy 子类实例
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type

import numpy as np

logger = logging.getLogger("quantlab.strategy_builder")


# ============================================================
# Data Models
# ============================================================

@dataclass(slots=True)
class SignalRule:
    """信号规则（对应前端的一行 Signal 选择）"""
    type: str           # "threshold" / "crossover" / "zero_cross"
    factor: str         # 因子名
    op: str = "<"       # 操作符（threshold 用）
    value: float = 30.0 # 阈值（threshold 用）
    direction: str = "long"  # "long" / "short" / "both"
    # crossover 专用
    fast_factor: str = ""
    slow_factor: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SignalRule":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass(slots=True)
class PositionConfig:
    """仓位配置"""
    type: str = "target"    # "target" / "equal_weight" / "risk_parity"
    value: float = 1.0      # 目标仓位比例
    max_position: float = 1.0
    min_position: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PositionConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass(slots=True)
class RiskConfig:
    """风控配置"""
    stop_loss: float = 0.0      # 止损比例 0=不启用
    take_profit: float = 0.0    # 止盈比例 0=不启用
    max_drawdown: float = 0.0   # 最大回撤限制 0=不启用
    trailing_stop: float = 0.0  # 移动止损 0=不启用

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RiskConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass(slots=True)
class StrategySpec:
    """策略规格（JSON 可序列化）"""
    name: str
    signals: List[SignalRule] = field(default_factory=list)
    signal_logic: str = "AND"   # "AND" / "OR" / "MAJORITY"
    position: PositionConfig = field(default_factory=PositionConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    spec_id: str = ""

    def __post_init__(self):
        if not self.spec_id:
            self.spec_id = self._compute_id()
        if not self.created_at:
            self.created_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def _compute_id(self) -> str:
        raw = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return f"spec_{hashlib.md5(raw.encode()).hexdigest()[:10]}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "signals": [s.to_dict() for s in self.signals],
            "signal_logic": self.signal_logic,
            "position": self.position.to_dict(),
            "risk": self.risk.to_dict(),
            "description": self.description,
            "tags": self.tags,
            "created_at": self.created_at,
            "spec_id": self.spec_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategySpec":
        signals = [SignalRule.from_dict(s) for s in d.get("signals", [])]
        position = PositionConfig.from_dict(d.get("position", {}))
        risk = RiskConfig.from_dict(d.get("risk", {}))
        return cls(
            name=d["name"],
            signals=signals,
            signal_logic=d.get("signal_logic", "AND"),
            position=position,
            risk=risk,
            description=d.get("description", ""),
            tags=d.get("tags", []),
            created_at=d.get("created_at", ""),
            spec_id=d.get("spec_id", ""),
        )


# ============================================================
# Compiler
# ============================================================

class StrategyCompiler:
    """
    将 StrategySpec 编译成可运行的 Strategy 对象

    流程：
      1. 解析 SignalRule → 生成 on_bar 中的信号逻辑
      2. 组合信号（AND/OR/MAJORITY）
      3. 应用仓位配置
      4. 应用风控规则
      5. 动态创建 Strategy 子类
    """

    def compile(self, spec: StrategySpec):
        """
        编译策略规格为可运行的 Strategy 类

        返回一个动态创建的 BaseStrategy 子类
        """
        from ..strategy.base import BaseStrategy

        # 捕获 spec 到闭包
        _spec = spec
        _signal_rules = list(spec.signals)
        _logic = spec.signal_logic
        _pos = spec.position
        _risk = spec.risk

        class CompiledStrategy(BaseStrategy):
            """动态编译的策略"""
            strategy_id = _spec.spec_id
            strategy_name = _spec.name
            strategy_description = _spec.description or f"Compiled from {_spec.name}"
            strategy_tags = _spec.tags + ["compiled"]

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._signal_rules = _signal_rules
                self._logic = _logic
                self._pos_config = _pos
                self._risk_config = _risk

            def on_bar(self, ctx):
                """
                编译生成的 on_bar 逻辑

                1. 从 ctx 获取因子值
                2. 逐条 SignalRule 评估
                3. 组合信号
                4. 应用仓位
                5. 应用风控
                """
                # 1. 评估每条信号规则
                raw_signals = []
                for rule in self._signal_rules:
                    sig = self._evaluate_rule(rule, ctx)
                    raw_signals.append(sig)

                # 2. 组合信号
                if not raw_signals:
                    return 0

                combined = self._combine_signals(raw_signals)

                # 3. 应用仓位
                target = combined * self._pos_config.value

                # 4. 应用风控
                target = self._apply_risk(target, ctx)

                return target

            def _evaluate_rule(self, rule: SignalRule, ctx) -> int:
                """评估单条信号规则"""
                try:
                    if rule.type == "threshold":
                        factor_val = self._get_factor(rule.factor, ctx)
                        if factor_val is None:
                            return 0

                        if rule.op == "<":
                            hit = factor_val < rule.value
                        elif rule.op == "<=":
                            hit = factor_val <= rule.value
                        elif rule.op == ">":
                            hit = factor_val > rule.value
                        elif rule.op == ">=":
                            hit = factor_val >= rule.value
                        elif rule.op == "==":
                            hit = factor_val == rule.value
                        else:
                            hit = False

                        if hit:
                            return 1 if rule.direction in ("long", "both") else -1
                        return 0

                    elif rule.type == "crossover":
                        fast_val = self._get_factor(rule.fast_factor, ctx)
                        slow_val = self._get_factor(rule.slow_factor, ctx)
                        if fast_val is None or slow_val is None:
                            return 0
                        # 简化：fast > slow → 1, fast < slow → -1
                        if fast_val > slow_val:
                            return 1
                        elif fast_val < slow_val:
                            return -1
                        return 0

                    elif rule.type == "zero_cross":
                        factor_val = self._get_factor(rule.factor, ctx)
                        if factor_val is None:
                            return 0
                        if factor_val > 0:
                            return 1
                        elif factor_val < 0:
                            return -1
                        return 0

                except Exception as e:
                    logger.warning(f"Rule evaluation error: {e}")
                    return 0

                return 0

            def _get_factor(self, name: str, ctx) -> Optional[float]:
                """从上下文获取因子值"""
                # 尝试从 ctx.bar 获取
                if hasattr(ctx, 'bar') and hasattr(ctx.bar, name):
                    return getattr(ctx.bar, name)
                # 尝试从 ctx.data 获取
                if hasattr(ctx, 'data') and name in ctx.data:
                    val = ctx.data[name]
                    if isinstance(val, (int, float)):
                        return float(val)
                    return None
                # 尝试从 ctx.attributes 获取
                if hasattr(ctx, 'attributes') and name in ctx.attributes:
                    val = ctx.attributes[name]
                    if isinstance(val, (int, float)):
                        return float(val)
                return None

            def _combine_signals(self, signals: List[int]) -> int:
                """组合多个信号"""
                if self._logic == "AND":
                    # 所有信号都 > 0 → 1，所有都 < 0 → -1
                    if all(s > 0 for s in signals):
                        return 1
                    elif all(s < 0 for s in signals):
                        return -1
                    return 0
                elif self._logic == "OR":
                    # 任一信号 > 0 → 1
                    if any(s > 0 for s in signals):
                        return 1
                    elif any(s < 0 for s in signals):
                        return -1
                    return 0
                elif self._logic == "MAJORITY":
                    pos = sum(1 for s in signals if s > 0)
                    neg = sum(1 for s in signals if s < 0)
                    if pos > neg:
                        return 1
                    elif neg > pos:
                        return -1
                    return 0
                return 0

            def _apply_risk(self, target: float, ctx) -> float:
                """应用风控规则"""
                risk = self._risk_config
                if risk.stop_loss > 0 and hasattr(ctx, 'portfolio'):
                    # 简化止损逻辑
                    pass
                # 限制仓位范围
                target = max(self._pos_config.min_position, min(target, self._pos_config.max_position))
                return target

        CompiledStrategy.__name__ = spec.name.replace(" ", "")
        CompiledStrategy.__qualname__ = spec.name.replace(" ", "")
        return CompiledStrategy


# ============================================================
# Strategy Builder (Facade)
# ============================================================

class StrategyBuilder:
    """
    策略构建器（门面模式）

    统一管理：
      - 创建 StrategySpec
      - 编译为 Strategy
      - 保存/加载规格
      - 列出已保存的策略
    """

    def __init__(self) -> None:
        self.compiler = StrategyCompiler()
        self._specs: Dict[str, StrategySpec] = {}

    def create_spec(
        self,
        name: str,
        signals: List[Dict[str, Any]],
        signal_logic: str = "AND",
        position: Optional[Dict[str, Any]] = None,
        risk: Optional[Dict[str, Any]] = None,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> StrategySpec:
        """创建策略规格"""
        rules = [SignalRule.from_dict(s) for s in signals]
        pos = PositionConfig.from_dict(position or {})
        risk_cfg = RiskConfig.from_dict(risk or {})

        spec = StrategySpec(
            name=name,
            signals=rules,
            signal_logic=signal_logic,
            position=pos,
            risk=risk_cfg,
            description=description,
            tags=tags or [],
        )
        self._specs[spec.spec_id] = spec
        return spec

    def compile(self, spec: StrategySpec):
        """编译策略规格为 Strategy 类"""
        return self.compiler.compile(spec)

    def compile_and_instantiate(self, spec: StrategySpec):
        """编译并实例化策略"""
        cls = self.compiler.compile(spec)
        return cls()

    def get_spec(self, spec_id: str) -> Optional[StrategySpec]:
        return self._specs.get(spec_id)

    def list_specs(self) -> List[Dict[str, Any]]:
        return [
            {
                "spec_id": s.spec_id,
                "name": s.name,
                "description": s.description,
                "signal_count": len(s.signals),
                "signal_logic": s.signal_logic,
                "position_type": s.position.type,
                "position_value": s.position.value,
                "tags": s.tags,
                "created_at": s.created_at,
            }
            for s in self._specs.values()
        ]

    def delete_spec(self, spec_id: str) -> bool:
        if spec_id in self._specs:
            del self._specs[spec_id]
            return True
        return False

    def update_spec(self, spec_id: str, updates: Dict[str, Any]) -> Optional[StrategySpec]:
        """更新策略规格"""
        spec = self._specs.get(spec_id)
        if not spec:
            return None

        if "name" in updates:
            spec.name = updates["name"]
        if "description" in updates:
            spec.description = updates["description"]
        if "tags" in updates:
            spec.tags = updates["tags"]
        if "signals" in updates:
            spec.signals = [SignalRule.from_dict(s) for s in updates["signals"]]
        if "signal_logic" in updates:
            spec.signal_logic = updates["signal_logic"]
        if "position" in updates:
            spec.position = PositionConfig.from_dict(updates["position"])
        if "risk" in updates:
            spec.risk = RiskConfig.from_dict(updates["risk"])

        # 重新计算 ID
        spec.spec_id = spec._compute_id()
        self._specs[spec.spec_id] = spec
        return spec


# ============================================================
# Templates
# ============================================================

STRATEGY_TEMPLATES = {
    "long_only": {
        "name": "Long Only Strategy",
        "description": "单信号做多策略",
        "signals": [
            {"type": "threshold", "factor": "RSI14", "op": "<", "value": 30, "direction": "long"}
        ],
        "signal_logic": "AND",
        "position": {"type": "target", "value": 1.0},
        "risk": {"stop_loss": 0, "take_profit": 0, "max_drawdown": 0, "trailing_stop": 0},
        "tags": ["template", "long_only"],
    },
    "long_short": {
        "name": "Long-Short Strategy",
        "description": "信号驱动多空策略",
        "signals": [
            {"type": "threshold", "factor": "RSI14", "op": "<", "value": 30, "direction": "long"},
            {"type": "threshold", "factor": "RSI14", "op": ">", "value": 70, "direction": "short"},
        ],
        "signal_logic": "OR",
        "position": {"type": "target", "value": 1.0},
        "risk": {"stop_loss": 0.05, "take_profit": 0, "max_drawdown": 0, "trailing_stop": 0},
        "tags": ["template", "long_short"],
    },
    "crossover": {
        "name": "MA Crossover Strategy",
        "description": "均线交叉策略",
        "signals": [
            {"type": "crossover", "factor": "", "op": "", "value": 0, "direction": "long",
             "fast_factor": "MA5", "slow_factor": "MA20"},
        ],
        "signal_logic": "AND",
        "position": {"type": "target", "value": 1.0},
        "risk": {"stop_loss": 0, "take_profit": 0, "max_drawdown": 0, "trailing_stop": 0},
        "tags": ["template", "crossover"],
    },
    "multi_signal": {
        "name": "Multi-Signal Strategy",
        "description": "多信号组合策略",
        "signals": [
            {"type": "threshold", "factor": "RSI14", "op": "<", "value": 30, "direction": "long"},
            {"type": "threshold", "factor": "Momentum20", "op": ">", "value": 0, "direction": "long"},
        ],
        "signal_logic": "AND",
        "position": {"type": "target", "value": 1.0},
        "risk": {"stop_loss": 0.05, "take_profit": 0.1, "max_drawdown": 0.15, "trailing_stop": 0},
        "tags": ["template", "multi_signal"],
    },
}
