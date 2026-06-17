"""
Strategy Health — 策略健康监控

监控每个策略的运行状态：
  - 最近 24 小时信号数
  - 最近 24 小时成交数
  - 最近 24 小时收益
  - 最近一次活动时间
  - 运行状态（running / stopped / stalled）

发现：
  - 策略失效（信号数骤降）
  - 策略停摆（长时间无信号）
  - 策略异常（信号多但无成交）

自动报警阈值：
  - 24h 无信号 → STALLED
  - 24h 信号数 < min_signals → LOW_ACTIVITY
  - 24h 无成交 → NO_FILLS
  - 24h 亏损 > max_loss → LOSING

用法：
    from quantlab.observe.health import StrategyHealthMonitor

    monitor = StrategyHealthMonitor()

    # 记录事件
    monitor.record_signal("rsi_strategy")
    monitor.record_fill("rsi_strategy", pnl=100)
    monitor.record_signal("trend_strategy")
    monitor.record_fill("trend_strategy", pnl=-50)

    # 查询健康状态
    health = monitor.get_health("rsi_strategy")
    print(health.to_dict())

    # 全局状态
    all_health = monitor.list_health()
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("quantlab.observe.health")


# ------------------------------------------------------------------
# HealthStatus
# ------------------------------------------------------------------

class HealthStatus(str, Enum):
    HEALTHY = "healthy"               # 健康
    LOW_ACTIVITY = "low_activity"     # 活动不足
    STALLED = "stalled"               # 停摆（长时间无信号）
    NO_FILLS = "no_fills"             # 有信号无成交
    LOSING = "losing"                 # 持续亏损
    STOPPED = "stopped"               # 已停止
    UNKNOWN = "unknown"


# ------------------------------------------------------------------
# StrategyHealth
# ------------------------------------------------------------------

@dataclass
class StrategyHealth:
    """策略健康状态"""
    strategy_id: str
    status: HealthStatus = HealthStatus.UNKNOWN

    # 24h 统计
    signals_24h: int = 0
    fills_24h: int = 0
    pnl_24h: float = 0.0
    n_wins_24h: int = 0
    n_losses_24h: int = 0

    # 时间
    last_signal_time: Optional[str] = None
    last_fill_time: Optional[str] = None
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None

    # 累计
    total_signals: int = 0
    total_fills: int = 0
    total_pnl: float = 0.0

    # 报警
    alerts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "status": self.status.value,
            "signals_24h": self.signals_24h,
            "fills_24h": self.fills_24h,
            "pnl_24h": self.pnl_24h,
            "n_wins_24h": self.n_wins_24h,
            "n_losses_24h": self.n_losses_24h,
            "last_signal_time": self.last_signal_time,
            "last_fill_time": self.last_fill_time,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "total_signals": self.total_signals,
            "total_fills": self.total_fills,
            "total_pnl": self.total_pnl,
            "alerts": self.alerts,
        }


# ------------------------------------------------------------------
# HealthConfig
# ------------------------------------------------------------------

@dataclass
class HealthConfig:
    """健康监控配置"""
    window_hours: int = 24                 # 统计窗口
    min_signals_24h: int = 1               # 24h 最少信号数
    max_loss_24h: float = -1000.0          # 24h 最大亏损
    stalled_hours: float = 6.0             # 超过这个时间无信号 → STALLED
    min_fill_rate: float = 0.1             # 最低成交率（fills/signals）


# ------------------------------------------------------------------
# StrategyHealthMonitor
# ------------------------------------------------------------------

class StrategyHealthMonitor:
    """
    策略健康监控器

    用法：
        monitor = StrategyHealthMonitor()
        monitor.record_signal("rsi_strategy")
        monitor.record_fill("rsi_strategy", pnl=100)
        health = monitor.get_health("rsi_strategy")
    """

    def __init__(self, config: Optional[HealthConfig] = None) -> None:
        self.config = config or HealthConfig()

        # 每个策略的事件队列（带时间戳）
        # strategy_id → deque[(timestamp, event_type, pnl)]
        self._events: Dict[str, Deque[tuple]] = defaultdict(
            lambda: deque(maxlen=10000)
        )

        # 每个策略的基础信息
        self._health: Dict[str, StrategyHealth] = {}

    # ------------------------------------------------------------------
    # 记录事件
    # ------------------------------------------------------------------

    def register_strategy(self, strategy_id: str) -> None:
        """注册策略"""
        if strategy_id not in self._health:
            self._health[strategy_id] = StrategyHealth(
                strategy_id=strategy_id,
                started_at=datetime.now().isoformat(),
            )
            logger.info(f"HealthMonitor: registered strategy {strategy_id}")

    def record_signal(
        self,
        strategy_id: str,
        timestamp: Optional[datetime] = None,
        **metadata,
    ) -> None:
        """记录信号"""
        self.register_strategy(strategy_id)
        ts = timestamp or datetime.now()
        self._events[strategy_id].append((ts, "signal", 0.0, metadata))

        h = self._health[strategy_id]
        h.total_signals += 1
        h.last_signal_time = ts.isoformat()

    def record_fill(
        self,
        strategy_id: str,
        pnl: float = 0.0,
        timestamp: Optional[datetime] = None,
        **metadata,
    ) -> None:
        """记录成交"""
        self.register_strategy(strategy_id)
        ts = timestamp or datetime.now()
        self._events[strategy_id].append((ts, "fill", pnl, metadata))

        h = self._health[strategy_id]
        h.total_fills += 1
        h.total_pnl += pnl
        h.last_fill_time = ts.isoformat()

    def record_stop(self, strategy_id: str, reason: str = "") -> None:
        """记录策略停止"""
        self.register_strategy(strategy_id)
        h = self._health[strategy_id]
        h.status = HealthStatus.STOPPED
        h.stopped_at = datetime.now().isoformat()
        logger.info(
            f"HealthMonitor: strategy {strategy_id} stopped ({reason})"
        )

    # ------------------------------------------------------------------
    # 查询健康状态
    # ------------------------------------------------------------------

    def get_health(self, strategy_id: str) -> StrategyHealth:
        """获取策略健康状态"""
        self.register_strategy(strategy_id)
        self._update_health(strategy_id)
        return self._health[strategy_id]

    def list_health(self) -> List[StrategyHealth]:
        """列出所有策略健康状态"""
        for sid in list(self._health.keys()):
            self._update_health(sid)
        return list(self._health.values())

    def _update_health(self, strategy_id: str) -> None:
        """更新策略健康状态"""
        h = self._health[strategy_id]
        if h.status == HealthStatus.STOPPED:
            return  # 停止的策略不再更新

        now = datetime.now()
        window_start = now - timedelta(hours=self.config.window_hours)

        # 统计窗口内事件
        signals_24h = 0
        fills_24h = 0
        pnl_24h = 0.0
        n_wins = 0
        n_losses = 0
        last_signal_ts: Optional[datetime] = None
        last_fill_ts: Optional[datetime] = None

        for ts, event_type, pnl, _meta in self._events[strategy_id]:
            if ts < window_start:
                continue

            if event_type == "signal":
                signals_24h += 1
                if last_signal_ts is None or ts > last_signal_ts:
                    last_signal_ts = ts
            elif event_type == "fill":
                fills_24h += 1
                pnl_24h += pnl
                if pnl > 0:
                    n_wins += 1
                elif pnl < 0:
                    n_losses += 1
                if last_fill_ts is None or ts > last_fill_ts:
                    last_fill_ts = ts

        h.signals_24h = signals_24h
        h.fills_24h = fills_24h
        h.pnl_24h = pnl_24h
        h.n_wins_24h = n_wins
        h.n_losses_24h = n_losses
        if last_signal_ts:
            h.last_signal_time = last_signal_ts.isoformat()
        if last_fill_ts:
            h.last_fill_time = last_fill_ts.isoformat()

        # 判断状态
        h.alerts = []
        h.status = self._evaluate_status(h, last_signal_ts, now)

    def _evaluate_status(
        self,
        h: StrategyHealth,
        last_signal_ts: Optional[datetime],
        now: datetime,
    ) -> HealthStatus:
        """评估健康状态"""
        alerts: List[str] = []

        # 1) 长时间无信号 → STALLED
        if last_signal_ts is not None:
            hours_since_signal = (now - last_signal_ts).total_seconds() / 3600
            if hours_since_signal > self.config.stalled_hours:
                alerts.append(
                    f"stalled: no signal for {hours_since_signal:.1f}h"
                )
                h.alerts = alerts
                return HealthStatus.STALLED
        elif h.total_signals == 0:
            # 从未产生信号
            alerts.append("no signal ever")
            h.alerts = alerts
            return HealthStatus.UNKNOWN

        # 2) 24h 信号数不足
        if h.signals_24h < self.config.min_signals_24h:
            alerts.append(
                f"low activity: {h.signals_24h} signals in 24h"
            )

        # 3) 有信号无成交
        if h.signals_24h > 0 and h.fills_24h == 0:
            alerts.append("no fills in 24h")
            h.alerts = alerts
            return HealthStatus.NO_FILLS

        # 4) 成交率过低
        if h.signals_24h > 0:
            fill_rate = h.fills_24h / h.signals_24h
            if fill_rate < self.config.min_fill_rate:
                alerts.append(
                    f"low fill rate: {fill_rate:.1%}"
                )

        # 5) 持续亏损
        if h.pnl_24h < self.config.max_loss_24h:
            alerts.append(
                f"losing: pnl_24h={h.pnl_24h:.2f}"
            )
            h.alerts = alerts
            return HealthStatus.LOSING

        # 6) 低活动
        if alerts:
            h.alerts = alerts
            return HealthStatus.LOW_ACTIVITY

        return HealthStatus.HEALTHY

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """全局统计"""
        all_health = self.list_health()
        from collections import Counter

        status_counts: Counter = Counter(h.status.value for h in all_health)

        return {
            "n_strategies": len(all_health),
            "by_status": dict(status_counts),
            "total_signals_24h": sum(h.signals_24h for h in all_health),
            "total_fills_24h": sum(h.fills_24h for h in all_health),
            "total_pnl_24h": sum(h.pnl_24h for h in all_health),
        }


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_monitor: Optional[StrategyHealthMonitor] = None


def get_health_monitor() -> StrategyHealthMonitor:
    """获取全局 StrategyHealthMonitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = StrategyHealthMonitor()
    return _global_monitor


def set_health_monitor(monitor: StrategyHealthMonitor) -> None:
    global _global_monitor
    _global_monitor = monitor
