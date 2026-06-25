"""
QuantLab 量化回测框架
====================

模块组织:
    factors/      — 因子库（算子 + Alpha191 + Alpha101）
    signals/      — 信号策略层（SignalStrategy 基类 + 具体策略）
    engine/       — 回测引擎（BarEngine 等）
    portfolio_construction/ — 组合构建（TopN 等）
    research/     — 实验与报告（Experiment / Report）
    asset/        — 资产注册中心（已实现）
    ml/           — 机器学习实验台（已实现）
    execution/    — 执行层（已实现）
"""

__version__ = "0.1.0"
