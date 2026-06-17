"""
Market Data Service — 统一行情服务

整个交易系统的地基。Backtest / Paper / Live 三模式全部调用同一套接口。

目录（按用户规划）：
  execution/market/
    ├── service.py      本文件：统一 Service
    ├── cache.py        行情缓存
    ├── websocket.py    WS 推送抽象
    ├── snapshot.py     快照
    └── provider.py     数据源适配

统一接口：
    class MarketDataService:
        get_bar(symbol, interval)            最新一根 bar
        get_bars(symbol, interval, limit)    历史 N 根 bar
        subscribe_ticks(symbols, callback)   订阅 tick
        subscribe_bars(symbols, callback)    订阅 bar
        snapshot(symbol)                     最新快照

数据源：
  - Backtest  → 从 DataFrame 读取
  - Paper     → 从 Replay / 模拟生成
  - Live      → Binance WebSocket / REST

用法：
    from quantlab.execution.market import MarketDataService, BarSource

    # Backtest 模式
    service = MarketDataService(mode="backtest")
    service.load_bars("BTCUSDT", "1m", df)
    bar = service.get_bar("BTCUSDT", "1m")

    # Live 模式
    service = MarketDataService(mode="live", provider=binance_provider)
    service.subscribe_ticks(["BTCUSDT"], on_tick)
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

import pandas as pd

from ...core.tick import Tick

logger = logging.getLogger("quantlab.execution.market")


# ------------------------------------------------------------------
# Bar 数据结构
# ------------------------------------------------------------------

@dataclass
class Bar:
    """一根 K 线"""
    symbol: str
    interval: str            # "1m" / "5m" / "1h" / "1d"
    timestamp: Any           # 开盘时间
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    closed: bool = True      # 是否收盘

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "timestamp": str(self.timestamp),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "closed": self.closed,
        }


@dataclass
class Snapshot:
    """最新快照"""
    symbol: str
    last_price: float
    bid: float = 0.0
    ask: float = 0.0
    volume_24h: float = 0.0
    timestamp: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "last_price": self.last_price,
            "bid": self.bid,
            "ask": self.ask,
            "volume_24h": self.volume_24h,
            "timestamp": str(self.timestamp) if self.timestamp else None,
        }


# ------------------------------------------------------------------
# Provider 抽象
# ------------------------------------------------------------------

class MarketDataProvider:
    """
    数据源抽象基类

    子类：
      - BacktestProvider   从 DataFrame 读
      - BinanceProvider    从 Binance REST/WS 读
      - ReplayProvider     从历史数据回放
    """

    name: str = "BASE"

    def get_bars(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        raise NotImplementedError

    def subscribe_ticks(
        self,
        symbols: List[str],
        callback: Callable[[Tick], None],
    ) -> None:
        raise NotImplementedError

    def subscribe_bars(
        self,
        symbols: List[str],
        interval: str,
        callback: Callable[[Bar], None],
    ) -> None:
        raise NotImplementedError

    def snapshot(self, symbol: str) -> Optional[Snapshot]:
        raise NotImplementedError


# ------------------------------------------------------------------
# Backtest Provider（从 DataFrame 读）
# ------------------------------------------------------------------

class BacktestProvider(MarketDataProvider):
    """
    从预加载的 DataFrame 读行情

    df 要求列：timestamp, open, high, low, close, volume
    """

    name = "BACKTEST"

    def __init__(self) -> None:
        # symbol+interval → DataFrame
        self._bars: Dict[str, pd.DataFrame] = {}
        # symbol → 最新价
        self._last_prices: Dict[str, float] = {}

    def load_bars(
        self,
        symbol: str,
        interval: str,
        df: pd.DataFrame,
    ) -> None:
        """加载历史 bar 数据"""
        key = f"{symbol}_{interval}"
        df = df.copy()
        df.reset_index(drop=True, inplace=True)
        self._bars[key] = df
        if len(df) > 0:
            self._last_prices[symbol] = float(df.iloc[-1]["close"])
        logger.info(
            f"BacktestProvider: loaded {len(df)} bars for {key}"
        )

    def get_bars(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> pd.DataFrame:
        key = f"{symbol}_{interval}"
        df = self._bars.get(key)
        if df is None:
            return pd.DataFrame()
        return df.tail(limit)

    def update_price(self, symbol: str, price: float) -> None:
        """更新最新价（回测循环里调用）"""
        self._last_prices[symbol] = price

    def snapshot(self, symbol: str) -> Optional[Snapshot]:
        price = self._last_prices.get(symbol)
        if price is None:
            return None
        return Snapshot(
            symbol=symbol,
            last_price=price,
            timestamp=pd.Timestamp.now(),
        )

    def subscribe_ticks(
        self,
        symbols: List[str],
        callback: Callable[[Tick], None],
    ) -> None:
        # Backtest 不支持实时订阅
        logger.warning("BacktestProvider: subscribe_ticks not supported")

    def subscribe_bars(
        self,
        symbols: List[str],
        interval: str,
        callback: Callable[[Bar], None],
    ) -> None:
        logger.warning("BacktestProvider: subscribe_bars not supported")


# ------------------------------------------------------------------
# MarketDataService
# ------------------------------------------------------------------

class MarketDataService:
    """
    统一行情服务

    三模式：
      - backtest : 从预加载数据读
      - paper    : 从 Replay 或模拟生成
      - live     : 从交易所 WS/REST 读

    所有上层（Backtest / Paper / Live）调用同一接口。
    """

    def __init__(
        self,
        mode: str = "backtest",
        provider: Optional[MarketDataProvider] = None,
        cache_size: int = 1000,
    ) -> None:
        """
        参数：
          mode        backtest / paper / live
          provider    数据源（不传则按 mode 自动创建）
          cache_size  每个品种缓存的 bar 数量
        """
        self.mode = mode
        self.provider = provider or self._default_provider(mode)
        self.cache_size = cache_size

        # bar 缓存：symbol+interval → deque[Bar]
        self._bar_cache: Dict[str, Deque[Bar]] = defaultdict(
            lambda: deque(maxlen=cache_size)
        )
        # tick 缓存：symbol → 最新 Tick
        self._last_ticks: Dict[str, Tick] = {}
        # 订阅回调
        self._tick_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._bar_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        # 锁
        self._lock = threading.RLock()

    def _default_provider(self, mode: str) -> MarketDataProvider:
        if mode == "backtest":
            return BacktestProvider()
        # paper / live 需要外部传入 provider
        return BacktestProvider()

    # ------------------------------------------------------------------
    # Bar 接口
    # ------------------------------------------------------------------

    def get_bar(
        self,
        symbol: str,
        interval: str,
    ) -> Optional[Bar]:
        """获取最新一根 bar"""
        # 先看缓存
        key = f"{symbol}_{interval}"
        with self._lock:
            cache = self._bar_cache.get(key)
            if cache:
                return cache[-1]

        # 从 provider 拿
        df = self.provider.get_bars(symbol, interval, limit=1)
        if df is None or len(df) == 0:
            return None
        return self._row_to_bar(df.iloc[-1], symbol, interval)

    def get_bars(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> List[Bar]:
        """获取历史 N 根 bar"""
        # 先看缓存
        key = f"{symbol}_{interval}"
        with self._lock:
            cache = self._bar_cache.get(key)
            if cache and len(cache) >= limit:
                return list(cache)[-limit:]

        # 从 provider 拿
        df = self.provider.get_bars(symbol, interval, limit=limit)
        if df is None or len(df) == 0:
            return []
        return [
            self._row_to_bar(row, symbol, interval)
            for _, row in df.iterrows()
        ]

    def push_bar(self, bar: Bar) -> None:
        """
        推送一根 bar（内部或外部调用）

        - 更新缓存
        - 触发订阅回调
        """
        key = f"{bar.symbol}_{bar.interval}"
        with self._lock:
            self._bar_cache[key].append(bar)

        # 触发回调
        callbacks = self._bar_callbacks.get(key, [])
        for cb in callbacks:
            try:
                cb(bar)
            except Exception as e:
                logger.error(f"bar callback error: {e}")

    # ------------------------------------------------------------------
    # Tick 接口
    # ------------------------------------------------------------------

    def subscribe_ticks(
        self,
        symbols: List[str],
        callback: Callable[[Tick], None],
    ) -> None:
        """订阅 tick"""
        for sym in symbols:
            self._tick_callbacks[sym].append(callback)

        # 委托给 provider
        try:
            self.provider.subscribe_ticks(symbols, self._on_tick_internal)
        except NotImplementedError:
            logger.warning(
                f"MarketDataService: provider {self.provider.name} "
                f"does not support subscribe_ticks"
            )

    def subscribe_bars(
        self,
        symbols: List[str],
        interval: str,
        callback: Callable[[Bar], None],
    ) -> None:
        """订阅 bar"""
        for sym in symbols:
            key = f"{sym}_{interval}"
            self._bar_callbacks[key].append(callback)

        try:
            self.provider.subscribe_bars(symbols, interval, self._on_bar_internal)
        except NotImplementedError:
            logger.warning(
                f"MarketDataService: provider {self.provider.name} "
                f"does not support subscribe_bars"
            )

    def push_tick(self, tick: Tick) -> None:
        """
        推送一个 tick

        - 更新最新价缓存
        - 触发订阅回调
        """
        with self._lock:
            self._last_ticks[tick.symbol] = tick

        callbacks = self._tick_callbacks.get(tick.symbol, [])
        for cb in callbacks:
            try:
                cb(tick)
            except Exception as e:
                logger.error(f"tick callback error: {e}")

    def _on_tick_internal(self, tick: Tick) -> None:
        """provider 回调入口"""
        self.push_tick(tick)

    def _on_bar_internal(self, bar: Bar) -> None:
        """provider 回调入口"""
        self.push_bar(bar)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self, symbol: str) -> Optional[Snapshot]:
        """获取最新快照"""
        # 优先用 tick 缓存
        tick = self._last_ticks.get(symbol)
        if tick is not None:
            return Snapshot(
                symbol=symbol,
                last_price=tick.price,
                timestamp=tick.timestamp,
            )
        # 退回 provider
        return self.provider.snapshot(symbol)

    def last_price(self, symbol: str) -> Optional[float]:
        """便捷方法：最新价"""
        snap = self.snapshot(symbol)
        return snap.last_price if snap else None

    # ------------------------------------------------------------------
    # Backtest 专用：加载历史数据
    # ------------------------------------------------------------------

    def load_bars(
        self,
        symbol: str,
        interval: str,
        df: pd.DataFrame,
    ) -> None:
        """加载历史 bar 数据（Backtest 模式）"""
        if isinstance(self.provider, BacktestProvider):
            self.provider.load_bars(symbol, interval, df)
            # 同时填缓存
            for _, row in df.iterrows():
                bar = self._row_to_bar(row, symbol, interval)
                self.push_bar(bar)
        else:
            logger.warning(
                "MarketDataService.load_bars only for BacktestProvider"
            )

    def update_price(self, symbol: str, price: float) -> None:
        """更新最新价（回测循环里调用）"""
        if isinstance(self.provider, BacktestProvider):
            self.provider.update_price(symbol, price)
        # 同步更新 tick 缓存
        self.push_tick(Tick(
            timestamp=pd.Timestamp.now(),
            symbol=symbol,
            price=price,
        ))

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_bar(row: Any, symbol: str, interval: str) -> Bar:
        """DataFrame 行 → Bar"""
        ts = row.get("timestamp", row.name if hasattr(row, "name") else None)
        return Bar(
            symbol=symbol,
            interval=interval,
            timestamp=ts,
            open=float(row.get("open", 0)),
            high=float(row.get("high", 0)),
            low=float(row.get("low", 0)),
            close=float(row.get("close", 0)),
            volume=float(row.get("volume", 0)),
            closed=True,
        )

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        with self._lock:
            return {
                "mode": self.mode,
                "provider": self.provider.name,
                "n_cached_bars": sum(len(v) for v in self._bar_cache.values()),
                "n_last_ticks": len(self._last_ticks),
                "n_tick_subscriptions": sum(
                    len(v) for v in self._tick_callbacks.values()
                ),
                "n_bar_subscriptions": sum(
                    len(v) for v in self._bar_callbacks.values()
                ),
            }


# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_global_service: Optional[MarketDataService] = None


def get_market_data_service() -> MarketDataService:
    """获取全局 MarketDataService（默认 backtest 模式）"""
    global _global_service
    if _global_service is None:
        _global_service = MarketDataService(mode="backtest")
    return _global_service


def set_market_data_service(service: MarketDataService) -> None:
    """设置全局 MarketDataService"""
    global _global_service
    _global_service = service
