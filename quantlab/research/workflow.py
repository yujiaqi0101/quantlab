"""
Research Workflow Engine — V2.0

核心思想：系统知道下一步该做什么

流程：
  FactorCreated  → 提示"创建 Signal？"
  SignalCreated  → 提示"创建 Strategy？"
  StrategyCreated → 提示"运行 Backtest？"
  BacktestFinished → 提示"加入 Candidate？"
  SweepFinished  → 提示"查看 Heatmap？"

用法：
    from quantlab.research.workflow import ResearchWorkflowEngine

    engine = ResearchWorkflowEngine(event_bus)
    engine.start()

    # 事件触发后，前端可以通过 API 获取建议
    suggestions = engine.get_suggestions()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..event.event_bus import EventBus
from ..event.event_types import (
    FactorCreatedEvent,
    SignalCreatedEvent,
    StrategyCreatedEvent,
    BacktestFinishedEvent,
    SweepFinishedEvent,
    CandidateGeneratedEvent,
)

logger = logging.getLogger("quantlab.research.workflow")


# ------------------------------------------------------------------
# Suggestion — 系统建议
# ------------------------------------------------------------------

@dataclass(slots=True)
class Suggestion:
    """系统建议"""
    action: str          # "create_signal" / "create_strategy" / "run_backtest" / ...
    label: str           # 显示文本
    description: str     # 详细说明
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0    # 0=最高
    dismissed: bool = False


# ------------------------------------------------------------------
# Workflow Rules — 规则定义
# ------------------------------------------------------------------

WORKFLOW_RULES: Dict[str, List[Dict[str, Any]]] = {
    "FACTOR_CREATED": [
        {
            "action": "create_signal",
            "label": "Create Signal from this Factor",
            "description": "Use this factor to build a trading signal (threshold, crossover, etc.)",
            "priority": 0,
        },
        {
            "action": "ic_analysis",
            "label": "Run IC Analysis",
            "description": "Check the factor's predictive power before building signals",
            "priority": 1,
        },
    ],
    "SIGNAL_CREATED": [
        {
            "action": "create_strategy",
            "label": "Create Strategy from this Signal",
            "description": "Combine this signal with position/risk rules to form a strategy",
            "priority": 0,
        },
        {
            "action": "forward_return",
            "label": "Check Forward Returns",
            "description": "Analyze the signal's forward return profile",
            "priority": 1,
        },
    ],
    "STRATEGY_CREATED": [
        {
            "action": "run_backtest",
            "label": "Run Backtest",
            "description": "Test this strategy on historical data",
            "priority": 0,
        },
        {
            "action": "add_signal",
            "label": "Add More Signals",
            "description": "Combine with additional signals for better filtering",
            "priority": 1,
        },
    ],
    "BACKTEST_FINISHED": [
        {
            "action": "add_candidate",
            "label": "Add to Candidates",
            "description": "This strategy looks promising — add it to the candidate list",
            "priority": 0,
            "condition": "sharpe > 1.0",
        },
        {
            "action": "run_sweep",
            "label": "Run Parameter Sweep",
            "description": "Optimize parameters with a grid search",
            "priority": 1,
        },
        {
            "action": "walk_forward",
            "label": "Walk-Forward Analysis",
            "description": "Validate strategy stability with out-of-sample testing",
            "priority": 2,
        },
    ],
    "SWEEP_FINISHED": [
        {
            "action": "view_heatmap",
            "label": "View Heatmap",
            "description": "Visualize parameter sensitivity",
            "priority": 0,
        },
        {
            "action": "find_candidates",
            "label": "Find Candidates",
            "description": "Auto-select robust parameter combinations",
            "priority": 1,
        },
    ],
}


# ------------------------------------------------------------------
# ResearchWorkflowEngine
# ------------------------------------------------------------------

class ResearchWorkflowEngine:
    """
    研究流程引擎

    监听研究事件 → 生成建议 → 前端展示
    """

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._event_bus = event_bus or EventBus()
        self._suggestions: List[Suggestion] = []
        self._history: List[Dict[str, Any]] = []
        self._handlers: List[Callable] = []

    def start(self) -> None:
        """启动引擎，注册事件监听"""
        self._handlers = [
            self._event_bus.subscribe("FACTOR_CREATED", self._on_factor_created),
            self._event_bus.subscribe("SIGNAL_CREATED", self._on_signal_created),
            self._event_bus.subscribe("STRATEGY_CREATED", self._on_strategy_created),
            self._event_bus.subscribe("BACKTEST_FINISHED", self._on_backtest_finished),
            self._event_bus.subscribe("SWEEP_FINISHED", self._on_sweep_finished),
        ]
        logger.info("ResearchWorkflowEngine started")

    def stop(self) -> None:
        """停止引擎"""
        for h in self._handlers:
            # EventBus doesn't have a clean unsubscribe by handler ref
            pass
        self._handlers.clear()
        logger.info("ResearchWorkflowEngine stopped")

    # ---- 查询 ----

    def get_suggestions(self, include_dismissed: bool = False) -> List[Suggestion]:
        """获取当前建议"""
        if include_dismissed:
            return list(self._suggestions)
        return [s for s in self._suggestions if not s.dismissed]

    def dismiss_suggestion(self, index: int) -> None:
        """忽略建议"""
        if 0 <= index < len(self._suggestions):
            self._suggestions[index].dismissed = True

    def clear_suggestions(self) -> None:
        """清空建议"""
        self._suggestions.clear()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取事件历史"""
        return self._history[-limit:]

    def get_next_step(self) -> Optional[Suggestion]:
        """获取最高优先级的下一步建议"""
        active = [s for s in self._suggestions if not s.dismissed]
        if not active:
            return None
        return min(active, key=lambda s: s.priority)

    # ---- 事件处理 ----

    def _on_factor_created(self, event) -> None:
        self._record(event)
        self._add_suggestions("FACTOR_CREATED", {
            "factor_name": getattr(event, "factor_name", ""),
            "category": getattr(event, "category", ""),
        })

    def _on_signal_created(self, event) -> None:
        self._record(event)
        self._add_suggestions("SIGNAL_CREATED", {
            "signal_name": getattr(event, "signal_name", ""),
            "factor_name": getattr(event, "factor_name", ""),
        })

    def _on_strategy_created(self, event) -> None:
        self._record(event)
        self._add_suggestions("STRATEGY_CREATED", {
            "strategy_id": getattr(event, "strategy_id", ""),
            "strategy_name": getattr(event, "strategy_name", ""),
        })

    def _on_backtest_finished(self, event) -> None:
        self._record(event)
        sharpe = getattr(event, "sharpe", 0)
        context = {
            "experiment_id": getattr(event, "experiment_id", ""),
            "strategy_id": getattr(event, "strategy_id", ""),
            "sharpe": sharpe,
            "max_drawdown": getattr(event, "max_drawdown", 0),
        }
        self._add_suggestions("BACKTEST_FINISHED", context)

        # 自动检查：如果 sharpe > 1.5，自动建议加入候选
        if sharpe > 1.5:
            self._suggestions.insert(0, Suggestion(
                action="add_candidate",
                label="Add to Candidates (Auto-suggested)",
                description=f"Sharpe={sharpe:.2f} exceeds threshold — strong candidate",
                context=context,
                priority=0,
            ))

    def _on_sweep_finished(self, event) -> None:
        self._record(event)
        self._add_suggestions("SWEEP_FINISHED", {
            "sweep_id": getattr(event, "sweep_id", ""),
            "strategy_id": getattr(event, "strategy_id", ""),
            "best_sharpe": getattr(event, "best_sharpe", 0),
        })

    # ---- 内部 ----

    def _record(self, event) -> None:
        self._history.append({
            "type": getattr(event, "type", "UNKNOWN"),
            "timestamp": getattr(event, "timestamp", None),
        })

    def _add_suggestions(self, event_type: str, context: Dict[str, Any]) -> None:
        rules = WORKFLOW_RULES.get(event_type, [])
        for rule in rules:
            # 检查条件
            condition = rule.get("condition")
            if condition and not self._eval_condition(condition, context):
                continue

            self._suggestions.append(Suggestion(
                action=rule["action"],
                label=rule["label"],
                description=rule["description"],
                context=context,
                priority=rule.get("priority", 0),
            ))

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """简单条件评估"""
        try:
            # 支持 "sharpe > 1.0" 格式
            parts = condition.split()
            if len(parts) == 3:
                key, op, val = parts
                ctx_val = context.get(key, 0)
                threshold = float(val)
                if op == ">":
                    return float(ctx_val) > threshold
                elif op == ">=":
                    return float(ctx_val) >= threshold
                elif op == "<":
                    return float(ctx_val) < threshold
        except Exception:
            pass
        return True
