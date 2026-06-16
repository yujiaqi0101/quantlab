"""
事件类型
所有事件都基于这个基类
未来加新事件：
   BarEvent / TickEvent / NewsEvent / ...
"""

from dataclasses import (
    dataclass,
    field,
)
from typing import Any


@dataclass(slots=True)
class Event:

    type: str

    timestamp: object = None

    payload: Any = None


# ----------------------------------------------------------------
# MarketEvent：市场行情
# V1 暂用 Bar 行情
# 未来 Tick 行情：
#   MarketEvent(type="TICK", payload={symbol, price, volume})
# 策略不需要改：监听 MarketEvent 即可
# ----------------------------------------------------------------


@dataclass(slots=True)
class MarketEvent(Event):

    type: str = "MARKET"

    symbol: str = ""

    data: Any = None


# ----------------------------------------------------------------
# SignalEvent：策略信号
# 策略监听 MarketEvent
# 产出 SignalEvent（direction/score）
# ----------------------------------------------------------------


@dataclass(slots=True)
class SignalEvent(Event):

    type: str = "SIGNAL"

    symbol: str = ""

    direction: int = 0

    score: float = 0.0


# ----------------------------------------------------------------
# OrderEvent：下单
# 组合构建器监听 SignalEvent
# 产出 OrderEvent（symbol, quantity）
# ----------------------------------------------------------------


@dataclass(slots=True)
class OrderEvent(Event):

    type: str = "ORDER"

    symbol: str = ""

    quantity: int = 0


# ----------------------------------------------------------------
# FillEvent：成交
# 撮合器监听 OrderEvent
# 撮合成功产出 FillEvent
# 仓位/资金监听 FillEvent 更新
# ----------------------------------------------------------------


@dataclass(slots=True)
class FillEvent(Event):

    type: str = "FILL"

    symbol: str = ""

    quantity: int = 0

    price: float = 0.0

    commission: float = 0.0


EVENT_TYPES = (
    MarketEvent,
    SignalEvent,
    OrderEvent,
    FillEvent,
)


# ================================================================
# V2.0 Research Events — 研究流程事件
#
# 目的：让系统知道下一步该做什么
# 例如：FactorCreated → 自动提示创建 Signal
#       BacktestFinished → 自动检查是否加入 Candidate
# ================================================================


@dataclass(slots=True)
class FactorCreatedEvent(Event):
    """因子创建完成"""
    type: str = "FACTOR_CREATED"
    factor_name: str = ""
    category: str = ""


@dataclass(slots=True)
class SignalCreatedEvent(Event):
    """信号创建完成"""
    type: str = "SIGNAL_CREATED"
    signal_name: str = ""
    factor_name: str = ""
    signal_type: str = ""  # threshold / crossover / composite


@dataclass(slots=True)
class StrategyCreatedEvent(Event):
    """策略创建完成"""
    type: str = "STRATEGY_CREATED"
    strategy_id: str = ""
    strategy_name: str = ""
    from_builder: bool = False  # 是否来自 Strategy Builder


@dataclass(slots=True)
class BacktestFinishedEvent(Event):
    """回测完成"""
    type: str = "BACKTEST_FINISHED"
    experiment_id: str = ""
    strategy_id: str = ""
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0


@dataclass(slots=True)
class SweepFinishedEvent(Event):
    """参数扫描完成"""
    type: str = "SWEEP_FINISHED"
    sweep_id: str = ""
    strategy_id: str = ""
    total_combos: int = 0
    best_sharpe: float = 0.0


@dataclass(slots=True)
class CandidateGeneratedEvent(Event):
    """候选策略生成"""
    type: str = "CANDIDATE_GENERATED"
    strategy_id: str = ""
    experiment_id: str = ""
    sharpe: float = 0.0
    max_drawdown: float = 0.0


RESEARCH_EVENT_TYPES = (
    FactorCreatedEvent,
    SignalCreatedEvent,
    StrategyCreatedEvent,
    BacktestFinishedEvent,
    SweepFinishedEvent,
    CandidateGeneratedEvent,
)
