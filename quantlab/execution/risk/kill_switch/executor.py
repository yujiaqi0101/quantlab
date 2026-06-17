"""
Kill Switch Executor — 执行器

Kill Switch 触发后执行：
  1. 停止所有策略
  2. 撤销所有订单
  3. 切换只读模式
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from .trigger import KillSwitchEvent, KillSwitchTriggerEngine

logger = logging.getLogger("quantlab.execution.risk.kill_switch.executor")


class KillSwitchExecutor:
    """
    Kill Switch 执行器

    用法：
        executor = KillSwitchExecutor(
            trigger_engine=trigger,
            cancel_all_orders=oms.cancel_all,
            stop_all_strategies=supervisor.stop_all,
        )
        executor.arm()  # 注册回调
    """

    def __init__(
        self,
        trigger_engine: KillSwitchTriggerEngine,
        cancel_all_orders: Optional[Callable] = None,
        stop_all_strategies: Optional[Callable] = None,
        enable_readonly: Optional[Callable] = None,
    ) -> None:
        self._trigger = trigger_engine
        self._cancel_all = cancel_all_orders
        self._stop_all = stop_all_strategies
        self._enable_readonly = enable_readonly
        self._executed: bool = False
        self._execution_log: List[dict] = []

    def arm(self) -> None:
        """注册到触发引擎"""
        self._trigger.on_trigger(self._on_triggered)
        logger.info("KillSwitchExecutor armed")

    def disarm(self) -> None:
        """解除"""
        logger.info("KillSwitchExecutor disarmed")

    @property
    def executed(self) -> bool:
        return self._executed

    @property
    def execution_log(self) -> List[dict]:
        return list(self._execution_log)

    def _on_triggered(self, event: KillSwitchEvent) -> None:
        """Kill Switch 触发时的执行流程"""
        logger.critical(
            f"KillSwitchExecutor executing for: {event.trigger.value}"
        )

        import time
        steps = []

        # 1. 停止所有策略
        if self._stop_all:
            try:
                self._stop_all()
                steps.append({"step": "stop_strategies", "status": "OK", "ts": int(time.time() * 1000)})
                logger.info("KillSwitch: all strategies stopped")
            except Exception as e:
                steps.append({"step": "stop_strategies", "status": "FAIL", "error": str(e), "ts": int(time.time() * 1000)})
                logger.error(f"KillSwitch: stop strategies failed: {e}")

        # 2. 撤销所有订单
        if self._cancel_all:
            try:
                cancelled = self._cancel_all()
                steps.append({"step": "cancel_orders", "status": "OK", "cancelled": cancelled, "ts": int(time.time() * 1000)})
                logger.info(f"KillSwitch: {cancelled} orders cancelled")
            except Exception as e:
                steps.append({"step": "cancel_orders", "status": "FAIL", "error": str(e), "ts": int(time.time() * 1000)})
                logger.error(f"KillSwitch: cancel orders failed: {e}")

        # 3. 切换只读模式
        if self._enable_readonly:
            try:
                self._enable_readonly()
                steps.append({"step": "enable_readonly", "status": "OK", "ts": int(time.time() * 1000)})
                logger.info("KillSwitch: readonly mode enabled")
            except Exception as e:
                steps.append({"step": "enable_readonly", "status": "FAIL", "error": str(e), "ts": int(time.time() * 1000)})
                logger.error(f"KillSwitch: enable readonly failed: {e}")

        self._executed = True
        self._execution_log.append({
            "event": event.to_dict(),
            "steps": steps,
            "timestamp": int(time.time() * 1000),
        })

    def reset(self) -> None:
        """重置执行器"""
        self._executed = False
        self._execution_log.clear()
        self._trigger.deactivate()
        logger.info("KillSwitchExecutor reset")
