"""
FactorContext 单元测试
======================

验证:
    - 从 dict 构造对齐面板
    - 必需列缺失抛 KeyError
    - vwap/amount 缺失时的派生近似
    - symbols/dates 属性
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.context import FactorContext


def _make_data(symbols=None, n=5, with_vwap=True, with_amount=True):
    """构造测试用 OHLCV 数据。"""
    symbols = symbols or ["A", "B"]
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    out = {}
    rng = np.random.default_rng(42)
    for sym in symbols:
        cols = {
            "open": rng.uniform(90, 110, n),
            "high": rng.uniform(100, 120, n),
            "low": rng.uniform(80, 100, n),
            "close": rng.uniform(95, 115, n),
            "volume": rng.integers(1000, 10000, n).astype(float),
        }
        if with_vwap:
            cols["vwap"] = rng.uniform(95, 115, n)
        if with_amount:
            cols["amount"] = cols["close"] * cols["volume"]
        out[sym] = pd.DataFrame(cols, index=dates)
    return out


def test_from_dict_basic():
    data = _make_data()
    ctx = FactorContext.from_dict(data)
    assert ctx.symbols == ["A", "B"]
    assert len(ctx.dates) == 5
    assert ctx.open.shape == (5, 2)
    assert ctx.close.shape == (5, 2)


def test_from_dict_missing_required_column():
    data = _make_data()
    del data["A"]["high"]
    with pytest.raises(KeyError, match="high"):
        FactorContext.from_dict(data)


def test_from_dict_empty():
    with pytest.raises(ValueError, match="不能为空"):
        FactorContext.from_dict({})


def test_vwap_present():
    data = _make_data(with_vwap=True, with_amount=False)
    ctx = FactorContext.from_dict(data)
    assert ctx.vwap is not None
    # get_vwap 直接返回
    vw = ctx.get_vwap()
    assert vw.shape == (5, 2)


def test_vwap_approx_from_amount_volume():
    """vwap 缺失但有 amount → 用 amount/volume 近似。"""
    data = _make_data(with_vwap=False, with_amount=True)
    ctx = FactorContext.from_dict(data)
    assert ctx.vwap is None
    vw = ctx.get_vwap()
    # 应约等于 close (因为 amount = close*volume)
    np.testing.assert_allclose(
        vw.values, ctx.close.values, rtol=1e-6
    )


def test_vwap_fallback_to_close():
    """vwap 和 amount 都缺失 → 兜底用 close。"""
    data = _make_data(with_vwap=False, with_amount=False)
    ctx = FactorContext.from_dict(data)
    vw = ctx.get_vwap()
    pd.testing.assert_frame_equal(vw, ctx.close)


def test_vwap_volume_zero_yields_nan():
    """volume=0 时 amount/volume 应为 NaN 而非 inf。"""
    data = _make_data(with_vwap=False, with_amount=True)
    data["A"].loc[data["A"].index[0], "volume"] = 0.0
    ctx = FactorContext.from_dict(data)
    vw = ctx.get_vwap()
    assert np.isnan(vw.iloc[0, 0])


def test_amount_present():
    data = _make_data(with_vwap=False, with_amount=True)
    ctx = FactorContext.from_dict(data)
    am = ctx.get_amount()
    assert am.shape == (5, 2)


def test_amount_approx_from_vwap_volume():
    """amount 缺失但有 vwap → 用 vwap*volume 近似。"""
    data = _make_data(with_vwap=True, with_amount=False)
    ctx = FactorContext.from_dict(data)
    am = ctx.get_amount()
    expected = ctx.vwap * ctx.volume
    pd.testing.assert_frame_equal(am, expected)


def test_repr():
    data = _make_data()
    ctx = FactorContext.from_dict(data)
    s = repr(ctx)
    assert "FactorContext" in s
    assert "symbols=2" in s
