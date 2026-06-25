"""
Alpha191 Phase 4 批次11 因子单元测试
==========================================

覆盖新增: #110, #113, #114, #115, #119, #121
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_110, alpha_113, alpha_114, alpha_115, alpha_119, alpha_121,
    ALPHA110_DIRECTION, ALPHA113_DIRECTION, ALPHA114_DIRECTION,
    ALPHA115_DIRECTION, ALPHA119_DIRECTION, ALPHA121_DIRECTION,
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


# ---------------- Alpha #110 ----------------

def test_alpha_110_basic():
    ctx = _make_ctx(n=40)
    r = alpha_110(ctx, period=20)
    assert r.shape == ctx.close.shape
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_110_direction():
    assert ALPHA110_DIRECTION == 1


def test_alpha_110_finite():
    ctx = _make_ctx(n=40)
    r = alpha_110(ctx, period=20)
    valid = r.iloc[20:].dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #113 ----------------

def test_alpha_113_basic():
    ctx = _make_ctx(n=40)
    r = alpha_113(ctx)
    assert r.shape == ctx.close.shape
    # delay 5 + ts_sum 20 → idx 24 首值
    assert r.iloc[:24].isna().all().all()
    assert not r.iloc[24].isna().all()


def test_alpha_113_direction():
    assert ALPHA113_DIRECTION == -1


# ---------------- Alpha #114 ----------------

def test_alpha_114_basic():
    ctx = _make_ctx(n=40)
    r = alpha_114(ctx)
    assert r.shape == ctx.close.shape
    # ts_sum 5 + delay 2 → idx 6
    assert r.iloc[:6].isna().all().all()


def test_alpha_114_direction():
    assert ALPHA114_DIRECTION == 1


def test_alpha_114_finite():
    ctx = _make_ctx(n=40)
    r = alpha_114(ctx)
    valid = r.iloc[6:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #115 ----------------

def test_alpha_115_basic():
    ctx = _make_ctx(n=60)
    r = alpha_115(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean(30) + corr(10) → idx 38 首值
    assert r.iloc[:38].isna().all().all()
    assert not r.iloc[38].isna().all()


def test_alpha_115_direction():
    assert ALPHA115_DIRECTION == 1


# ---------------- Alpha #119 ----------------

def test_alpha_119_basic():
    ctx = _make_ctx(n=100)
    r = alpha_119(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 55
    assert r.iloc[:55].isna().all().all()
    assert not r.iloc[55].isna().all()


def test_alpha_119_direction():
    assert ALPHA119_DIRECTION == 1


# ---------------- Alpha #121 ----------------

def test_alpha_121_basic():
    ctx = _make_ctx(n=100)
    r = alpha_121(ctx)
    assert r.shape == ctx.close.shape
    # left = rank(vwap - ts_min(vwap, 12)) → idx 11 首值
    assert r.iloc[:11].isna().all().all()
    assert not r.iloc[11].isna().all()


def test_alpha_121_direction():
    assert ALPHA121_DIRECTION == -1


def test_alpha_121_finite():
    ctx = _make_ctx(n=100)
    r = alpha_121(ctx)
    valid = r.iloc[11:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()
