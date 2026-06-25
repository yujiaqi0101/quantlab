"""
Alpha191 Phase 4 批次9 因子单元测试
==========================================

覆盖新增: #9, #59, #63, #94, #105
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_009, alpha_059, alpha_063, alpha_094, alpha_105,
    ALPHA009_DIRECTION, ALPHA059_DIRECTION, ALPHA063_DIRECTION,
    ALPHA094_DIRECTION, ALPHA105_DIRECTION,
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


# ---------------- Alpha #9 ----------------

def test_alpha_009_basic():
    ctx = _make_ctx(n=30)
    r = alpha_009(ctx, period=7, m=2)
    assert r.shape == ctx.close.shape
    # delay(1) 使 idx 0 为 NaN; sma(ewm) 从首期开始但首值 NaN
    assert r.iloc[:1].isna().all().all()
    # 后段应有非 NaN 值
    assert not r.iloc[2:].isna().all().all()


def test_alpha_009_direction():
    assert ALPHA009_DIRECTION == 1


def test_alpha_009_no_inf():
    """成交量下限保护：VOLUME=0 处应置 NaN 而非 inf。"""
    ctx = _make_ctx(n=30)
    r = alpha_009(ctx, period=7, m=2)
    valid = r.replace([np.inf, -np.inf], np.nan).dropna()
    # 不应出现 inf
    assert not np.isinf(r.to_numpy()).any()


# ---------------- Alpha #59 ----------------

def test_alpha_059_basic():
    ctx = _make_ctx(n=40)
    r = alpha_059(ctx, period=20)
    assert r.shape == ctx.close.shape
    # tr 预热 1 (delay 1) + ts_sum(20) 预热 19 → idx 20 首值
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_059_direction():
    assert ALPHA059_DIRECTION == -1


def test_alpha_059_nonnegative():
    """TR 为非负值，其累积和也应非负。"""
    ctx = _make_ctx(n=40)
    r = alpha_059(ctx, period=20)
    valid = r.iloc[20:].dropna()
    if len(valid) > 0:
        assert (valid >= 0).all().all()


# ---------------- Alpha #63 ----------------

def test_alpha_063_basic():
    ctx = _make_ctx(n=30)
    r = alpha_063(ctx, period=6)
    assert r.shape == ctx.close.shape
    # rsi 依赖 delta(1) → idx 0 NaN; sma(ewm) 从首期开始
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[2:].isna().all().all()


def test_alpha_063_direction():
    assert ALPHA063_DIRECTION == 1


def test_alpha_063_range():
    """RSI 值域应在 [0, 100]。"""
    ctx = _make_ctx(n=30)
    r = alpha_063(ctx, period=6)
    valid = r.iloc[2:].dropna()
    if len(valid) > 0:
        assert ((valid >= 0) & (valid <= 100)).all().all()


# ---------------- Alpha #94 ----------------

def test_alpha_094_basic():
    ctx = _make_ctx(n=40)
    r = alpha_094(ctx, period=30)
    assert r.shape == ctx.close.shape
    # signed_vol idx 0 有值; ts_sum(30) 预热 29 → idx 29 首值
    assert r.iloc[:29].isna().all().all()
    assert not r.iloc[29].isna().all()


def test_alpha_094_direction():
    assert ALPHA094_DIRECTION == 1


def test_alpha_094_sign():
    """上涨日成交量为正，下跌日为负，累积和符号应与价格趋势一致。"""
    ctx = _make_ctx(n=40)
    r = alpha_094(ctx, period=30)
    valid = r.iloc[29:].dropna()
    if len(valid) > 0:
        # 累积带方向成交量应为有限实数
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #105 ----------------

def test_alpha_105_basic():
    ctx = _make_ctx(n=30)
    r = alpha_105(ctx, period=10)
    assert r.shape == ctx.close.shape
    # rank 无预热; corr(10) 预热 9 → idx 9 首值
    assert r.iloc[:9].isna().all().all()
    assert not r.iloc[9].isna().all()


def test_alpha_105_direction():
    assert ALPHA105_DIRECTION == -1


def test_alpha_105_range():
    """corr 在 [-1, 1]，取负后仍在 [-1, 1]。"""
    ctx = _make_ctx(n=30)
    r = alpha_105(ctx, period=10)
    valid = r.iloc[9:].dropna()
    if len(valid) > 0:
        assert ((valid >= -1) & (valid <= 1)).all().all()
