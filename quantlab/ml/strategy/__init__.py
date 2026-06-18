"""
ML Strategy — ML 策略模块

ML Lab M5：把 Champion Model 变成 ML Strategy

  M5 第一/二部分：SignalGenerator       — Prediction → Signal
  M5 第三部分：  PositionSizer           — Signal → Position Size
  M5 第四部分：  RiskOverlay             — Position → Risk-adjusted Position
  M5 第五部分：  MLStrategy              — 统一策略接口（on_bar 流程）
  M5 第六部分：  StrategyBuilder         — Champion + FeatureSet → Strategy
  M5 第七部分：  DeploymentProfile       — paper/live 部署配置
  M5 第八部分：  MLBacktestAdapter       — 接入回测
"""

from .signal_generator import (
    Signal, SignalSide, SignalRule, SignalGenerator,
    signals_to_dataframe, summarize_signals,
)
from .position_sizer import (
    PositionSizer, PositionSizeConfig, SizingMode,
    compute_position_stats,
)
from .risk_overlay import (
    RiskOverlay, RiskConfig, RiskState,
)
from .ml_strategy import (
    MLStrategyV2, MLStrategyConfigV2,
)
from .strategy_builder import (
    StrategyBuilder, StrategyBuildRequest,
    get_strategy_builder,
)
from .deployment_profile import (
    DeploymentProfile, DeploymentEnv, DeploymentStatus,
    DeploymentManager, get_deployment_manager,
)
from .backtest_adapter import (
    MLBacktestAdapter, BacktestResult,
    get_backtest_adapter,
)

__all__ = [
    # M5 第二部分：Signal
    "Signal", "SignalSide", "SignalRule", "SignalGenerator",
    "signals_to_dataframe", "summarize_signals",
    # M5 第三部分：PositionSizer
    "PositionSizer", "PositionSizeConfig", "SizingMode",
    "compute_position_stats",
    # M5 第四部分：RiskOverlay
    "RiskOverlay", "RiskConfig", "RiskState",
    # M5 第五部分：MLStrategy
    "MLStrategyV2", "MLStrategyConfigV2",
    # M5 第六部分：Builder
    "StrategyBuilder", "StrategyBuildRequest", "get_strategy_builder",
    # M5 第七部分：Deployment
    "DeploymentProfile", "DeploymentEnv", "DeploymentStatus",
    "DeploymentManager", "get_deployment_manager",
    # M5 第八部分：Backtest Adapter
    "MLBacktestAdapter", "BacktestResult", "get_backtest_adapter",
]
