"""
Event Replay Engine V2 — 生产级回放

新增能力：deterministic replay（确定性回放）

输入：market events + strategy logic + config
输出：完全一致结果（bit-level 一致）

用途：debug live trading issues
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("quantlab.execution.fidelity.replay")


class ReplayState(str, Enum):
    IDLE = "IDLE"
    LOADING = "LOADING"
    READY = "READY"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"


@dataclass
class ReplayEvent:
    """回放事件"""
    timestamp: int
    type: str
    data: Dict = field(default_factory=dict)
    sequence: int = 0       # 序列号，保证顺序

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "type": self.type,
            "data": self.data,
            "sequence": self.sequence,
        }

    def fingerprint(self) -> str:
        """事件指纹 — 用于确定性验证"""
        raw = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class ReplayConfig:
    """回放配置"""
    speed: float = 1.0
    deterministic: bool = True    # 确定性模式
    random_seed: int = 42         # 随机种子
    checkpoint_interval: int = 1000  # 每 N 事件做一次 checkpoint


@dataclass
class ReplayCheckpoint:
    """回放检查点"""
    sequence: int
    state_hash: str
    timestamp: int


class DeterministicReplayEngine:
    """
    确定性回放引擎

    用法：
        engine = DeterministicReplayEngine()
        engine.load_events(events)
        engine.set_strategy_handler(strategy_handler)
        engine.set_config(ReplayConfig(deterministic=True))
        result = engine.play()
        # 验证结果一致性
        assert engine.verify(result, expected_hash)
    """

    def __init__(self, config: ReplayConfig = None) -> None:
        self.config = config or ReplayConfig()
        self._events: List[ReplayEvent] = []
        self._position: int = 0
        self._state = ReplayState.IDLE
        self._strategy_handler: Optional[Callable] = None
        self._checkpoints: List[ReplayCheckpoint] = []
        self._output_log: List[Dict] = []
        self._state_hash = hashlib.sha256(b"init").hexdigest()

    @property
    def state(self) -> ReplayState:
        return self._state

    @property
    def position(self) -> int:
        return self._position

    @property
    def total_events(self) -> int:
        return len(self._events)

    @property
    def progress(self) -> float:
        if not self._events:
            return 0.0
        return self._position / len(self._events)

    def load_events(self, events: List[ReplayEvent]) -> None:
        """加载事件序列"""
        self._state = ReplayState.LOADING
        self._events = sorted(events, key=lambda e: (e.timestamp, e.sequence))
        self._position = 0
        self._state = ReplayState.READY
        logger.info(f"ReplayEngine V2: loaded {len(self._events)} events")

    def set_strategy_handler(self, handler: Callable[[ReplayEvent], Any]) -> None:
        self._strategy_handler = handler

    def set_config(self, config: ReplayConfig) -> None:
        self.config = config
        if config.deterministic:
            random.seed(config.random_seed)

    def play(self) -> Dict:
        """执行回放"""
        if self._state != ReplayState.READY:
            logger.warning("ReplayEngine V2: not ready")
            return {}

        self._state = ReplayState.PLAYING
        self._output_log = []

        for i in range(self._position, len(self._events)):
            event = self._events[i]
            self._position = i + 1

            # 执行策略
            output = None
            if self._strategy_handler:
                try:
                    output = self._strategy_handler(event)
                except Exception as e:
                    logger.error(f"Replay handler error at seq={event.sequence}: {e}")
                    output = {"error": str(e)}

            # 记录输出
            log_entry = {
                "sequence": event.sequence,
                "timestamp": event.timestamp,
                "event_type": event.type,
                "event_fingerprint": event.fingerprint(),
                "output": output,
            }
            self._output_log.append(log_entry)

            # 更新状态哈希
            self._update_state_hash(log_entry)

            # checkpoint
            if i > 0 and i % self.config.checkpoint_interval == 0:
                self._checkpoint()

        self._state = ReplayState.FINISHED
        logger.info(
            f"ReplayEngine V2: finished, "
            f"{len(self._output_log)} events processed"
        )

        return self.get_result()

    def _update_state_hash(self, log_entry: Dict) -> None:
        """更新状态哈希（用于确定性验证）"""
        raw = json.dumps(log_entry, sort_keys=True, default=str)
        self._state_hash = hashlib.sha256(
            (self._state_hash + raw).encode()
        ).hexdigest()

    def _checkpoint(self) -> None:
        cp = ReplayCheckpoint(
            sequence=self._position,
            state_hash=self._state_hash,
            timestamp=self._events[self._position - 1].timestamp if self._position > 0 else 0,
        )
        self._checkpoints.append(cp)

    def get_result(self) -> Dict:
        """获取回放结果"""
        return {
            "state": self._state.value,
            "events_processed": len(self._output_log),
            "total_events": self.total_events,
            "final_state_hash": self._state_hash,
            "checkpoints": [
                {
                    "sequence": cp.sequence,
                    "state_hash": cp.state_hash,
                    "timestamp": cp.timestamp,
                }
                for cp in self._checkpoints
            ],
            "config": {
                "deterministic": self.config.deterministic,
                "random_seed": self.config.random_seed,
            },
        }

    def verify(self, expected_hash: str) -> bool:
        """验证回放结果一致性"""
        return self._state_hash == expected_hash

    def get_output_log(self, limit: int = 100) -> List[Dict]:
        return self._output_log[-limit:]

    def get_status(self) -> Dict:
        return {
            "state": self._state.value,
            "position": self._position,
            "total_events": self.total_events,
            "progress": self.progress,
            "checkpoints": len(self._checkpoints),
        }
