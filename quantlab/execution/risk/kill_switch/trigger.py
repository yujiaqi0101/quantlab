"""
Kill Switch 2.0 — 触发器

升级版风控，多条件触发：
  1. 连续亏损
  2. 极端波动
  3. 数据异常
  4. 系统延迟
  5. 日亏损超限
  6. 对账不一致
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.risk.kill_switch")


class KillSwitchTrigger(str, Enum):
    DAILY_LOSS = "DAILY_LOSS"
    CONSECUTIVE_LOSS = "CONSECUTIVE_LOSS"
    EXTREME_VOLATILITY = "EXTREME_VOLATILITY"
    DATA_ANOMALY = "DATA_ANOMALY"
    SYSTEM_LATENCY = "SYSTEM_LATENCY"
    RECONCILE_MISMATCH = "RECONCILE_MISMATCH"
    MANUAL = "MANUAL"


@dataclass
class KillSwitchConfig:
    """Kill Switch 触发配置"""
    daily_loss_threshold: float = -0.05        # -5%
    consecutive_loss_count: int = 5             # 连续 5 笔亏损
    volatility_threshold: float = 0.10          # 10% 单日波动
    latency_threshold_ms: float = 5000          # 5 秒延迟
    reconcile_mismatch_count: int = 3           # 对账不一致次数


@dataclass
class KillSwitchEvent:
    """Kill Switch 触发事件"""
    trigger: KillSwitchTrigger
    message: str
    timestamp: int
    context: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "trigger": self.trigger.value,
            "message": self.message,
            "timestamp": self.timestamp,
            "context": self.context,
        }


class KillSwitchTriggerEngine:
    """
    Kill Switch 触发引擎

    监控多个条件，任一触发即激活 Kill Switch

    用法：
        engine = KillSwitchTriggerEngine(config)
        engine.on_trigger(callback)
        engine.check_daily_pnl(-0.06)  # → 触发 DAILY_LOSS
    """

    def __init__(self, config: KillSwitchConfig = KillSwitchConfig()) -> None:
        self.config = config
        self._active = False
        self._triggers: List[KillSwitchEvent] = []
        self._callbacks: List[Callable[[KillSwitchEvent], None]] = []
        self._consecutive_losses: int = 0
        self._reconcile_mismatches: int = 0

    @property
    def active(self) -> bool:
        return self._active

    @property
    def triggers(self) -> List[KillSwitchEvent]:
        return list(self._triggers)

    def on_trigger(self, callback: Callable[[KillSwitchEvent], None]) -> None:
        self._callbacks.append(callback)

    def activate(self, trigger: KillSwitchTrigger, message: str, context: Dict = None) -> None:
        """激活 Kill Switch"""
        if self._active:
            return
        self._active = True
        event = KillSwitchEvent(
            trigger=trigger,
            message=message,
            timestamp=int(time.time() * 1000),
            context=context or {},
        )
        self._triggers.append(event)
        logger.critical(f"KILL SWITCH TRIGGERED: {trigger.value} - {message}")
        for cb in self._callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Kill switch callback error: {e}")

    def deactivate(self) -> None:
        """手动解除"""
        self._active = False
        self._consecutive_losses = 0
        self._reconcile_mismatches = 0
        logger.info("Kill switch deactivated (manual reset)")

    def check_daily_pnl(self, pnl_pct: float) -> bool:
        """检查日亏损"""
        if pnl_pct <= self.config.daily_loss_threshold:
            self.activate(
                KillSwitchTrigger.DAILY_LOSS,
                f"Daily PnL {pnl_pct:.2%} <= {self.config.daily_loss_threshold:.2%}",
                {"pnl_pct": pnl_pct},
            )
            return True
        return False

    def check_consecutive_loss(self, is_loss: bool) -> bool:
        """检查连续亏损"""
        if is_loss:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0

        if self._consecutive_losses >= self.config.consecutive_loss_count:
            self.activate(
                KillSwitchTrigger.CONSECUTIVE_LOSS,
                f"Consecutive losses: {self._consecutive_losses}",
                {"count": self._consecutive_losses},
            )
            return True
        return False

    def check_volatility(self, daily_range_pct: float) -> bool:
        """检查极端波动"""
        if daily_range_pct >= self.config.volatility_threshold:
            self.activate(
                KillSwitchTrigger.EXTREME_VOLATILITY,
                f"Volatility {daily_range_pct:.2%} >= {self.config.volatility_threshold:.2%}",
                {"volatility": daily_range_pct},
            )
            return True
        return False

    def check_latency(self, latency_ms: float) -> bool:
        """检查系统延迟"""
        if latency_ms >= self.config.latency_threshold_ms:
            self.activate(
                KillSwitchTrigger.SYSTEM_LATENCY,
                f"Latency {latency_ms:.0f}ms >= {self.config.latency_threshold_ms:.0f}ms",
                {"latency_ms": latency_ms},
            )
            return True
        return False

    def check_reconcile(self, mismatch_count: int) -> bool:
        """检查对账不一致"""
        self._reconcile_mismatches += mismatch_count
        if self._reconcile_mismatches >= self.config.reconcile_mismatch_count:
            self.activate(
                KillSwitchTrigger.RECONCILE_MISMATCH,
                f"Reconcile mismatches: {self._reconcile_mismatches}",
                {"mismatches": self._reconcile_mismatches},
            )
            return True
        return False

    def manual_trigger(self, reason: str = "Manual") -> None:
        """手动触发"""
        self.activate(KillSwitchTrigger.MANUAL, reason)
