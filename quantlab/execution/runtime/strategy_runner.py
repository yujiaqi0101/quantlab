"""
Strategy Runner — 策略运行器

每个策略运行在一个独立的 StrategyRunner 中
实现状态隔离
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("quantlab.execution.runtime.strategy_runner")


class RunnerState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str
    name: str = ""
    symbols: list = field(default_factory=list)
    params: Dict = field(default_factory=dict)
    initial_capital: float = 100000.0


class StrategyRunner:
    """
    策略运行器 — 每个策略一个实例

    用法：
        runner = StrategyRunner(
            config=StrategyConfig(strategy_id="s1"),
            on_signal=signal_handler,
        )
        runner.start()
        runner.on_tick(tick_data)
        runner.stop()
    """

    def __init__(
        self,
        config: StrategyConfig,
        on_signal: Optional[Callable] = None,
    ) -> None:
        self.config = config
        self._on_signal = on_signal
        self._state = RunnerState.IDLE
        self._lock = threading.RLock()
        self._tick_count: int = 0
        self._signal_count: int = 0
        self._error_count: int = 0
        self._last_signal: Optional[Dict] = None
        self._state_history: list = []

    @property
    def strategy_id(self) -> str:
        return self.config.strategy_id

    @property
    def state(self) -> RunnerState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._state == RunnerState.RUNNING

    def start(self) -> None:
        with self._lock:
            if self._state == RunnerState.RUNNING:
                return
            self._set_state(RunnerState.RUNNING)
            logger.info(f"StrategyRunner started: {self.strategy_id}")

    def stop(self) -> None:
        with self._lock:
            if self._state == RunnerState.STOPPED:
                return
            self._set_state(RunnerState.STOPPED)
            logger.info(f"StrategyRunner stopped: {self.strategy_id}")

    def pause(self) -> None:
        self._set_state(RunnerState.PAUSED)

    def resume(self) -> None:
        if self._state == RunnerState.PAUSED:
            self._set_state(RunnerState.RUNNING)

    def on_tick(self, tick_data: Dict) -> Optional[Dict]:
        """处理 tick，返回信号"""
        if not self.is_running:
            return None

        try:
            self._tick_count += 1
            if self._on_signal:
                signal = self._on_signal(tick_data, self.config)
                if signal:
                    self._signal_count += 1
                    self._last_signal = signal
                    return signal
        except Exception as e:
            self._error_count += 1
            logger.error(f"StrategyRunner {self.strategy_id} error: {e}")
            self._set_state(RunnerState.ERROR)

        return None

    def get_status(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "state": self._state.value,
            "tick_count": self._tick_count,
            "signal_count": self._signal_count,
            "error_count": self._error_count,
            "last_signal": self._last_signal,
        }

    def _set_state(self, state: RunnerState) -> None:
        old = self._state
        self._state = state
        if old != state:
            import time
            self._state_history.append({
                "from": old.value,
                "to": state.value,
                "timestamp": int(time.time() * 1000),
            })
