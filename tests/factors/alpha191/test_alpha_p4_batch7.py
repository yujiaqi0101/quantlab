"""
Alpha191 Phase 4 批次7 因子单元测试
==========================================

覆盖: #80, #81, #102, #111, #120, #124, #126, #128,
      #132, #134, #145, #150, #155, #168, #178, #191
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_080, alpha_081, alpha_102, alpha_111, alpha_120, alpha_124,
    alpha_126, alpha_128, alpha_132, alpha_134, alpha_145, alpha_150,
    alpha_155, alpha_168, alpha_178, alpha_191,
    ALPHA080_DIRECTION, ALPHA081_DIRECTION, ALPHA102_DIRECTION,
    ALPHA111_DIRECTION, ALPHA120_DIRECTION, ALPHA124_DIRECTION,
    ALPHA126_DIRECTION, ALPHA128_DIRECTION, ALPHA132_DIRECTION,
    ALPHA134_DIRECTION, ALPHA145_DIRECTION, ALPHA150_DIRECTION,
    ALPHA155_DIRECTION, ALPHA168_DIRECTION, ALPHA178_DIRECTION,
    ALPHA191_DIRECTION,
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


# ---------------- Alpha #80 ----------------

def test_alpha_080_basic():
    ctx = _make_ctx(n=30)
    r = alpha_080(ctx, period=5)
    assert r.shape == ctx.close.shape
    # delay(5) 预热 5 期 → idx 5 首值
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_080_direction():
    assert ALPHA080_DIRECTION == 1


# ---------------- Alpha #81 ----------------

def test_alpha_081_basic():
    ctx = _make_ctx(n=30)
    r = alpha_081(ctx, n=21, m=2)
    assert r.shape == ctx.close.shape
    # ewm 从首期开始, 无 NaN 预热
    assert not r.iloc[0].isna().all()


def test_alpha_081_direction():
    assert ALPHA081_DIRECTION == 1


# ---------------- Alpha #102 ----------------

def test_alpha_102_basic():
    ctx = _make_ctx(n=30)
    r = alpha_102(ctx, n=6, m=1)
    assert r.shape == ctx.close.shape
    # delta(1) idx1 + ewm 从首个非NaN开始 → idx 1 首值
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_102_direction():
    assert ALPHA102_DIRECTION == 1


def test_alpha_102_no_inf():
    """分母为 0 时不应产生 inf"""
    ctx = _make_ctx(n=30)
    r = alpha_102(ctx, n=6, m=1)
    assert not np.isinf(r.values).any()


# ---------------- Alpha #111 ----------------

def test_alpha_111_basic():
    ctx = _make_ctx(n=30)
    r = alpha_111(ctx, long_n=11, short_n=4, m=2)
    assert r.shape == ctx.close.shape
    # ewm 从首期开始, 但 (H-L) 可能为 0 → NaN 传播
    # 首期至少有部分非NaN值
    assert not r.iloc[0].isna().all()


def test_alpha_111_direction():
    assert ALPHA111_DIRECTION == 1


# ---------------- Alpha #120 ----------------

def test_alpha_120_basic():
    ctx = _make_ctx(n=30)
    r = alpha_120(ctx)
    assert r.shape == ctx.close.shape
    # 无预热期 (仅 rank + 除法)
    assert not r.iloc[0].isna().all()


def test_alpha_120_direction():
    assert ALPHA120_DIRECTION == 1


def test_alpha_120_no_inf():
    """分母为 0 时不应产生 inf"""
    ctx = _make_ctx(n=30)
    r = alpha_120(ctx)
    assert not np.isinf(r.values).any()


# ---------------- Alpha #124 ----------------

def test_alpha_124_basic():
    ctx = _make_ctx(n=60)
    r = alpha_124(ctx, max_period=30, decay_period=2)
    assert r.shape == ctx.close.shape
    # ts_max(30) idx29 + decay_linear(2) idx30 → idx 30 首值
    assert r.iloc[:30].isna().all().all()
    assert not r.iloc[30].isna().all()


def test_alpha_124_direction():
    assert ALPHA124_DIRECTION == 1


def test_alpha_124_no_inf():
    """分母为 0 时不应产生 inf"""
    ctx = _make_ctx(n=60)
    r = alpha_124(ctx, max_period=30, decay_period=2)
    finite_part = r.iloc[30:]
    assert not np.isinf(finite_part.values).any()


# ---------------- Alpha #126 ----------------

def test_alpha_126_basic():
    ctx = _make_ctx(n=30)
    r = alpha_126(ctx)
    assert r.shape == ctx.close.shape
    # 无预热期
    assert not r.iloc[0].isna().all()
    # 验证公式: (C+H+L)/3
    expected = (ctx.close + ctx.high + ctx.low) / 3.0
    pd.testing.assert_frame_equal(r, expected)


def test_alpha_126_direction():
    assert ALPHA126_DIRECTION == 1


# ---------------- Alpha #128 ----------------

def test_alpha_128_basic():
    ctx = _make_ctx(n=30)
    r = alpha_128(ctx, period=14)
    assert r.shape == ctx.close.shape
    # delay(1) idx1 + sum_if(14) 从首个非NaN输入(idx0)开始累积0值 → idx 13 首值
    # (条件为假时值替换为0, rolling(14) 在 idx13 有14个非NaN值)
    assert r.iloc[:13].isna().all().all()
    assert not r.iloc[13].isna().all()


def test_alpha_128_direction():
    assert ALPHA128_DIRECTION == 1


def test_alpha_128_range():
    """MFI 应在 0-100 之间"""
    ctx = _make_ctx(n=30)
    r = alpha_128(ctx, period=14)
    valid = r.iloc[14:].dropna()
    if len(valid) > 0:
        assert (valid >= 0).all().all()
        assert (valid <= 100).all().all()


# ---------------- Alpha #132 ----------------

def test_alpha_132_basic():
    ctx = _make_ctx(n=30)
    r = alpha_132(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_mean(20) 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_132_direction():
    assert ALPHA132_DIRECTION == 1


# ---------------- Alpha #134 ----------------

def test_alpha_134_basic():
    ctx = _make_ctx(n=30)
    r = alpha_134(ctx, period=12)
    assert r.shape == ctx.close.shape
    # delay(12) 预热 12 → idx 12 首值
    assert r.iloc[:12].isna().all().all()
    assert not r.iloc[12].isna().all()


def test_alpha_134_direction():
    assert ALPHA134_DIRECTION == 1


# ---------------- Alpha #145 ----------------

def test_alpha_145_basic():
    ctx = _make_ctx(n=60)
    r = alpha_145(ctx, short=9, long=26, mid=12)
    assert r.shape == ctx.close.shape
    # max(9, 26, 12) = 26, 预热 25 → idx 25 首值
    assert r.iloc[:25].isna().all().all()
    assert not r.iloc[25].isna().all()


def test_alpha_145_direction():
    assert ALPHA145_DIRECTION == 1


def test_alpha_145_no_inf():
    """分母为 0 时不应产生 inf"""
    ctx = _make_ctx(n=60)
    r = alpha_145(ctx, short=9, long=26, mid=12)
    finite_part = r.iloc[25:]
    assert not np.isinf(finite_part.values).any()


# ---------------- Alpha #150 ----------------

def test_alpha_150_basic():
    ctx = _make_ctx(n=30)
    r = alpha_150(ctx)
    assert r.shape == ctx.close.shape
    # 无预热期
    assert not r.iloc[0].isna().all()
    # 验证公式: (C+H+L)/3 * V
    expected = (ctx.close + ctx.high + ctx.low) / 3.0 * ctx.volume
    pd.testing.assert_frame_equal(r, expected)


def test_alpha_150_direction():
    assert ALPHA150_DIRECTION == 1


# ---------------- Alpha #155 ----------------

def test_alpha_155_basic():
    ctx = _make_ctx(n=60)
    r = alpha_155(ctx, short=13, long=27, signal=10, m=2)
    assert r.shape == ctx.close.shape
    # ewm 从首期开始, 无 NaN 预热
    assert not r.iloc[0].isna().all()


def test_alpha_155_direction():
    assert ALPHA155_DIRECTION == 1


# ---------------- Alpha #168 ----------------

def test_alpha_168_basic():
    ctx = _make_ctx(n=30)
    r = alpha_168(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_mean(20) 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_168_direction():
    assert ALPHA168_DIRECTION == -1


def test_alpha_168_sign():
    """方向为 -1, 应返回负值"""
    ctx = _make_ctx(n=30)
    r = alpha_168(ctx, period=20)
    valid = r.iloc[19:].dropna()
    if len(valid) > 0:
        assert (valid <= 0).all().all()


# ---------------- Alpha #178 ----------------

def test_alpha_178_basic():
    ctx = _make_ctx(n=30)
    r = alpha_178(ctx)
    assert r.shape == ctx.close.shape
    # delay(1) 预热 1 → idx 1 首值
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_178_direction():
    assert ALPHA178_DIRECTION == 1


# ---------------- Alpha #191 ----------------

def test_alpha_191_basic():
    ctx = _make_ctx(n=60)
    r = alpha_191(ctx, ma_period=20, corr_period=5)
    assert r.shape == ctx.close.shape
    # ts_mean(20) idx19 + corr(5) idx23 → idx 23 首值
    assert r.iloc[:23].isna().all().all()
    assert not r.iloc[23].isna().all()


def test_alpha_191_direction():
    assert ALPHA191_DIRECTION == 1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_080",
        "quantlab.factors.alpha191.alpha_081",
        "quantlab.factors.alpha191.alpha_102",
        "quantlab.factors.alpha191.alpha_111",
        "quantlab.factors.alpha191.alpha_120",
        "quantlab.factors.alpha191.alpha_124",
        "quantlab.factors.alpha191.alpha_126",
        "quantlab.factors.alpha191.alpha_128",
        "quantlab.factors.alpha191.alpha_132",
        "quantlab.factors.alpha191.alpha_134",
        "quantlab.factors.alpha191.alpha_145",
        "quantlab.factors.alpha191.alpha_150",
        "quantlab.factors.alpha191.alpha_155",
        "quantlab.factors.alpha191.alpha_168",
        "quantlab.factors.alpha191.alpha_178",
        "quantlab.factors.alpha191.alpha_191",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
