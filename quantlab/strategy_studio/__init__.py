"""
Strategy Studio — 策略工作室

把 StrategyBuilder 从"生成器"重构为"装配器"。

核心组件：
  - DependencyResolver: 依赖解析器（解析 ref → 构建依赖图 → 验证完整性）
  - StrategyComposer: 装配器（compose 逻辑）
  - StrategyValidator: 验证器（smoke test）
  - StrategyRuntime: 运行时解释器（P6）

装配流程：
  1. 解析所有 ref 引用
  2. 构建依赖图
  3. 验证依赖完整性
  4. 生成 StrategyPackage
  5. 保存到 storage
  6. （可选）运行 smoke test 验证
"""

from .resolver import DependencyResolver, DependencyGraph, ValidationResult
from .composer import StrategyComposer, ComposeRequest, ComposeResult
from .validator import StrategyValidator, ValidationReport
from .runtime import StrategyRuntime, Bar, Order, BarResult, RunResult

__all__ = [
    "DependencyResolver",
    "DependencyGraph",
    "ValidationResult",
    "StrategyComposer",
    "ComposeRequest",
    "ComposeResult",
    "StrategyValidator",
    "ValidationReport",
    "StrategyRuntime",
    "Bar",
    "Order",
    "BarResult",
    "RunResult",
]
