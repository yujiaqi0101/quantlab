"""
QuantLab V2.0 — Services Layer

统一业务入口。所有 API 端点只调 services，不直接碰 core/research/infra。

依赖规则：
  services → core
  services → research
  services → infra
  services 不依赖 api（不依赖 FastAPI）

每个 Service 是一个 Facade，封装：
  - 业务逻辑编排
  - 缓存策略
  - 事件发布
  - 错误处理

用法：
    from quantlab.services import get_service

    factor_svc = get_service("factor")
    factors = factor_svc.list_factors()

    # 或者直接导入
    from quantlab.services import FactorService
    svc = FactorService()
"""

from .factor_service import FactorService
from .signal_service import SignalService
from .strategy_service import StrategyService
from .experiment_service import ExperimentService
from .dataset_service import DatasetService
from .backtest_service import BacktestService
from .alpha_service import AlphaService


__all__ = [
    "FactorService",
    "SignalService",
    "StrategyService",
    "ExperimentService",
    "DatasetService",
    "BacktestService",
    "AlphaService",
    "ServiceContainer",
    "get_service",
]


class ServiceContainer:
    """
    Service 容器 — 统一管理所有 Service 实例

    确保：
      - 单例：每个 Service 只创建一次
      - 懒加载：首次访问时才创建
      - 可注入：测试时可以替换 Service
    """

    def __init__(self) -> None:
        self._services: dict = {}
        self._factories: dict = {}

    def register(self, name: str, factory=None) -> None:
        """注册 Service 工厂"""
        if factory is not None:
            self._factories[name] = factory
        # 清除缓存，下次访问时重新创建
        self._services.pop(name, None)

    def get(self, name: str):
        """获取 Service 实例（懒加载 + 单例）"""
        if name not in self._services:
            if name in self._factories:
                self._services[name] = self._factories[name]()
            else:
                self._services[name] = self._create_default(name)
        return self._services[name]

    def _create_default(self, name: str):
        """默认 Service 创建"""
        if name == "factor":
            return FactorService()
        elif name == "signal":
            return SignalService()
        elif name == "strategy":
            return StrategyService()
        elif name == "experiment":
            return ExperimentService()
        elif name == "dataset":
            return DatasetService()
        elif name == "backtest":
            return BacktestService()
        elif name == "alpha":
            return AlphaService()
        else:
            raise KeyError(f"Unknown service: {name}")

    @property
    def factor(self) -> FactorService:
        return self.get("factor")

    @property
    def signal(self) -> SignalService:
        return self.get("signal")

    @property
    def strategy(self) -> StrategyService:
        return self.get("strategy")

    @property
    def experiment(self) -> ExperimentService:
        return self.get("experiment")

    @property
    def dataset(self) -> DatasetService:
        return self.get("dataset")

    @property
    def backtest(self) -> BacktestService:
        return self.get("backtest")

    @property
    def alpha(self) -> AlphaService:
        return self.get("alpha")

    def list_services(self) -> list:
        """列出所有已注册的 Service 名称"""
        return ["factor", "signal", "strategy", "experiment", "dataset", "backtest", "alpha"]

    def reset(self) -> None:
        """重置所有 Service（测试用）"""
        self._services.clear()


# 全局单例
_container: ServiceContainer = ServiceContainer()


def get_service(name: str):
    """获取 Service 实例"""
    return _container.get(name)


def get_container() -> ServiceContainer:
    """获取 Service 容器"""
    return _container
