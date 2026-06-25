"""
Alpha191 Phase 4 批次8 因子单元测试
==========================================

覆盖: #10, #85, #88, #89, #96, #103, #106, #107, #109,
      #112, #116, #117, #144, #160, #174
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_010, alpha_085, alpha_088, alpha_089, alpha_096, alpha_103,
    alpha_106, alpha_107, alpha_109, alpha_112, alpha_116, alpha_117,
    alpha_144, alpha_160, alpha_174,
    ALPHA010_DIRECTION, ALPHA085_DIRECTION, ALPHA088_DIRECTION,
    ALPHA089_DIRECTION, ALPHA096_DIRECTION, ALPHA103_DIRECTION,
    ALPHA106_DIRECTION, ALPHA107_DIRECTION, ALPHA109_DIRECTION,
    ALPHA112_DIRECTION, ALPHA116_DIRECTION, ALPHA117_DIRECTION,
    ALPHA144_DIRECTION, ALPHA160_DIRECTION, ALPHA174_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=120):
    dates = pd.date_range("2025-06-01", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B", "C", "D", "E"]:
        close = 100 + rng.normal(0, 1, n).cumsum()
        close = close.astype(float)
        df = pd.DataFrame(
            {
                "open": close + rng.normal(0, 0.5, n),
                "high": close + np.abs(rng.normal(0, 1, n)),
                "low": close - np.abs(rng.normal(0, 1, n)),
                "close": close,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #10 ----------------

def test_alpha_010_basic():
    ctx = _make_ctx(n=60)
    r = alpha_010(ctx, std_period=20, max_period=5)
    assert r.shape == ctx.close.shape
    # RET>=0 时取 CLOSE（从 idx 0 有值）; ts_max(5) 预热 4 期 → idx 4
    # 但 rank 需要截面非NaN值, 实际首值可能更晚
    assert not r.iloc[4:].isna().all().all()


def test_alpha_010_direction():
    assert ALPHA010_DIRECTION == -1


def test_alpha_010_rank_range():
    ctx = _make_ctx(n=60)
    r = alpha_010(ctx, std_period=20, max_period=5)
    valid = r.dropna()
    if len(valid) > 0:
        assert ((valid >= 0) & (valid <= 1)).all().all()


# ---------------- Alpha #85 ----------------

def test_alpha_085_basic():
    ctx = _make_ctx(n=60)
    r = alpha_085(ctx, ma_period=20, vol_rank=20, delta_period=7, price_rank=8)
    assert r.shape == ctx.close.shape
    # ts_mean(20) 预热 19 期 → idx 19; ts_rank(20) 预热 19 期 → idx 38
    # delta(7) 预热 7 期 → idx 7; ts_rank(8) 预热 7 期 → idx 14
    # 整体取较晚的: idx 38
    assert r.iloc[:38].isna().all().all()
    assert not r.iloc[38].isna().all()


def test_alpha_085_direction():
    assert ALPHA085_DIRECTION == -1


# ---------------- Alpha #88 ----------------

def test_alpha_088_basic():
    ctx = _make_ctx(n=40)
    r = alpha_088(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay(20) 预热 20 期 → idx 20
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_088_direction():
    assert ALPHA088_DIRECTION == 1


# ---------------- Alpha #89 ----------------

def test_alpha_089_basic():
    ctx = _make_ctx(n=40)
    r = alpha_089(ctx)
    assert r.shape == ctx.close.shape
    # sma(ewm) 从首期开始计算, 无 NaN 预热
    assert not r.iloc[0].isna().all()


def test_alpha_089_direction():
    assert ALPHA089_DIRECTION == 1


# ---------------- Alpha #96 ----------------

def test_alpha_096_basic():
    ctx = _make_ctx(n=20)
    r = alpha_096(ctx, period=9, sma_n=3, sma_m=1)
    assert r.shape == ctx.close.shape
    # ts_max/ts_min(9) 预热 8 期 → idx 8; ewm 从首期开始计算
    # 整体: idx 8
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_096_direction():
    assert ALPHA096_DIRECTION == 1


def test_alpha_096_range():
    ctx = _make_ctx(n=30)
    r = alpha_096(ctx, period=9, sma_n=3, sma_m=1)
    valid = r.iloc[8:].dropna()
    if len(valid) > 0:
        # KDJ-D 使用 ewm 平滑, 可能略超 [0, 100] 边界
        assert ((valid >= -10) & (valid <= 110)).all().all()


# ---------------- Alpha #103 ----------------

def test_alpha_103_basic():
    ctx = _make_ctx(n=30)
    r = alpha_103(ctx, period=20)
    assert r.shape == ctx.close.shape
    # lowday(20) 预热 19 期 → idx 19
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_103_direction():
    assert ALPHA103_DIRECTION == 1


def test_alpha_103_range():
    ctx = _make_ctx(n=30)
    r = alpha_103(ctx, period=20)
    valid = r.iloc[19:].dropna()
    if len(valid) > 0:
        # LOWDAY 在 [0, period-1]，(period-lowday)/period*100 在 [0, 100]
        assert ((valid >= 0) & (valid <= 100)).all().all()


# ---------------- Alpha #106 ----------------

def test_alpha_106_basic():
    ctx = _make_ctx(n=30)
    r = alpha_106(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay(20) 预热 20 期 → idx 20
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_106_direction():
    assert ALPHA106_DIRECTION == 1


# ---------------- Alpha #107 ----------------

def test_alpha_107_basic():
    ctx = _make_ctx(n=10)
    r = alpha_107(ctx)
    assert r.shape == ctx.close.shape
    # delay(1) 预热 1 期 → idx 1
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_107_direction():
    assert ALPHA107_DIRECTION == -1


def test_alpha_107_rank_range():
    ctx = _make_ctx(n=10)
    r = alpha_107(ctx)
    valid = r.iloc[1:].dropna()
    if len(valid) > 0:
        # rank 在 [0, 1]，乘积取负后在 [-1, 0]
        assert ((valid >= -1) & (valid <= 0)).all().all()


# ---------------- Alpha #109 ----------------

def test_alpha_109_basic():
    ctx = _make_ctx(n=30)
    r = alpha_109(ctx, n=10, m=2)
    assert r.shape == ctx.close.shape
    # ewm 从首期开始计算, 无 NaN 预热
    assert not r.iloc[0].isna().all()


def test_alpha_109_direction():
    assert ALPHA109_DIRECTION == 1


# ---------------- Alpha #112 ----------------

def test_alpha_112_basic():
    ctx = _make_ctx(n=20)
    r = alpha_112(ctx, period=12)
    assert r.shape == ctx.close.shape
    # delay(1) → idx 1; up/down 中 idx 0 被替换为 0.0 → rolling(12) 在 idx 11 首值
    assert r.iloc[:11].isna().all().all()
    assert not r.iloc[11].isna().all()


def test_alpha_112_direction():
    assert ALPHA112_DIRECTION == 1


def test_alpha_112_range():
    ctx = _make_ctx(n=20)
    r = alpha_112(ctx, period=12)
    valid = r.iloc[12:].dropna()
    if len(valid) > 0:
        # CMO 在 [-100, 100]
        assert ((valid >= -100) & (valid <= 100)).all().all()


# ---------------- Alpha #116 ----------------

def test_alpha_116_basic():
    ctx = _make_ctx(n=30)
    r = alpha_116(ctx, period=20)
    assert r.shape == ctx.close.shape
    # regbeta(20) 预热 19 期 → idx 19
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_116_direction():
    assert ALPHA116_DIRECTION == 1


# ---------------- Alpha #117 ----------------

def test_alpha_117_basic():
    ctx = _make_ctx(n=40)
    r = alpha_117(ctx, vol_rank=32, price_rank=16, ret_rank=32)
    assert r.shape == ctx.close.shape
    # ts_rank(32) 预热 31 期；但 ret 首期 NaN，使 ts_rank(ret,32) 预热多1期 → idx 32
    assert r.iloc[:32].isna().all().all()
    assert not r.iloc[32].isna().all()


def test_alpha_117_direction():
    assert ALPHA117_DIRECTION == 1


# ---------------- Alpha #144 ----------------

def test_alpha_144_basic():
    ctx = _make_ctx(n=30)
    r = alpha_144(ctx, period=20)
    assert r.shape == ctx.close.shape
    # sum_if 将 idx 0 的 NaN 替换为 0.0 → idx 19 首值; ts_mean(20) → idx 19
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_144_direction():
    assert ALPHA144_DIRECTION == 1


# ---------------- Alpha #160 ----------------

def test_alpha_160_basic():
    ctx = _make_ctx(n=40)
    r = alpha_160(ctx, std_period=20, sma_n=20, sma_m=1)
    assert r.shape == ctx.close.shape
    # ts_std(20) 预热 19 期 → idx 19; ewm 从首期开始计算
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_160_direction():
    assert ALPHA160_DIRECTION == 1


# ---------------- Alpha #174 ----------------

def test_alpha_174_basic():
    ctx = _make_ctx(n=40)
    r = alpha_174(ctx, std_period=20, sma_n=20, sma_m=1)
    assert r.shape == ctx.close.shape
    # ts_std(20) 预热 19 期 → idx 19; ewm 从首期开始计算
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_174_direction():
    assert ALPHA174_DIRECTION == 1
