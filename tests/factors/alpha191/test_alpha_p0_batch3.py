"""
Alpha191 P0 因子单元测试 (批次3)
================================

覆盖: #76, #137, #158, #161, #165, #175, #183, #188, #189
含 TR/SUMAC 依赖因子。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_076, alpha_137, alpha_158, alpha_161, alpha_165,
    alpha_175, alpha_183, alpha_188, alpha_189,
    ALPHA076_DIRECTION, ALPHA137_DIRECTION, ALPHA158_DIRECTION,
    ALPHA161_DIRECTION, ALPHA165_DIRECTION, ALPHA175_DIRECTION,
    ALPHA183_DIRECTION, ALPHA188_DIRECTION, ALPHA189_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=100):
    """长数据 (5 标的 × n 日)，覆盖 48 日窗口因子。"""
    dates = pd.date_range("2025-01-02", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B", "C", "D", "E"]:
        close = 100 + rng.normal(0, 1, n).cumsum()
        close = close.astype(float)
        high = close + np.abs(rng.normal(0, 1, n))
        low = close - np.abs(rng.normal(0, 1, n))
        df = pd.DataFrame(
            {
                "open": close + rng.normal(0, 0.5, n),
                "high": high,
                "low": low,
                "close": close,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #76 ----------------

def test_alpha_076_basic():
    ctx = _make_ctx(n=100)
    r = alpha_076(ctx, period=20)
    assert r.shape == ctx.close.shape
    # 前 20 期 NaN (RET 首期 NaN + rolling 20)
    assert r.iloc[:20].isna().all().all()
    # 第 20 期开始有值
    assert not r.iloc[20].isna().all()


def test_alpha_076_direction():
    assert ALPHA076_DIRECTION == -1


# ---------------- Alpha #137 ----------------

def test_alpha_137_basic():
    ctx = _make_ctx(n=30)
    r = alpha_137(ctx)
    assert r.shape == ctx.close.shape
    # 首期 NaN (无前一日收盘价)
    assert r.iloc[0].isna().all()
    # 第 1 期开始有值
    assert not r.iloc[1].isna().all()


def test_alpha_137_direction():
    assert ALPHA137_DIRECTION == 1


# ---------------- Alpha #158 ----------------

def test_alpha_158_basic():
    ctx = _make_ctx(n=30)
    r = alpha_158(ctx)
    assert r.shape == ctx.close.shape
    # 无预热期，首期有值
    assert not r.iloc[0].isna().all()


def test_alpha_158_direction():
    assert ALPHA158_DIRECTION == 1


# ---------------- Alpha #161 ----------------

def test_alpha_161_basic():
    ctx = _make_ctx(n=30)
    r = alpha_161(ctx, period=12)
    assert r.shape == ctx.close.shape
    # 前 12 期 NaN (TR 预热 1 + ts_mean 12 - 1 重叠)
    assert r.iloc[:12].isna().all().all()
    assert not r.iloc[12].isna().all()


def test_alpha_161_direction():
    assert ALPHA161_DIRECTION == 1


# ---------------- Alpha #175 ----------------

def test_alpha_175_basic():
    ctx = _make_ctx(n=30)
    r = alpha_175(ctx, period=6)
    assert r.shape == ctx.close.shape
    # 前 6 期 NaN
    assert r.iloc[:6].isna().all().all()
    assert not r.iloc[6].isna().all()


def test_alpha_175_direction():
    assert ALPHA175_DIRECTION == 1


# ---------------- Alpha #165 ----------------

def test_alpha_165_basic():
    # 窗口嵌套: MA48 + SUMAC48 + ts_max/min48 ≈ 141 期预热
    ctx = _make_ctx(n=160)
    r = alpha_165(ctx, period=48)
    assert r.shape == ctx.close.shape
    # 前 140 期 NaN
    assert r.iloc[:140].isna().all().all()
    assert not r.iloc[141].isna().all()


def test_alpha_165_direction():
    assert ALPHA165_DIRECTION == 1


# ---------------- Alpha #183 ----------------

def test_alpha_183_basic():
    # 窗口嵌套: MA24 + SUMAC24 + ts_max/min24 ≈ 69 期预热
    ctx = _make_ctx(n=90)
    r = alpha_183(ctx, period=24)
    assert r.shape == ctx.close.shape
    # 前 68 期 NaN
    assert r.iloc[:68].isna().all().all()
    assert not r.iloc[69].isna().all()


def test_alpha_183_direction():
    assert ALPHA183_DIRECTION == 1


# ---------------- Alpha #188 ----------------

def test_alpha_188_basic():
    ctx = _make_ctx(n=30)
    r = alpha_188(ctx)
    assert r.shape == ctx.close.shape
    # SMA 预热期较短，但建议至少 11 期
    assert not r.iloc[-1].isna().all()


def test_alpha_188_direction():
    assert ALPHA188_DIRECTION == 1


# ---------------- Alpha #189 ----------------

def test_alpha_189_basic():
    ctx = _make_ctx(n=30)
    r = alpha_189(ctx)
    assert r.shape == ctx.close.shape
    # 前 11 期 NaN (MA6 + mean6 - 1)
    assert r.iloc[:10].isna().all().all()
    assert not r.iloc[11].isna().all()


def test_alpha_189_direction():
    assert ALPHA189_DIRECTION == 1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_076",
        "quantlab.factors.alpha191.alpha_137",
        "quantlab.factors.alpha191.alpha_158",
        "quantlab.factors.alpha191.alpha_161",
        "quantlab.factors.alpha191.alpha_165",
        "quantlab.factors.alpha191.alpha_175",
        "quantlab.factors.alpha191.alpha_183",
        "quantlab.factors.alpha191.alpha_188",
        "quantlab.factors.alpha191.alpha_189",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import sys

    mod = sys.modules.get(modname)
    if mod is None:
        import importlib

        mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
