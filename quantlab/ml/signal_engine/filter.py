"""
模块 4: Signal Filter

过滤不可交易信号：流动性/停牌/涨跌停/上市时间/黑名单。

需要行情数据的过滤器接受 market_data_provider 回调（避免直接耦合数据源）。
过滤掉的信号保留在 SignalSet.metadata["filtered_out"] 里以便溯源。
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .signal import Signal, SignalDirection, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.filter")


class SignalFilter(ABC):
    """信号过滤器抽象基类"""

    name: str = "base"

    @abstractmethod
    def filter(self, signal_set: SignalSet) -> SignalSet:
        """过滤信号集，返回新的 SignalSet"""
        ...

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name}


class BlacklistFilter(SignalFilter):
    """黑名单过滤"""

    name = "blacklist"

    def __init__(self, blacklist: Optional[Set[str]] = None) -> None:
        self.blacklist: Set[str] = set(blacklist or [])

    def filter(self, signal_set: SignalSet) -> SignalSet:
        kept: List[Signal] = []
        filtered_out: List[Dict[str, Any]] = []
        for s in signal_set.signals:
            if s.symbol in self.blacklist:
                filtered_out.append({"signal_id": s.signal_id, "symbol": s.symbol, "reason": "blacklist"})
            else:
                kept.append(s)
        new_set = SignalSet(
            signals=kept,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata.setdefault("filtered_out", []).extend(filtered_out)
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "blacklist": list(self.blacklist)}


class LiquidityFilter(SignalFilter):
    """流动性过滤 — 最小成交额/成交量"""

    name = "liquidity"

    def __init__(
        self,
        min_volume: float = 0.0,
        min_amount: float = 0.0,
        market_data_provider: Optional[Callable] = None,
    ) -> None:
        self.min_volume = float(min_volume)
        self.min_amount = float(min_amount)
        self.market_data_provider = market_data_provider

    def filter(self, signal_set: SignalSet) -> SignalSet:
        if self.market_data_provider is None:
            # 无数据源，透传
            return signal_set
        kept: List[Signal] = []
        filtered_out: List[Dict[str, Any]] = []
        for s in signal_set.signals:
            try:
                bar = self.market_data_provider(s.symbol, s.datetime)
                vol = float(bar.get("volume", 0)) if bar else 0.0
                amt = float(bar.get("amount", 0)) if bar else 0.0
                if vol < self.min_volume or amt < self.min_amount:
                    filtered_out.append({
                        "signal_id": s.signal_id, "symbol": s.symbol,
                        "reason": "liquidity", "volume": vol, "amount": amt,
                    })
                else:
                    s.metadata["filter_volume"] = vol
                    s.metadata["filter_amount"] = amt
                    kept.append(s)
            except Exception as e:
                logger.warning(f"LiquidityFilter {s.symbol} failed: {e}")
                kept.append(s)  # 出错保留
        new_set = SignalSet(
            signals=kept,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata.setdefault("filtered_out", []).extend(filtered_out)
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.name,
            "min_volume": self.min_volume,
            "min_amount": self.min_amount,
        }


class SuspensionFilter(SignalFilter):
    """停牌过滤 — 需行情数据"""

    name = "suspension"

    def __init__(self, market_data_provider: Optional[Callable] = None) -> None:
        self.market_data_provider = market_data_provider

    def filter(self, signal_set: SignalSet) -> SignalSet:
        if self.market_data_provider is None:
            return signal_set
        kept: List[Signal] = []
        filtered_out: List[Dict[str, Any]] = []
        for s in signal_set.signals:
            try:
                bar = self.market_data_provider(s.symbol, s.datetime)
                if bar is None or bar.get("suspended", False):
                    filtered_out.append({"signal_id": s.signal_id, "symbol": s.symbol, "reason": "suspension"})
                else:
                    kept.append(s)
            except Exception:
                kept.append(s)
        new_set = SignalSet(
            signals=kept,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata.setdefault("filtered_out", []).extend(filtered_out)
        return new_set


class PriceLimitFilter(SignalFilter):
    """涨跌停过滤 — 需行情数据"""

    name = "price_limit"

    def __init__(self, market_data_provider: Optional[Callable] = None) -> None:
        self.market_data_provider = market_data_provider

    def filter(self, signal_set: SignalSet) -> SignalSet:
        if self.market_data_provider is None:
            return signal_set
        kept: List[Signal] = []
        filtered_out: List[Dict[str, Any]] = []
        for s in signal_set.signals:
            try:
                bar = self.market_data_provider(s.symbol, s.datetime)
                if bar and bar.get("limit_hit", False):
                    filtered_out.append({"signal_id": s.signal_id, "symbol": s.symbol, "reason": "price_limit"})
                else:
                    kept.append(s)
            except Exception:
                kept.append(s)
        new_set = SignalSet(
            signals=kept,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata.setdefault("filtered_out", []).extend(filtered_out)
        return new_set


class ListingAgeFilter(SignalFilter):
    """上市时间过滤 — 新股过滤"""

    name = "listing_age"

    def __init__(
        self,
        min_listing_days: int = 60,
        listing_date_provider: Optional[Callable] = None,
    ) -> None:
        self.min_listing_days = int(min_listing_days)
        self.listing_date_provider = listing_date_provider

    def filter(self, signal_set: SignalSet) -> SignalSet:
        if self.listing_date_provider is None:
            return signal_set
        kept: List[Signal] = []
        filtered_out: List[Dict[str, Any]] = []
        for s in signal_set.signals:
            try:
                list_date_str = self.listing_date_provider(s.symbol)
                if list_date_str:
                    list_date = datetime.fromisoformat(list_date_str)
                    sig_date = datetime.fromisoformat(s.datetime)
                    age_days = (sig_date - list_date).days
                    if age_days < self.min_listing_days:
                        filtered_out.append({
                            "signal_id": s.signal_id, "symbol": s.symbol,
                            "reason": "listing_age", "age_days": age_days,
                        })
                        continue
                kept.append(s)
            except Exception:
                kept.append(s)
        new_set = SignalSet(
            signals=kept,
            pipeline_config=signal_set.pipeline_config,
            metadata=dict(signal_set.metadata),
        )
        new_set.metadata.setdefault("filtered_out", []).extend(filtered_out)
        return new_set

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "min_listing_days": self.min_listing_days}


class CompositeFilter(SignalFilter):
    """组合过滤器 — 顺序应用多个 filter"""

    name = "composite"

    def __init__(self, filters: Optional[List[SignalFilter]] = None) -> None:
        self.filters: List[SignalFilter] = list(filters or [])

    def add(self, f: SignalFilter) -> "CompositeFilter":
        self.filters.append(f)
        return self

    def filter(self, signal_set: SignalSet) -> SignalSet:
        current = signal_set
        for f in self.filters:
            current = f.filter(current)
        return current

    def to_dict(self) -> Dict[str, Any]:
        return {"method": self.name, "filters": [f.to_dict() for f in self.filters]}


# ---- 工厂 ----

def get_filter(method: str, **params) -> SignalFilter:
    """获取过滤器实例"""
    method = method.lower()
    if method == "blacklist":
        return BlacklistFilter(set(params.get("blacklist", [])))
    if method == "liquidity":
        return LiquidityFilter(
            min_volume=params.get("min_volume", 0.0),
            min_amount=params.get("min_amount", 0.0),
            market_data_provider=params.get("market_data_provider"),
        )
    if method == "suspension":
        return SuspensionFilter(params.get("market_data_provider"))
    if method == "price_limit":
        return PriceLimitFilter(params.get("market_data_provider"))
    if method == "listing_age":
        return ListingAgeFilter(
            min_listing_days=params.get("min_listing_days", 60),
            listing_date_provider=params.get("listing_date_provider"),
        )
    logger.warning(f"Unknown filter method: {method}, returning noop BlacklistFilter")
    return BlacklistFilter()


def build_filters(filter_configs: List[Dict[str, Any]]) -> CompositeFilter:
    """从配置列表构建组合过滤器"""
    composite = CompositeFilter()
    for cfg in filter_configs:
        method = cfg.get("method", "")
        params = {k: v for k, v in cfg.items() if k != "method"}
        composite.add(get_filter(method, **params))
    return composite
