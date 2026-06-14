"""
Kill Switch / Emergency Stop

V3.1：迁移自 risk/kill_switch.py

触发后：
    1) stop = True
    2) 拒新单
    3) LiveEngine 读 stop 决定是否平仓 + 停机
"""

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .limits import MaxDailyLoss
from .checks import RiskCheck


@dataclass
class EmergencyStop:
    """紧急停止"""
    threshold: float              # 负数，如 -0.05
    daily_pnl: float = 0.0
    initial_equity: float = 0.0
    stop: bool = False
    _on_trigger: Optional[Callable] = None

    def set_initial_equity(self, equity: float) -> None:
        self.initial_equity = equity

    def on_trigger(self, callback: Callable) -> None:
        self._on_trigger = callback

    def update_pnl(self, pnl: float) -> None:
        self.daily_pnl = pnl
        if self.initial_equity > 0:
            ret = pnl / self.initial_equity
            if ret <= self.threshold:
                self.stop = True
                if self._on_trigger is not None:
                    self._on_trigger(self)


class KillSwitch(RiskCheck):
    """包装 EmergencyStop"""
    name = "KILL_SWITCH"

    def __init__(self, estop: EmergencyStop):
        self.estop = estop

    def check(self, order, context: Dict) -> bool:
        return not self.estop.stop
