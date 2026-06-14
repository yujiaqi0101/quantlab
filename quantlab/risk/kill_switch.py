"""
V3.1：re-export
  KillSwitch/EmergencyStop 已迁移到 live/risk/kill_switch.py
"""
from quantlab.live.risk.kill_switch import (
    EmergencyStop,
    KillSwitch,
)

__all__ = ["EmergencyStop", "KillSwitch"]
