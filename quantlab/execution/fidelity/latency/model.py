"""
Latency Model — 延迟模型

模拟真实交易延迟：
  1. signal_delay_ms（信号产生到下单）
  2. order_route_delay（订单路由）
  3. exchange_delay（交易所处理）
  4. fill_notify_delay（成交回报）

最终效果：signal → order = 真实延迟
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("quantlab.execution.fidelity.latency")


@dataclass
class LatencyProfile:
    """延迟画像"""
    signal_delay_ms: float = 50.0       # 信号处理延迟
    order_route_delay_ms: float = 20.0  # 订单路由延迟
    exchange_delay_ms: float = 30.0     # 交易所处理延迟
    fill_notify_delay_ms: float = 40.0  # 成交回报延迟
    jitter_ms: float = 10.0             # 随机抖动

    @property
    def total_one_way_ms(self) -> float:
        """单程总延迟（信号→交易所）"""
        return self.signal_delay_ms + self.order_route_delay_ms + self.exchange_delay_ms

    @property
    def total_round_trip_ms(self) -> float:
        """往返总延迟"""
        return self.total_one_way_ms + self.fill_notify_delay_ms

    def to_dict(self) -> Dict:
        return {
            "signal_delay_ms": self.signal_delay_ms,
            "order_route_delay_ms": self.order_route_delay_ms,
            "exchange_delay_ms": self.exchange_delay_ms,
            "fill_notify_delay_ms": self.fill_notify_delay_ms,
            "jitter_ms": self.jitter_ms,
            "total_one_way_ms": self.total_one_way_ms,
            "total_round_trip_ms": self.total_round_trip_ms,
        }


@dataclass
class LatencyMeasurement:
    """延迟测量"""
    signal_ts: int = 0
    order_submit_ts: int = 0
    exchange_recv_ts: int = 0
    fill_ts: int = 0
    local_recv_ts: int = 0

    @property
    def signal_to_order_ms(self) -> float:
        if self.signal_ts and self.order_submit_ts:
            return self.order_submit_ts - self.signal_ts
        return 0

    @property
    def order_to_exchange_ms(self) -> float:
        if self.order_submit_ts and self.exchange_recv_ts:
            return self.exchange_recv_ts - self.order_submit_ts
        return 0

    @property
    def exchange_to_fill_ms(self) -> float:
        if self.exchange_recv_ts and self.fill_ts:
            return self.fill_ts - self.exchange_recv_ts
        return 0

    @property
    def fill_to_local_ms(self) -> float:
        if self.fill_ts and self.local_recv_ts:
            return self.local_recv_ts - self.fill_ts
        return 0

    @property
    def total_latency_ms(self) -> float:
        if self.signal_ts and self.local_recv_ts:
            return self.local_recv_ts - self.signal_ts
        return 0

    def to_dict(self) -> Dict:
        return {
            "signal_to_order_ms": self.signal_to_order_ms,
            "order_to_exchange_ms": self.order_to_exchange_ms,
            "exchange_to_fill_ms": self.exchange_to_fill_ms,
            "fill_to_local_ms": self.fill_to_local_ms,
            "total_latency_ms": self.total_latency_ms,
        }


class LatencySimulator:
    """
    延迟模拟器

    用法：
        sim = LatencySimulator(LatencyProfile(signal_delay_ms=50))
        # 模拟信号到成交的完整延迟
        measurement = sim.simulate(signal_ts=now)
        print(f"Total latency: {measurement.total_latency_ms}ms")
    """

    def __init__(self, profile: LatencyProfile = None) -> None:
        self.profile = profile or LatencyProfile()
        self._measurements: list = []

    def simulate(
        self,
        signal_ts: int = 0,
        apply_jitter: bool = True,
    ) -> LatencyMeasurement:
        """模拟完整延迟链"""
        if signal_ts == 0:
            signal_ts = int(time.time() * 1000)

        def jitter(base: float) -> float:
            if apply_jitter:
                return base + random.uniform(-self.profile.jitter_ms, self.profile.jitter_ms)
            return base

        order_submit_ts = signal_ts + jitter(self.profile.signal_delay_ms)
        exchange_recv_ts = order_submit_ts + jitter(self.profile.order_route_delay_ms)
        fill_ts = exchange_recv_ts + jitter(self.profile.exchange_delay_ms)
        local_recv_ts = fill_ts + jitter(self.profile.fill_notify_delay_ms)

        m = LatencyMeasurement(
            signal_ts=signal_ts,
            order_submit_ts=int(order_submit_ts),
            exchange_recv_ts=int(exchange_recv_ts),
            fill_ts=int(fill_ts),
            local_recv_ts=int(local_recv_ts),
        )
        self._measurements.append(m.to_dict())
        return m

    def expected_fill_price(
        self,
        signal_price: float,
        volatility: float,
        direction: str = "BUY",
    ) -> float:
        """
        基于延迟估算预期成交价

        延迟期间价格可能漂移
        """
        # 延迟期间价格变动（简化为布朗运动）
        delay_seconds = self.profile.total_one_way_ms / 1000
        price_drift = signal_price * volatility * (delay_seconds ** 0.5) * random.gauss(0, 1)

        if direction == "BUY":
            return signal_price + price_drift
        else:
            return signal_price - price_drift

    def get_stats(self) -> Dict:
        if not self._measurements:
            return {"count": 0}

        total_latencies = [m["total_latency_ms"] for m in self._measurements]
        return {
            "count": len(self._measurements),
            "avg_total_ms": sum(total_latencies) / len(total_latencies),
            "max_total_ms": max(total_latencies),
            "min_total_ms": min(total_latencies),
            "profile": self.profile.to_dict(),
        }
