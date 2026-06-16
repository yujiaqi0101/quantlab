"""
QuantLab V2.0 — Services Layer

统一业务入口。所有 API 端点只调 services，不直接碰 core/research/infra。

依赖规则：
  services → core
  services → research
  services → infra
  services 不依赖 studio（不依赖 FastAPI）

每个 Service 是一个 Facade，封装：
  - 业务逻辑编排
  - 缓存策略
  - 事件发布
  - 错误处理

用法：
    from quantlab.services import FactorService, StrategyService

    factor_svc = FactorService()
    factors = factor_svc.list_factors()
"""

from .factor_service import FactorService
from .signal_service import SignalService
from .strategy_service import StrategyService
from .experiment_service import ExperimentService
from .dataset_service import DatasetService

__all__ = [
    "FactorService",
    "SignalService",
    "StrategyService",
    "ExperimentService",
    "DatasetService",
]
