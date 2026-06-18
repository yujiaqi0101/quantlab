"""
Deployment Manager — 部署管理器

T1 第八模块：Research → Deploy 闭环

  Deploy Strategy 按钮 → 启动 Runtime + Scheduler + Broker + 策略
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..runtime import Runtime

logger = logging.getLogger("quantlab.execution.deployment")


class DeployStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass
class DeployRequest:
    """部署请求"""
    strategy_id: str
    symbols: List[str]
    params: Dict = field(default_factory=dict)
    initial_capital: float = 100000.0
    broker_type: str = "PAPER"       # PAPER / BINANCE
    strategy_name: str = ""

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name or self.strategy_id,
            "symbols": self.symbols,
            "params": self.params,
            "initial_capital": self.initial_capital,
            "broker_type": self.broker_type,
        }


@dataclass
class DeployResult:
    """部署结果"""
    deploy_id: str = field(default_factory=lambda: f"DEPLOY-{uuid.uuid4().hex[:8]}")
    strategy_id: str = ""
    status: DeployStatus = DeployStatus.PENDING
    message: str = ""
    deployed_at: int = 0
    runtime_status: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "deploy_id": self.deploy_id,
            "strategy_id": self.strategy_id,
            "status": self.status.value,
            "message": self.message,
            "deployed_at": self.deployed_at,
            "runtime_status": self.runtime_status,
        }


@dataclass
class DeploymentRecord:
    """部署记录"""
    deploy_id: str
    strategy_id: str
    request: DeployRequest
    result: DeployResult
    runtime: Optional[Runtime] = None
    created_at: int = 0

    def to_dict(self) -> Dict:
        return {
            "deploy_id": self.deploy_id,
            "strategy_id": self.strategy_id,
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
            "created_at": self.created_at,
        }


class DeploymentManager:
    """
    部署管理器

    用法：
        manager = DeploymentManager()
        result = manager.deploy(DeployRequest(
            strategy_id="rsi",
            symbols=["BTCUSDT"],
        ))
        manager.undeploy(result.deploy_id)
    """

    def __init__(self) -> None:
        self._deployments: Dict[str, DeploymentRecord] = {}

    # ------------------------------------------------------------------
    # 部署
    # ------------------------------------------------------------------
    def deploy(self, request: DeployRequest) -> DeployResult:
        """部署策略"""
        deploy_id = f"DEPLOY-{uuid.uuid4().hex[:8]}"
        now = int(time.time() * 1000)

        logger.info(
            f"Deploying strategy: {request.strategy_id} "
            f"(symbols={request.symbols}, capital={request.initial_capital})"
        )

        try:
            # 1. 创建 Runtime
            runtime = Runtime(initial_capital=request.initial_capital)

            # 2. 启动 Runtime
            runtime.start()

            # 3. 部署策略
            runtime.deploy_strategy(
                strategy_id=request.strategy_id,
                symbols=request.symbols,
                params=request.params,
            )

            # 4. 记录
            result = DeployResult(
                deploy_id=deploy_id,
                strategy_id=request.strategy_id,
                status=DeployStatus.RUNNING,
                message=f"Strategy {request.strategy_id} deployed successfully",
                deployed_at=now,
                runtime_status=runtime.get_status(),
            )

            record = DeploymentRecord(
                deploy_id=deploy_id,
                strategy_id=request.strategy_id,
                request=request,
                result=result,
                runtime=runtime,
                created_at=now,
            )
            self._deployments[deploy_id] = record

            logger.info(f"Deploy success: {deploy_id}")
            return result

        except Exception as e:
            logger.error(f"Deploy failed: {e}", exc_info=True)
            return DeployResult(
                deploy_id=deploy_id,
                strategy_id=request.strategy_id,
                status=DeployStatus.FAILED,
                message=f"Deploy failed: {e}",
                deployed_at=now,
            )

    def undeploy(self, deploy_id: str) -> bool:
        """卸载部署"""
        record = self._deployments.get(deploy_id)
        if not record:
            return False

        try:
            if record.runtime:
                record.runtime.stop()
            record.result.status = DeployStatus.STOPPED
            record.result.message = "Undeployed"
            logger.info(f"Undeploy success: {deploy_id}")
            return True
        except Exception as e:
            logger.error(f"Undeploy failed: {e}")
            return False

    def restart(self, deploy_id: str) -> bool:
        """重启部署"""
        record = self._deployments.get(deploy_id)
        if not record:
            return False
        # 先停再启
        self.undeploy(deploy_id)
        new_result = self.deploy(record.request)
        # 替换记录
        if new_result.status == DeployStatus.RUNNING:
            record.result = new_result
            return True
        return False

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_deployment(self, deploy_id: str) -> Optional[DeploymentRecord]:
        return self._deployments.get(deploy_id)

    def list_deployments(self, status: Optional[DeployStatus] = None) -> List[DeploymentRecord]:
        """列出所有部署"""
        records = list(self._deployments.values())
        if status:
            records = [r for r in records if r.result.status == status]
        return records

    def get_active_deployments(self) -> List[DeploymentRecord]:
        """获取活跃部署"""
        return self.list_deployments(status=DeployStatus.RUNNING)

    def get_status(self) -> Dict:
        """获取部署管理器状态"""
        records = list(self._deployments.values())
        return {
            "total": len(records),
            "running": sum(1 for r in records if r.result.status == DeployStatus.RUNNING),
            "stopped": sum(1 for r in records if r.result.status == DeployStatus.STOPPED),
            "failed": sum(1 for r in records if r.result.status == DeployStatus.FAILED),
            "deployments": [r.to_dict() for r in records],
        }

    # ------------------------------------------------------------------
    # 运行时操作
    # ------------------------------------------------------------------
    def get_runtime(self, deploy_id: str) -> Optional[Runtime]:
        """获取部署对应的 Runtime"""
        record = self._deployments.get(deploy_id)
        return record.runtime if record else None

    def pause(self, deploy_id: str) -> bool:
        record = self._deployments.get(deploy_id)
        if record and record.runtime:
            record.runtime.pause()
            return True
        return False

    def resume(self, deploy_id: str) -> bool:
        record = self._deployments.get(deploy_id)
        if record and record.runtime:
            record.runtime.resume()
            return True
        return False
