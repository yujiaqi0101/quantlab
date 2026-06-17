"""
Metrics Collector — 指标收集器

核心指标：
  1. PnL (realized / unrealized / total)
  2. Latency (tick → signal → order → fill)
  3. Exposure (per symbol / total)
  4. Error Rate
  5. Order Count / Fill Count
  6. Slippage
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Deque, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.observe.metrics")


class MetricType(str, Enum):
    COUNTER = "COUNTER"        # 累计值
    GAUGE = "GAUGE"            # 瞬时值
    HISTOGRAM = "HISTOGRAM"    # 分布
    TIMER = "TIMER"            # 计时


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: int
    labels: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "labels": self.labels,
        }


class MetricsCollector:
    """
    指标收集器

    用法：
        collector = MetricsCollector()
        collector.gauge("pnl.total", 1234.56)
        collector.counter("orders.total", 1, labels={"strategy": "s1"})
        collector.timer("latency.tick_to_fill", 12.5)
        collector.snapshot()
    """

    def __init__(self, history_size: int = 10000) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=1000)
        )
        self._history: Deque[MetricPoint] = deque(maxlen=history_size)
        self._lock = threading.RLock()

    def counter(
        self,
        name: str,
        value: float = 1,
        labels: Dict = None,
    ) -> None:
        """累计指标"""
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] += value
            self._record(name, self._counters[key], labels)

    def gauge(
        self,
        name: str,
        value: float,
        labels: Dict = None,
    ) -> None:
        """瞬时指标"""
        with self._lock:
            key = self._key(name, labels)
            self._gauges[key] = value
            self._record(name, value, labels)

    def timer(
        self,
        name: str,
        value_ms: float,
        labels: Dict = None,
    ) -> None:
        """计时指标"""
        with self._lock:
            self._histograms[self._key(name, labels)].append(value_ms)
            self._record(name, value_ms, labels)

    def histogram(
        self,
        name: str,
        value: float,
        labels: Dict = None,
    ) -> None:
        """分布指标"""
        with self._lock:
            self._histograms[self._key(name, labels)].append(value)
            self._record(name, value, labels)

    def _record(self, name: str, value: float, labels: Dict = None) -> None:
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=int(time.time() * 1000),
            labels=labels or {},
        )
        self._history.append(point)

    def _key(self, name: str, labels: Dict = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_counter(self, name: str, labels: Dict = None) -> float:
        return self._counters.get(self._key(name, labels), 0.0)

    def get_gauge(self, name: str, labels: Dict = None) -> float:
        return self._gauges.get(self._key(name, labels), 0.0)

    def get_histogram_stats(
        self,
        name: str,
        labels: Dict = None,
    ) -> Dict:
        values = list(self._histograms.get(self._key(name, labels), []))
        if not values:
            return {"count": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "mean": sum(values) / n,
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
            "max": sorted_vals[-1],
        }

    def snapshot(self) -> Dict:
        """获取所有指标快照"""
        with self._lock:
            counters = {k: v for k, v in self._counters.items()}
            gauges = {k: v for k, v in self._gauges.items()}
            histograms = {
                k: self._compute_stats(list(v))
                for k, v in self._histograms.items()
            }

        return {
            "timestamp": int(time.time() * 1000),
            "counters": counters,
            "gauges": gauges,
            "histograms": histograms,
        }

    def _compute_stats(self, values: List[float]) -> Dict:
        if not values:
            return {"count": 0, "mean": 0, "p50": 0, "p95": 0, "max": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "mean": sum(values) / n,
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)] if n > 1 else sorted_vals[0],
            "max": sorted_vals[-1],
        }

    def get_history(
        self,
        name: Optional[str] = None,
        limit: int = 100,
    ) -> List[MetricPoint]:
        points = list(self._history)
        if name:
            points = [p for p in points if p.name == name]
        return points[-limit:]
