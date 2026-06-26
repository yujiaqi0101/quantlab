"""
Cache 层单元测试

重点:
  1. MemoryCache L1 hit/miss + LRU
  2. ParquetCache L2 持久化 + 跨执行命中
  3. CacheManifest 持久化
  4. CacheInvalidator 反向失效传播 (Close -> Return/EMA 失效, ATR 不失效)
  5. CachePlanner 按 cost 分级
  6. CacheManager 端到端
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quantlab.research import ResearchFrame
from quantlab.research.builtin import (
    ATRNode,
    CloseNode,
    EMANode,
    MACDNode,
    ReturnNode,
    RSINode,
)
from quantlab.research.cache import (
    CacheEntry,
    CacheInvalidator,
    CacheKey,
    CacheManager,
    CacheManifest,
    CachePlanner,
    MemoryCache,
    ParquetCache,
    WindowCache,
)
from quantlab.research.graph import ResearchGraph


def _make_panel(n=10, symbols=("BTC", "ETH")) -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    rows = []
    for dt in dates:
        for sym in symbols:
            close = 100.0 + np.random.randn() * 5
            rows.append(
                {
                    "datetime": dt,
                    "symbol": sym,
                    "open": close - 0.5,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000.0,
                }
            )
    return pd.DataFrame(rows).set_index(["datetime", "symbol"])


def _make_frame() -> ResearchFrame:
    return ResearchFrame.from_panel(_make_panel(), name="test")


def _make_key(node_id="rsi", fp="abc123") -> CacheKey:
    return CacheKey(node_id=node_id, node_fingerprint=fp, dataset_fingerprint="ds1")


# ---------------------------------------------------------------------- #
# 1. MemoryCache
# ---------------------------------------------------------------------- #
class TestMemoryCache:
    def test_set_and_get(self):
        cache = MemoryCache(max_entries=10)
        key = _make_key()
        frame = _make_frame()
        entry = CacheEntry(key=key, data=frame)
        cache.set(entry)
        got = cache.get(key)
        assert got is not None
        assert got.data is frame

    def test_miss(self):
        cache = MemoryCache()
        got = cache.get(_make_key("nope"))
        assert got is None
        assert cache.misses == 1

    def test_lru_eviction(self):
        cache = MemoryCache(max_entries=2)
        k1 = _make_key("n1", "f1")
        k2 = _make_key("n2", "f2")
        k3 = _make_key("n3", "f3")
        for k in (k1, k2, k3):
            cache.set(CacheEntry(key=k, data=_make_frame()))
        # k1 应被淘汰
        assert cache.has(k1) is False
        assert cache.has(k2) is True
        assert cache.has(k3) is True

    def test_invalidate(self):
        cache = MemoryCache()
        key = _make_key()
        cache.set(CacheEntry(key=key, data=_make_frame()))
        assert cache.invalidate(key) is True
        assert cache.has(key) is False

    def test_ttl_expiry(self):
        import time
        cache = MemoryCache()
        key = _make_key()
        cache.set(CacheEntry(key=key, data=_make_frame(), ttl=0.1))
        time.sleep(0.15)
        assert cache.get(key) is None

    def test_stats(self):
        cache = MemoryCache()
        cache.set(CacheEntry(key=_make_key("n1", "f1"), data=_make_frame()))
        cache.get(_make_key("different", "different"))  # miss
        s = cache.stats()
        assert s["level"] == "L1_memory"
        assert s["entries"] == 1
        assert s["misses"] == 1


# ---------------------------------------------------------------------- #
# 2. WindowCache
# ---------------------------------------------------------------------- #
class TestWindowCache:
    def test_append_and_get(self):
        wc = WindowCache(window_size=3)
        key = _make_key()
        wc.append_state(key, "s1")
        wc.append_state(key, "s2")
        assert wc.get_state(key) == "s2"
        assert len(wc.get_history(key)) == 2

    def test_window_eviction(self):
        wc = WindowCache(window_size=2)
        key = _make_key()
        for s in ("a", "b", "c"):
            wc.append_state(key, s)
        # 只保留最近 2 个
        assert wc.get_history(key) == ["b", "c"]


# ---------------------------------------------------------------------- #
# 3. ParquetCache
# ---------------------------------------------------------------------- #
class TestParquetCache:
    def test_persistence(self, tmp_path):
        cache = ParquetCache(cache_dir=str(tmp_path))
        key = _make_key()
        frame = _make_frame()
        cache.set(CacheEntry(key=key, data=frame))
        # 重新读取
        got = cache.get(key)
        assert got is not None
        assert got.data.name == frame.name
        assert got.data.data.shape == frame.data.shape

    def test_miss(self, tmp_path):
        cache = ParquetCache(cache_dir=str(tmp_path))
        assert cache.get(_make_key("nope")) is None
        assert cache.misses == 1

    def test_invalidate(self, tmp_path):
        cache = ParquetCache(cache_dir=str(tmp_path))
        key = _make_key()
        cache.set(CacheEntry(key=key, data=_make_frame()))
        assert cache.has(key)
        assert cache.invalidate(key)
        assert not cache.has(key)

    def test_stats(self, tmp_path):
        cache = ParquetCache(cache_dir=str(tmp_path))
        cache.set(CacheEntry(key=_make_key(), data=_make_frame()))
        s = cache.stats()
        assert s["level"] == "L2_parquet"
        assert s["entries"] == 1


# ---------------------------------------------------------------------- #
# 4. CacheManifest
# ---------------------------------------------------------------------- #
class TestCacheManifest:
    def test_add_and_get(self, tmp_path):
        m = CacheManifest(path=str(tmp_path / "manifest.json"))
        from quantlab.research.cache import CacheManifestEntry
        entry = CacheManifestEntry(
            key="k1", node_id="rsi", node_fingerprint="f1", level="L1"
        )
        m.add(entry)
        got = m.get("k1")
        assert got is not None
        assert got.node_id == "rsi"

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "manifest.json")
        m1 = CacheManifest(path=path)
        from quantlab.research.cache import CacheManifestEntry
        m1.add(CacheManifestEntry(key="k1", node_id="rsi", node_fingerprint="f1"))
        # 新实例读取
        m2 = CacheManifest(path=path)
        assert m2.get("k1") is not None

    def test_find_by_node(self, tmp_path):
        m = CacheManifest(path=str(tmp_path / "m.json"))
        from quantlab.research.cache import CacheManifestEntry
        m.add(CacheManifestEntry(key="k1", node_id="rsi", node_fingerprint="f1"))
        m.add(CacheManifestEntry(key="k2", node_id="rsi", node_fingerprint="f2"))
        m.add(CacheManifestEntry(key="k3", node_id="ema", node_fingerprint="f3"))
        rsis = m.find_by_node("rsi")
        assert len(rsis) == 2

    def test_find_downstream(self, tmp_path):
        m = CacheManifest(path=str(tmp_path / "m.json"))
        from quantlab.research.cache import CacheManifestEntry
        m.add(CacheManifestEntry(key="up", node_id="close", node_fingerprint="f1"))
        m.add(
            CacheManifestEntry(
                key="down", node_id="rsi", node_fingerprint="f2", upstream_keys=["up"]
            )
        )
        ds = m.find_downstream("up")
        assert len(ds) == 1
        assert ds[0].node_id == "rsi"


# ---------------------------------------------------------------------- #
# 5. CacheInvalidator
# ---------------------------------------------------------------------- #
class TestCacheInvalidator:
    def test_invalidate_propagation(self, tmp_path):
        """close 变更 → return/ema/rsi 失效 (传播)，ATR 不失效 (无依赖)。"""
        m = CacheManifest(path=str(tmp_path / "m.json"))
        from quantlab.research.cache import CacheManifestEntry
        # 注册缓存
        for nid in ("close", "return", "ema", "rsi", "atr"):
            m.add(CacheManifestEntry(key=f"k_{nid}", node_id=nid, node_fingerprint="f"))
        inv = CacheInvalidator(manifest=m)
        # 注册依赖
        inv.register_dependency("close", "return")
        inv.register_dependency("close", "ema")
        inv.register_dependency("ema", "rsi")  # rsi 依赖 ema (假设)
        # atr 不注册 (不依赖 close)
        invalidated = inv.invalidate("close")
        # close + return + ema + rsi 都失效，atr 不失效
        assert set(invalidated) == {"close", "return", "ema", "rsi"}
        assert "atr" not in invalidated
        # manifest 中 close/return/ema/rsi 条目已删除
        assert m.find_by_node("close") == []
        assert m.find_by_node("atr") != []

    def test_downstream_of(self, tmp_path):
        m = CacheManifest(path=str(tmp_path / "m.json"))
        inv = CacheInvalidator(manifest=m)
        inv.register_dependency("close", "return")
        inv.register_dependency("return", "rsi")
        assert inv.downstream_of("close") == {"return"}
        assert inv.all_downstream("close") == {"return", "rsi"}


# ---------------------------------------------------------------------- #
# 6. CachePlanner
# ---------------------------------------------------------------------- #
class TestCachePlanner:
    def test_plan_by_cost(self):
        """cost<=2 → L1, cost==3 → L2, cost>=4 → L3。"""
        planner = CachePlanner()
        g = ResearchGraph()
        g.add_node(CloseNode())           # cost=1 → L1
        g.add_node(RSINode(window=14))    # cost=2 → L1
        g.add_node(MACDNode())            # cost=2 → L1
        compiled = g.compile()
        plan = planner.plan(g, compiled)
        assert plan["close"].level == "L1"
        assert plan["rsi"].level == "L1"
        assert plan["macd"].level == "L1"

    def test_expensive_node_to_l3(self):
        from quantlab.research.builtin import Alpha014Node
        planner = CachePlanner()
        g = ResearchGraph()
        g.add_node(Alpha014Node())  # cost=3 → L2
        compiled = g.compile()
        plan = planner.plan(g, compiled)
        assert plan["alpha014"].level == "L2"


# ---------------------------------------------------------------------- #
# 7. CacheManager 端到端
# ---------------------------------------------------------------------- #
class TestCacheManager:
    def test_l1_hit_miss(self, tmp_path):
        cm = CacheManager(
            manifest=CacheManifest(path=str(tmp_path / "m.json")),
            parquet_cache=ParquetCache(cache_dir=str(tmp_path / "pq")),
        )
        key = _make_key()
        frame = _make_frame()
        # miss
        assert cm.get(key) is None
        # set L1
        cm.set(key, frame, level="L1")
        # hit
        got = cm.get(key)
        assert got is not None
        assert got.data.data.shape == frame.data.shape

    def test_l2_backfill_l1(self, tmp_path):
        """L2 命中后回填 L1。"""
        cm = CacheManager(
            manifest=CacheManifest(path=str(tmp_path / "m.json")),
            parquet_cache=ParquetCache(cache_dir=str(tmp_path / "pq")),
        )
        key = _make_key()
        frame = _make_frame()
        # set L2
        cm.set(key, frame, level="L2")
        # 清空 L1 (模拟 L1 miss)
        cm.memory.clear()
        # get → 从 L2 读 → 回填 L1
        got = cm.get(key)
        assert got is not None
        assert cm.memory.has(key)

    def test_invalidate_node(self, tmp_path):
        cm = CacheManager(
            manifest=CacheManifest(path=str(tmp_path / "m.json")),
            parquet_cache=ParquetCache(cache_dir=str(tmp_path / "pq")),
        )
        # 注册依赖
        cm.invalidator.register_dependency("close", "rsi")
        key_close = _make_key("close", "f1")
        key_rsi = _make_key("rsi", "f2")
        cm.set(key_close, _make_frame(), level="L1")
        cm.set(key_rsi, _make_frame(), level="L1")
        # 失效 close → rsi 也失效
        invalidated = cm.invalidate_node("close")
        assert set(invalidated) == {"close", "rsi"}
        assert not cm.memory.has(key_close)
        assert not cm.memory.has(key_rsi)

    def test_stats(self, tmp_path):
        cm = CacheManager(
            manifest=CacheManifest(path=str(tmp_path / "m.json")),
            parquet_cache=ParquetCache(cache_dir=str(tmp_path / "pq")),
        )
        cm.set(_make_key(), _make_frame(), level="L1")
        s = cm.stats()
        assert "memory" in s
        assert s["memory"]["entries"] == 1
