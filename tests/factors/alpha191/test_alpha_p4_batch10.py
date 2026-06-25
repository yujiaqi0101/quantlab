"""
Alpha191 Phase 4 批次10 因子单元测试
==========================================

覆盖新增: #4, #52, #55, #56, #69, #101
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_004, alpha_052, alpha_055, alpha_056, alpha_069, alpha_101,
    ALPHA004_DIRECTION, ALPHA052_DIRECTION, ALPHA055_DIRECTION,
    ALPHA056_DIRECTION, ALPHA069_DIRECTION, ALPHA101_DIRECTION,
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
                "vwap": close + rng.normal(0, 0.3, n),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #4 ----------------

def test_alpha_004_basic():
    ctx = _make_ctx(n=30)
    r = alpha_004(ctx)
    assert r.shape == ctx.close.shape
    # ma8 预热 7; ma2 预热 1; ma20 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_004_direction():
    assert ALPHA004_DIRECTION == 1


def test_alpha_004_values():
    ctx = _make_ctx(n=30)
    r = alpha_004(ctx)
    valid = r.iloc[19:].dropna()
    if len(valid) > 0:
        assert set(valid.to_numpy().flatten().tolist()) - {np.nan} <= {-1.0, 1.0}


# ---------------- Alpha #52 ----------------

def test_alpha_052_basic():
    ctx = _make_ctx(n=40)
    r = alpha_052(ctx, period=26)
    assert r.shape == ctx.close.shape
    # delay 1 + ts_sum 26 → idx 26 首值
    assert r.iloc[:26].isna().all().all()
    assert not r.iloc[26].isna().all()


def test_alpha_052_direction():
    assert ALPHA052_DIRECTION == 1


def test_alpha_052_finite():
    ctx = _make_ctx(n=40)
    r = alpha_052(ctx, period=26)
    valid = r.iloc[26:].dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #55 ----------------

def test_alpha_055_basic():
    ctx = _make_ctx(n=40)
    r = alpha_055(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay 1 + ts_sum 20 → idx 20 首值
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_055_direction():
    assert ALPHA055_DIRECTION == -1


def test_alpha_055_finite():
    ctx = _make_ctx(n=40)
    r = alpha_055(ctx, period=20)
    valid = r.iloc[20:].dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #56 ----------------

def test_alpha_056_basic():
    ctx = _make_ctx(n=80)
    r = alpha_056(ctx)
    assert r.shape == ctx.close.shape
    # 右侧: ts_mean(40) + ts_sum(19) + corr(13) → 预热 ~71
    assert r.iloc[:71].isna().all().all() or r.iloc[:50].isna().all().all()


def test_alpha_056_direction():
    assert ALPHA056_DIRECTION == 1


# ---------------- Alpha #69 ----------------

def test_alpha_069_basic():
    ctx = _make_ctx(n=40)
    r = alpha_069(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay 1 + ts_sum 20 → idx 20 首值
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_069_direction():
    assert ALPHA069_DIRECTION == 1


def test_alpha_069_finite():
    ctx = _make_ctx(n=40)
    r = alpha_069(ctx, period=20)
    valid = r.iloc[20:].dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #101 ----------------

def test_alpha_101_basic():
    ctx = _make_ctx(n=80)
    r = alpha_101(ctx)
    assert r.shape == ctx.close.shape
    # 左侧: ts_mean(30)+ts_sum(37)+corr(15) → 预热 81
    # 右侧: corr(rank hybrid, rank vol, 11)
    # 通常前约 80 期为 NaN
    assert r.iloc[:50].isna().all().all()


def test_alpha_101_direction():
    assert ALPHA101_DIRECTION == -1


def test_alpha_101_values():
    ctx = _make_ctx(n=100)
    r = alpha_101(ctx)
    valid = r.dropna()
    if len(valid) > 0:
        unique_vals = set(valid.to_numpy().flatten().tolist()) - {np.nan}
        assert unique_vals <= {0.0, -1.0}
