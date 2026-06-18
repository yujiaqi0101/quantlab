"""
Deployment Profile — 策略上线配置

ML Lab M5 第七部分：策略上线配置

  配置：
    strategy:  LGBM_Momentum
    broker:    paper
    capital:   100000
    max_position: 0.2

  未来：
    Paper → Binance
    只改配置。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.strategy.deployment")


# ------------------------------------------------------------------
# 部署环境
# ------------------------------------------------------------------

class DeploymentEnv(str, Enum):
    """部署环境"""
    BACKTEST = "backtest"      # 回测
    PAPER = "paper"            # 模拟盘
    LIVE = "live"              # 实盘


class DeploymentStatus(str, Enum):
    """部署状态"""
    DRAFT = "DRAFT"            # 草稿
    READY = "READY"            # 就绪
    RUNNING = "RUNNING"        # 运行中
    STOPPED = "STOPPED"        # 已停止
    FAILED = "FAILED"          # 失败


# ------------------------------------------------------------------
# Deployment Profile
# ------------------------------------------------------------------

@dataclass
class DeploymentProfile:
    """
    部署配置

    用法：
        profile = DeploymentProfile(
            strategy_id="MLS-xxx",
            env=DeploymentEnv.PAPER,
            broker="paper",
            capital=100000,
            max_position=0.2,
        )
        profile.save("storage/deployments/profile_xxx.json")
    """
    # 标识
    profile_id: str = field(default_factory=lambda: f"DEP-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""

    # 策略
    strategy_id: str = ""                # MLStrategy ID
    strategy_name: str = ""
    model_version_id: str = ""           # 关联的 ModelVersion

    # 环境
    env: DeploymentEnv = DeploymentEnv.BACKTEST
    status: DeploymentStatus = DeploymentStatus.DRAFT

    # 经纪商
    broker: str = "paper"                # paper / binance / ibkr
    broker_config: Dict[str, Any] = field(default_factory=dict)

    # 资金
    capital: float = 100000.0
    currency: str = "USDT"

    # 仓位限制（覆盖策略自身的 risk_config）
    max_position: float = 0.2
    max_portfolio: float = 1.0
    max_leverage: float = 1.0

    # 标的
    symbols: List[str] = field(default_factory=list)
    timeframe: str = "1h"

    # 运行参数
    rebalance_freq: str = "1h"           # 调仓频率
    slippage_bps: float = 5.0            # 滑点（基点）
    commission_bps: float = 2.0          # 手续费（基点）

    # 风控覆盖
    max_drawdown: float = 0.20
    max_daily_loss: float = 0.05
    kill_switch_enabled: bool = True

    # 元信息
    created_at: str = ""
    updated_at: str = ""
    deployed_at: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "description": self.description,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "model_version_id": self.model_version_id,
            "env": self.env.value,
            "status": self.status.value,
            "broker": self.broker,
            "broker_config": self.broker_config,
            "capital": self.capital,
            "currency": self.currency,
            "max_position": self.max_position,
            "max_portfolio": self.max_portfolio,
            "max_leverage": self.max_leverage,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "rebalance_freq": self.rebalance_freq,
            "slippage_bps": self.slippage_bps,
            "commission_bps": self.commission_bps,
            "max_drawdown": self.max_drawdown,
            "max_daily_loss": self.max_daily_loss,
            "kill_switch_enabled": self.kill_switch_enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "deployed_at": self.deployed_at,
            "author": self.author,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DeploymentProfile":
        return cls(
            profile_id=d.get("profile_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            strategy_id=d.get("strategy_id", ""),
            strategy_name=d.get("strategy_name", ""),
            model_version_id=d.get("model_version_id", ""),
            env=DeploymentEnv(d.get("env", "backtest")),
            status=DeploymentStatus(d.get("status", "DRAFT")),
            broker=d.get("broker", "paper"),
            broker_config=d.get("broker_config", {}),
            capital=d.get("capital", 100000.0),
            currency=d.get("currency", "USDT"),
            max_position=d.get("max_position", 0.2),
            max_portfolio=d.get("max_portfolio", 1.0),
            max_leverage=d.get("max_leverage", 1.0),
            symbols=d.get("symbols", []),
            timeframe=d.get("timeframe", "1h"),
            rebalance_freq=d.get("rebalance_freq", "1h"),
            slippage_bps=d.get("slippage_bps", 5.0),
            commission_bps=d.get("commission_bps", 2.0),
            max_drawdown=d.get("max_drawdown", 0.20),
            max_daily_loss=d.get("max_daily_loss", 0.05),
            kill_switch_enabled=d.get("kill_switch_enabled", True),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            deployed_at=d.get("deployed_at", ""),
            author=d.get("author", ""),
            tags=d.get("tags", []),
        )

    def save(self, path: str) -> None:
        """保存到文件"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"DeploymentProfile saved: {path}")

    @classmethod
    def load(cls, path: str) -> "DeploymentProfile":
        """从文件加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


# ------------------------------------------------------------------
# Deployment Manager
# ------------------------------------------------------------------

class DeploymentManager:
    """
    部署管理器

    用法：
        mgr = DeploymentManager()
        profile = mgr.create_profile(strategy_id="MLS-xxx", env=DeploymentEnv.PAPER)
        mgr.deploy(profile.profile_id)
        mgr.stop(profile.profile_id)
    """

    def __init__(self, storage_dir: str = "storage/deployments") -> None:
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._profiles: Dict[str, DeploymentProfile] = {}
        self._load_all()

    def _load_all(self) -> None:
        """加载所有 profile"""
        if not os.path.exists(self.storage_dir):
            return
        for fname in os.listdir(self.storage_dir):
            if fname.endswith(".json"):
                try:
                    path = os.path.join(self.storage_dir, fname)
                    profile = DeploymentProfile.load(path)
                    self._profiles[profile.profile_id] = profile
                except Exception as e:
                    logger.error(f"Failed to load {fname}: {e}")

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_profile(
        self,
        strategy_id: str,
        env: DeploymentEnv = DeploymentEnv.PAPER,
        **kwargs,
    ) -> DeploymentProfile:
        """创建部署配置"""
        import pandas as pd
        now = pd.Timestamp.now().isoformat()
        profile = DeploymentProfile(
            strategy_id=strategy_id,
            env=env,
            created_at=now,
            updated_at=now,
            **kwargs,
        )
        self._profiles[profile.profile_id] = profile
        self._save(profile)
        logger.info(f"Profile created: {profile.profile_id}")
        return profile

    def get_profile(self, profile_id: str) -> Optional[DeploymentProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(
        self,
        env: Optional[DeploymentEnv] = None,
        status: Optional[DeploymentStatus] = None,
    ) -> List[DeploymentProfile]:
        result = list(self._profiles.values())
        if env:
            result = [p for p in result if p.env == env]
        if status:
            result = [p for p in result if p.status == status]
        return result

    def update_profile(
        self,
        profile_id: str,
        updates: Dict[str, Any],
    ) -> Optional[DeploymentProfile]:
        """更新配置"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return None
        for k, v in updates.items():
            if k in ("env", "status"):
                continue  # 通过专门方法修改
            if hasattr(profile, k):
                setattr(profile, k, v)
        import pandas as pd
        profile.updated_at = pd.Timestamp.now().isoformat()
        self._save(profile)
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        if profile_id not in self._profiles:
            return False
        self._profiles.pop(profile_id)
        path = os.path.join(self.storage_dir, f"{profile_id}.json")
        if os.path.exists(path):
            os.remove(path)
        return True

    # ------------------------------------------------------------------
    # 部署生命周期
    # ------------------------------------------------------------------

    def deploy(self, profile_id: str) -> bool:
        """部署（标记为 RUNNING）"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        if profile.status not in (DeploymentStatus.DRAFT, DeploymentStatus.READY, DeploymentStatus.STOPPED):
            return False
        import pandas as pd
        profile.status = DeploymentStatus.RUNNING
        profile.deployed_at = pd.Timestamp.now().isoformat()
        self._save(profile)
        logger.info(f"Profile deployed: {profile_id} ({profile.env.value})")
        return True

    def stop(self, profile_id: str) -> bool:
        """停止部署"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        if profile.status != DeploymentStatus.RUNNING:
            return False
        profile.status = DeploymentStatus.STOPPED
        self._save(profile)
        logger.info(f"Profile stopped: {profile_id}")
        return True

    def mark_failed(self, profile_id: str, reason: str = "") -> bool:
        """标记失败"""
        profile = self._profiles.get(profile_id)
        if not profile:
            return False
        profile.status = DeploymentStatus.FAILED
        self._save(profile)
        logger.warning(f"Profile failed: {profile_id} ({reason})")
        return True

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _save(self, profile: DeploymentProfile) -> None:
        path = os.path.join(self.storage_dir, f"{profile.profile_id}.json")
        profile.save(path)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._profiles),
            "profiles": [p.to_dict() for p in self._profiles.values()],
        }


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_manager: Optional[DeploymentManager] = None


def get_deployment_manager(storage_dir: str = "storage/deployments") -> DeploymentManager:
    """获取全局 DeploymentManager 单例"""
    global _manager
    if _manager is None:
        _manager = DeploymentManager(storage_dir)
    return _manager
