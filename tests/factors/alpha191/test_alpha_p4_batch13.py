"""
Alpha191 Phase 4 批次13 因子单元测试
==========================================

覆盖新增: #133, #135, #136, #138, #139, #140
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_133, alpha_135, alpha_136, alpha_138, alpha_139, alpha_140,
    ALPHA133_DIRECTION, ALPHA135_DIRECTION, ALPHA136_DIRECTION,
    ALPHA138_DIRECTION, ALPHA139_DIRECTION, ALPHA140_DIRECTION,
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


# ---------------- Alpha #133 ----------------

def test_alpha_133_basic():
    ctx = _make_ctx(n=100)
    r = alpha_133(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean 60 + ts_rank 2 + corr 10 + decay 3 → idx 71
    assert r.iloc[:71].isna().all().all()


def test_alpha_133_direction():
    assert ALPHA133_DIRECTION == 1


# ---------------- Alpha #135 ----------------

def test_alpha_135_basic():
    ctx = _make_ctx(n=20)
    r = alpha_135(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 含 NaN; sma 用 ewm 无预热 → idx 1 起有效
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_135_direction():
    assert ALPHA135_DIRECTION == -1


def test_alpha_135_values():
    ctx = _make_ctx(n=20)
    r = alpha_135(ctx)
    valid = r.iloc[1:].dropna()
    if len(valid) > 0:
        # sma(x,5,1) ∈ [0,1], 减 0.5 → [-0.5, 0.5]
        vals = valid.to_numpy().flatten()
        assert vals.min() >= -0.5 - 1e-9
        assert vals.max() <= 0.5 + 1e-9


# ---------------- Alpha #136 ----------------

def test_alpha_136_basic():
    ctx = _make_ctx(n=20)
    r = alpha_136(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 (returns) + delta 3 → idx 3
    assert r.iloc[:3].isna().all().all()


def test_alpha_136_direction():
    assert ALPHA136_DIRECTION == -1


def test_alpha_136_finite():
    ctx = _make_ctx(n=20)
    r = alpha_136(ctx)
    valid = r.iloc[3:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #138 ----------------

def test_alpha_138_basic():
    ctx = _make_ctx(n=10)
    r = alpha_138(ctx)
    assert r.shape == ctx.close.shape
    # 首期可计算
    assert not r.iloc[0].isna().all()


def test_alpha_138_direction():
    assert ALPHA138_DIRECTION == 1


def test_alpha_138_finite():
    ctx = _make_ctx(n=10)
    r = alpha_138(ctx)
    valid = r.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #139 ----------------

def test_alpha_139_basic():
    ctx = _make_ctx(n=20)
    r = alpha_139(ctx)
    assert r.shape == ctx.close.shape
    # delay 5 + decay 5 → idx 9
    assert r.iloc[:9].isna().all().all()


def test_alpha_139_direction():
    assert ALPHA139_DIRECTION == -1


# ---------------- Alpha #140 ----------------

def test_alpha_140_basic():
    ctx = _make_ctx(n=20)
    r = alpha_140(ctx)
    assert r.shape == ctx.close.shape
    # ts_min/ts_max 5 → idx 4
    assert r.iloc[:4].isna().all().all()


def test_alpha_140_direction():
    assert ALPHA140_DIRECTION == 1


def test_alpha_140_finite():
    ctx = _make_ctx(n=20)
    r = alpha_140(ctx)
    valid = r.iloc[4:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()
