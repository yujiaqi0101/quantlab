"""
Execution Profile — 执行配置包

把执行模式从硬编码升级为可注册、可复用的 Package。

4 种实现：
  - PaperExecution: 模拟交易
  - BinanceExecution: 币安实盘
  - ReplayExecution: 回放模式
  - BacktestExecution: 回测模式
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..base import AssetPackage, PackageType

logger = logging.getLogger("quantlab.asset_package.types.execution")


# ==================================================================
# ExecutionProfile 基类
# ==================================================================

@dataclass
class ExecutionProfile(AssetPackage):
    """执行配置包基类"""
    package_type: PackageType = PackageType.EXECUTION

    def get_broker_type(self) -> str:
        """返回 broker 类型标识（用于 Runtime 创建对应 broker）"""
        raise NotImplementedError("Subclass must implement get_broker_type()")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })


# ==================================================================
# 1. PaperExecution — 模拟交易
# ==================================================================

@dataclass
class PaperExecution(ExecutionProfile):
    """模拟交易执行"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001      # 0.1%
    slippage_rate: float = 0.001        # 0.1%

    def to_config(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.initial_capital = config.get("initial_capital", 100000.0)
        self.commission_rate = config.get("commission_rate", 0.001)
        self.slippage_rate = config.get("slippage_rate", 0.001)

    def get_broker_type(self) -> str:
        return "paper"


# ==================================================================
# 2. BinanceExecution — 币安实盘
# ==================================================================

@dataclass
class BinanceExecution(ExecutionProfile):
    """币安实盘执行"""
    api_key: str = ""                   # 实际使用时从环境变量读取
    api_secret: str = ""
    testnet: bool = True                # 默认测试网
    commission_rate: float = 0.001

    def to_config(self) -> Dict[str, Any]:
        # 不输出密钥
        return {
            "testnet": self.testnet,
            "commission_rate": self.commission_rate,
            "has_credentials": bool(self.api_key),
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.testnet = config.get("testnet", True)
        self.commission_rate = config.get("commission_rate", 0.001)
        # 密钥从环境变量读取
        import os
        self.api_key = os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = os.environ.get("BINANCE_API_SECRET", "")

    def get_broker_type(self) -> str:
        return "binance"


# ==================================================================
# 3. ReplayExecution — 回放模式
# ==================================================================

@dataclass
class ReplayExecution(ExecutionProfile):
    """回放模式执行（用于 fidelity 测试）"""
    replay_speed: float = 1.0           # 回放速度倍数
    commission_rate: float = 0.001

    def to_config(self) -> Dict[str, Any]:
        return {
            "replay_speed": self.replay_speed,
            "commission_rate": self.commission_rate,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.replay_speed = config.get("replay_speed", 1.0)
        self.commission_rate = config.get("commission_rate", 0.001)

    def get_broker_type(self) -> str:
        return "replay"


# ==================================================================
# 4. BacktestExecution — 回测模式
# ==================================================================

@dataclass
class BacktestExecution(ExecutionProfile):
    """回测模式执行"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.001

    def to_config(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "commission_rate": self.commission_rate,
            "slippage_rate": self.slippage_rate,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.initial_capital = config.get("initial_capital", 100000.0)
        self.commission_rate = config.get("commission_rate", 0.001)
        self.slippage_rate = config.get("slippage_rate", 0.001)

    def get_broker_type(self) -> str:
        return "backtest"
