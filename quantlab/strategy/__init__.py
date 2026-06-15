"""
V4.1 Strategy Registry

策略注册中心 —— 平台形态的关键。

模块：
  base          BaseStrategy（继承 SignalStrategy，零侵入）
  metadata      StrategyMetadata / StrategyParameter
  versioning    semver + 源码快照（复现性）
  registry      StrategyRegistry（核心）
  loader        自动发现（signals/ + strategies/ + 插件 zip）
  api           服务层（list_strategies / get_strategy / ...）

新策略写法的两种姿势：
  A) 极简（自动推导）
      class MyStrategy(BaseStrategy):
          def __init__(self, period: int = 14):
              self.period = period
          def signal(self, ctx):
              ...

  B) 显式 metadata
      class MyStrategy(BaseStrategy):
          strategy_id = "my"
          strategy_tags = ["my_tag"]
          @classmethod
          def metadata(cls):
              return StrategyMetadata(
                  id="my",
                  parameters=[
                      StrategyParameter(
                          name="period", type="int",
                          default=14, min=2, max=100,
                      ),
                  ],
              )
          ...

旧策略（继承 SignalStrategy）也兼容：
  - get_metadata_for_class() 会从 __init__ 签名自动推导
  - 不需要改一行代码
"""

from .metadata import (
    StrategyMetadata,
    StrategyParameter,
    PARAM_TYPES,
)
from .base import (
    BaseStrategy,
    is_base_strategy,
    is_strategy_class,
    get_metadata_for_class,
)
from .versioning import (
    StrategyVersion,
    parse_version,
    version_lt,
    version_eq,
    snapshot_source,
    source_hash,
    class_fingerprint,
)
from .registry import (
    StrategyRegistry,
    get_strategy_registry,
    set_strategy_registry,
)
from .loader import (
    discover_builtin,
    discover_directory,
    discover_plugin,
    discover_all,
)
from .api import (
    list_strategies,
    get_strategy,
    list_strategy_versions,
    get_strategy_source,
    validate_strategy_params,
    create_strategy,
)
# V4.6 Factor Strategy
from .factor_strategy import FactorStrategy, MultiFactorStrategy


__all__ = [
    # metadata
    "StrategyMetadata",
    "StrategyParameter",
    "PARAM_TYPES",
    # base
    "BaseStrategy",
    "is_base_strategy",
    "is_strategy_class",
    "get_metadata_for_class",
    # versioning
    "StrategyVersion",
    "parse_version",
    "version_lt",
    "version_eq",
    "snapshot_source",
    "source_hash",
    "class_fingerprint",
    # registry
    "StrategyRegistry",
    "get_strategy_registry",
    "set_strategy_registry",
    # loader
    "discover_builtin",
    "discover_directory",
    "discover_plugin",
    "discover_all",
    # api
    "list_strategies",
    "get_strategy",
    "list_strategy_versions",
    "get_strategy_source",
    "validate_strategy_params",
    "create_strategy",
    # V4.6
    "FactorStrategy",
    "MultiFactorStrategy",
]
