"""
Execution Analytics — 执行分析

统计：
  signal_time    信号产生时间
  order_time     订单提交时间
  fill_time      成交时间

计算：
  Signal Latency   信号 → 订单（策略决策耗时）
  Order Latency    订单 → 成交（broker 延迟）
  Fill Latency     信号 → 成交（端到端延迟）

例如：
  信号产生  10:00:00
  订单提交  10:00:02   → Signal Latency = 2s
  成交      10:00:05   → Order Latency = 3s
                         Fill Latency  = 5s

用法：
    from quantlab.observe.execution_analytics import ExecutionAnalytics

    analytics = ExecutionAnalytics()

    # 记录一笔交易的时间戳
    analytics.record(
        trace_id="t001",
        signal_time="2024-01-15T10:00:00",
        order_time="2024-01-15T10:00:02",
        fill_time="2024-01-15T10:00:05",
    )

    report = analytics.report()
    print(report.to_dict())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("quantlab.observe.execution_analytics")


# ------------------------------------------------------------------
# LatencyRecord
# ------------------------------------------------------------------

@dataclass
class LatencyRecord:
    """单笔交易的延迟记录"""
    trace_id: str
    signal_time: Optional[str] = None
    order_time: Optional[str] = None
    fill_time: Optional[str] = None
    # 计算后的延迟（秒）
    signal_latency: Optional[float] = None    # signal → order
    order_latency: Optional[float] = None     # order → fill
    fill_latency: Optional[float] = None      # signal → fill
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "signal_time": self.signal_time,
            "order_time": self.order_time,
            "fill_time": self.fill_time,
            "signal_latency": self.signal_latency,
            "order_latency": self.order_latency,
            "fill_latency": self.fill_latency,
            "metadata": self.metadata,
        }


# ------------------------------------------------------------------
# ExecutionAnalyticsReport
# ------------------------------------------------------------------

@dataclass
class ExecutionAnalyticsReport:
    """执行分析报告"""
    n_records: int = 0

    # Signal Latency
    signal_latency_mean: float = 0.0
    signal_latency_median: float = 0.0
    signal_latency_p95: float = 0.0
    signal_latency_max: float = 0.0
    signal_latency_min: float = 0.0

    # Order Latency
    order_latency_mean: float = 0.0
    order_latency_median: float = 0.0
    order_latency_p95: float = 0.0
    order_latency_max: float = 0.0
    order_latency_min: float = 0.0

    # Fill Latency (end-to-end)
    fill_latency_mean: float = 0.0
    fill_latency_median: float = 0.0
    fill_latency_p95: float = 0.0
    fill_latency_max: float = 0.0
    fill_latency_min: float = 0.0

    # 计数
    n_complete: int = 0        # signal+order+fill 都有
    n_signal_only: int = 0     # 只有 signal，没下单
    n_order_no_fill: int = 0   # 下了单没成交

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_records": self.n_records,
            "signal_latency": {
                "mean": self.signal_latency_mean,
                "median": self.signal_latency_median,
                "p95": self.signal_latency_p95,
                "max": self.signal_latency_max,
                "min": self.signal_latency_min,
            },
            "order_latency": {
                "mean": self.order_latency_mean,
                "median": self.order_latency_median,
                "p95": self.order_latency_p95,
                "max": self.order_latency_max,
                "min": self.order_latency_min,
            },
            "fill_latency": {
                "mean": self.fill_latency_mean,
                "median": self.fill_latency_median,
                "p95": self.fill_latency_p95,
                "max": self.fill_latency_max,
                "min": self.fill_latency_min,
            },
            "n_complete": self.n_complete,
            "n_signal_only": self.n_signal_only,
            "n_order_no_fill": self.n_order_no_fill,
        }


# ------------------------------------------------------------------
# ExecutionAnalytics
# ------------------------------------------------------------------

class ExecutionAnalytics:
    """
    执行分析器

    用法：
        analytics = ExecutionAnalytics()
        analytics.record("t001", signal_time=..., order_time=..., fill_time=...)
        report = analytics.report()
    """

    def __init__(self) -> None:
        self._records: Dict[str, LatencyRecord] = {}

    def record(
        self,
        trace_id: str,
        signal_time: Optional[str] = None,
        order_time: Optional[str] = None,
        fill_time: Optional[str] = None,
        **metadata,
    ) -> LatencyRecord:
        """
        记录一笔交易的时间戳

        可以分多次调用，按 trace_id 累积：
            analytics.record("t001", signal_time="10:00:00")
            analytics.record("t001", order_time="10:00:02")
            analytics.record("t001", fill_time="10:00:05")
        """
        rec = self._records.get(trace_id)
        if rec is None:
            rec = LatencyRecord(trace_id=trace_id)
            self._records[trace_id] = rec

        if signal_time is not None:
            rec.signal_time = signal_time
        if order_time is not None:
            rec.order_time = order_time
        if fill_time is not None:
            rec.fill_time = fill_time
        if metadata:
            rec.metadata.update(metadata)

        # 重新计算延迟
        self._compute_latencies(rec)
        return rec

    def _compute_latencies(self, rec: LatencyRecord) -> None:
        """计算延迟"""
        rec.signal_latency = self._diff_seconds(rec.signal_time, rec.order_time)
        rec.order_latency = self._diff_seconds(rec.order_time, rec.fill_time)
        rec.fill_latency = self._diff_seconds(rec.signal_time, rec.fill_time)

    @staticmethod
    def _diff_seconds(t1: Optional[str], t2: Optional[str]) -> Optional[float]:
        """计算两个时间戳差（秒）"""
        if t1 is None or t2 is None:
            return None
        try:
            d1 = ExecutionAnalytics._parse_time(t1)
            d2 = ExecutionAnalytics._parse_time(t2)
            return (d2 - d1).total_seconds()
        except Exception:
            return None

    @staticmethod
    def _parse_time(t: str) -> datetime:
        """解析时间字符串"""
        # 尝试 ISO 格式
        try:
            return datetime.fromisoformat(t)
        except ValueError:
            pass
        # 尝试常见格式
        for fmt in [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%H:%M:%S",
            "%H:%M:%S.%f",
        ]:
            try:
                return datetime.strptime(t, fmt)
            except ValueError:
                continue
        raise ValueError(f"cannot parse time: {t}")

    # ------------------------------------------------------------------
    # 报告
    # ------------------------------------------------------------------

    def report(self) -> ExecutionAnalyticsReport:
        """生成执行分析报告"""
        r = ExecutionAnalyticsReport()
        r.n_records = len(self._records)

        if r.n_records == 0:
            return r

        signal_lats: List[float] = []
        order_lats: List[float] = []
        fill_lats: List[float] = []

        for rec in self._records.values():
            # 计数
            has_signal = rec.signal_time is not None
            has_order = rec.order_time is not None
            has_fill = rec.fill_time is not None

            if has_signal and has_order and has_fill:
                r.n_complete += 1
            elif has_signal and not has_order:
                r.n_signal_only += 1
            elif has_order and not has_fill:
                r.n_order_no_fill += 1

            if rec.signal_latency is not None:
                signal_lats.append(rec.signal_latency)
            if rec.order_latency is not None:
                order_lats.append(rec.order_latency)
            if rec.fill_latency is not None:
                fill_lats.append(rec.fill_latency)

        # 统计
        r.signal_latency_mean = float(np.mean(signal_lats)) if signal_lats else 0.0
        r.signal_latency_median = float(np.median(signal_lats)) if signal_lats else 0.0
        r.signal_latency_p95 = float(np.percentile(signal_lats, 95)) if signal_lats else 0.0
        r.signal_latency_max = float(np.max(signal_lats)) if signal_lats else 0.0
        r.signal_latency_min = float(np.min(signal_lats)) if signal_lats else 0.0

        r.order_latency_mean = float(np.mean(order_lats)) if order_lats else 0.0
        r.order_latency_median = float(np.median(order_lats)) if order_lats else 0.0
        r.order_latency_p95 = float(np.percentile(order_lats, 95)) if order_lats else 0.0
        r.order_latency_max = float(np.max(order_lats)) if order_lats else 0.0
        r.order_latency_min = float(np.min(order_lats)) if order_lats else 0.0

        r.fill_latency_mean = float(np.mean(fill_lats)) if fill_lats else 0.0
        r.fill_latency_median = float(np.median(fill_lats)) if fill_lats else 0.0
        r.fill_latency_p95 = float(np.percentile(fill_lats, 95)) if fill_lats else 0.0
        r.fill_latency_max = float(np.max(fill_lats)) if fill_lats else 0.0
        r.fill_latency_min = float(np.min(fill_lats)) if fill_lats else 0.0

        return r

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get(self, trace_id: str) -> Optional[LatencyRecord]:
        return self._records.get(trace_id)

    def list_records(self, limit: int = 100) -> List[LatencyRecord]:
        return list(self._records.values())[-limit:]

    def clear(self) -> None:
        self._records.clear()
