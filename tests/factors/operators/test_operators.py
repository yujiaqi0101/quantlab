"""
算子库单元测试
==============

每个算子用构造数据 + numpy 交叉验证。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.operators.ts import (
    delay, delta, ts_rank, ts_max, ts_min,
    ts_argmax, ts_argmin, ts_sum, ts_mean, ts_std, product,
)
from quantlab.factors.operators.cross_section import rank, scale
from quantlab.factors.operators.stats import corr, cov
from quantlab.factors.operators.smooth import decay_linear, sma, wma
from quantlab.factors.operators.regression import regbeta
from quantlab.factors.operators.misc import (
    signed_power, sum_if, cumsum, highday, lowday, sequence,
)


def _panel(rows, cols=("A", "B")):
    dates = pd.date_range("2026-01-05", periods=len(rows), freq="B")
    arr = np.array(rows, dtype=float)
    # 一维输入广播到所有列
    if arr.ndim == 1:
        arr = np.tile(arr.reshape(-1, 1), (1, len(cols)))
    return pd.DataFrame(arr, index=dates, columns=list(cols))


# ---------------- 时序算子 ----------------

def test_delay():
    df = _panel([1, 2, 3, 4, 5])
    r = delay(df, 2)
    assert r.iloc[0].isna().all()
    assert r.iloc[1].isna().all()
    assert r.iloc[2, 0] == 1
    assert r.iloc[4, 0] == 3


def test_delay_negative_raises():
    df = _panel([1, 2, 3])
    with pytest.raises(ValueError):
        delay(df, -1)


def test_delta():
    df = _panel([10, 11, 12, 13, 14])
    r = delta(df, 1)
    assert r.iloc[0].isna().all()
    assert r.iloc[1, 0] == 1
    assert r.iloc[4, 0] == 1


def test_ts_rank():
    # 5 期递增序列，最近一期最大 → rank=1.0
    df = _panel([1, 2, 3, 4, 5])
    r = ts_rank(df, 5)
    assert r.iloc[4, 0] == pytest.approx(1.0)
    # 前面不足 5 期为 NaN
    assert r.iloc[3].isna().all()


def test_ts_rank_min_is_low():
    # 5 期递减，最近最小 → rank=0.2
    df = _panel([5, 4, 3, 2, 1])
    r = ts_rank(df, 5)
    assert r.iloc[4, 0] == pytest.approx(0.2)


def test_ts_max():
    df = _panel([1, 3, 2, 5, 4])
    r = ts_max(df, 3)
    assert r.iloc[2, 0] == 3
    assert r.iloc[3, 0] == 5
    assert r.iloc[4, 0] == 5


def test_ts_min():
    df = _panel([1, 3, 2, 5, 4])
    r = ts_min(df, 3)
    assert r.iloc[2, 0] == 1
    assert r.iloc[4, 0] == 2


def test_ts_argmax():
    # 最近一期是最大 → 位置 0
    df = _panel([1, 2, 3, 4, 5])
    r = ts_argmax(df, 5)
    assert r.iloc[4, 0] == 0
    # 最远一期最大 → 位置 4
    df2 = _panel([5, 4, 3, 2, 1])
    r2 = ts_argmax(df2, 5)
    assert r2.iloc[4, 0] == 4


def test_ts_argmin():
    df = _panel([1, 2, 3, 4, 5])
    r = ts_argmin(df, 5)
    assert r.iloc[4, 0] == 4  # 最远一期最小


def test_ts_sum():
    df = _panel([1, 2, 3, 4, 5])
    r = ts_sum(df, 3)
    assert r.iloc[2, 0] == 6
    assert r.iloc[4, 0] == 12


def test_ts_mean_vs_numpy():
    arr = np.random.default_rng(7).uniform(0, 100, (20, 3))
    df = _panel(arr, cols=("A", "B", "C"))
    r = ts_mean(df, 5)
    # 逐列对比 numpy
    for j, col in enumerate(df.columns):
        expected = pd.Series(arr[:, j]).rolling(5).mean().values
        np.testing.assert_allclose(r[col].values, expected, equal_nan=True)


def test_ts_std_ddof1():
    df = _panel([1, 2, 3, 4, 5])
    r = ts_std(df, 3)
    # 样本标准差 ddof=1
    expected = np.std([1, 2, 3], ddof=1)
    assert r.iloc[2, 0] == pytest.approx(expected)


def test_product():
    df = _panel([1, 2, 3, 4, 5])
    r = product(df, 3)
    assert r.iloc[2, 0] == 6   # 1*2*3
    assert r.iloc[4, 0] == 60  # 3*4*5


# ---------------- 截面算子 ----------------

def test_rank():
    df = _panel([[1, 2], [3, 4], [5, 6]])
    r = rank(df)
    # 每行 A<B → A 的 pct rank 应 < B
    assert (r.iloc[:, 0] < r.iloc[:, 1]).all()


def test_scale():
    df = _panel([[3, -1], [2, -2]])
    r = scale(df, 1.0)
    # 每行 abs 和应为 1
    np.testing.assert_allclose(r.abs().sum(axis=1).values, 1.0)


def test_scale_zero_row():
    df = _panel([[0, 0], [1, 2]])
    r = scale(df, 1.0)
    # 全零行应为 NaN
    assert r.iloc[0].isna().all()
    np.testing.assert_allclose(r.abs().sum(axis=1).iloc[1], 1.0)


# ---------------- 统计算子 ----------------

def test_corr_against_numpy():
    rng = np.random.default_rng(11)
    a = rng.uniform(0, 100, (20, 2))
    b = rng.uniform(0, 100, (20, 2))
    df_x = _panel(a)
    df_y = _panel(b)
    r = corr(df_x, df_y, 5)
    # 与 numpy 逐列对比最后一行
    for j, col in enumerate(df_x.columns):
        win_x = a[-5:, j]
        win_y = b[-5:, j]
        expected = np.corrcoef(win_x, win_y)[0, 1]
        assert r[col].iloc[-1] == pytest.approx(expected, abs=1e-9)


def test_cov_against_numpy():
    rng = np.random.default_rng(13)
    a = rng.uniform(0, 100, (20, 2))
    b = rng.uniform(0, 100, (20, 2))
    df_x = _panel(a)
    df_y = _panel(b)
    r = cov(df_x, df_y, 5)
    for j, col in enumerate(df_x.columns):
        win_x = a[-5:, j]
        win_y = b[-5:, j]
        expected = np.cov(win_x, win_y, ddof=1)[0, 1]
        assert r[col].iloc[-1] == pytest.approx(expected, abs=1e-9)


# ---------------- 平滑算子 ----------------

def test_decay_linear_weights():
    df = _panel([1, 2, 3])
    r = decay_linear(df, 3)
    # 权重 (3,2,1)/6 → (3*3+2*2+1*1)/6 = 14/6
    assert r.iloc[2, 0] == pytest.approx(14 / 6)


def test_sma_alpha():
    # alpha=m/n=1/3
    df = _panel([1, 2, 3, 4, 5])
    r = sma(df, 3, 1)
    # 用 pandas ewm 验证
    expected = df.ewm(alpha=1 / 3, adjust=False).mean()
    pd.testing.assert_frame_equal(r, expected)


def test_wma_equals_decay_linear():
    df = _panel([[1, 2], [3, 4], [5, 6]])
    a = wma(df, 3)
    b = decay_linear(df, 3)
    pd.testing.assert_frame_equal(a, b)


# ---------------- 回归算子 ----------------

def test_regbeta_perfect_linear():
    """y = 2*x + 5 → beta = 2。"""
    x = _panel([1, 2, 3, 4, 5, 6])
    y = (2 * x) + 5
    r = regbeta(y, x, n=5)
    # 前 n-1=4 期为 NaN
    assert r.iloc[:4].isna().all().all()
    # 第 5 期开始, beta≈2
    assert r.iloc[4, 0] == pytest.approx(2.0, abs=1e-9)
    assert r.iloc[5, 0] == pytest.approx(2.0, abs=1e-9)


def test_regbeta_negative_slope():
    """y = -3*x → beta = -3。"""
    x = _panel([1, 2, 3, 4, 5])
    y = -3 * x
    r = regbeta(y, x, n=4)
    assert r.iloc[3, 0] == pytest.approx(-3.0, abs=1e-9)


def test_regbeta_zero_variance_returns_nan():
    """x 恒定 → 方差 0 → beta = NaN。"""
    x = _panel([5, 5, 5, 5, 5])
    y = _panel([1, 2, 3, 4, 5])
    r = regbeta(y, x, n=4)
    assert np.isnan(r.iloc[3, 0])


def test_regbeta_short_window_raises():
    x = _panel([1, 2, 3])
    y = _panel([1, 2, 3])
    with pytest.raises(ValueError):
        regbeta(y, x, n=1)


# ---------------- 工具算子 ----------------

def test_signed_power_positive():
    df = _panel([2, 3, 4])
    r = signed_power(df, 2)
    assert r.iloc[0, 0] == 4
    assert r.iloc[1, 0] == 9
    assert r.iloc[2, 0] == 16


def test_signed_power_keeps_sign():
    df = _panel([-2, 3, -4])
    r = signed_power(df, 3)
    assert r.iloc[0, 0] == -8
    assert r.iloc[1, 0] == 27
    assert r.iloc[2, 0] == -64


def test_signed_power_fraction():
    df = _panel([4, 9])
    r = signed_power(df, 0.5)
    assert r.iloc[0, 0] == 2.0
    assert r.iloc[1, 0] == 3.0


def test_sum_if():
    x = _panel([10, 20, 30, 40, 50])
    # 仅奇数行 cond=1
    cond = _panel([0, 1, 0, 1, 0])
    r = sum_if(x, cond, n=3)
    # 窗口 [10,20,30] 取 20; [20,30,40] 取 20+40=60; [30,40,50] 取 40
    assert r.iloc[2, 0] == 20
    assert r.iloc[3, 0] == 60
    assert r.iloc[4, 0] == 40


def test_cumsum():
    df = _panel([1, 2, 3, 4])
    r = cumsum(df)
    assert r.iloc[0, 0] == 1
    assert r.iloc[1, 0] == 3
    assert r.iloc[2, 0] == 6
    assert r.iloc[3, 0] == 10


def test_highday_max_at_today():
    # 末值最大 → 0
    df = _panel([1, 2, 3, 4, 5])
    r = highday(df, 5)
    assert r.iloc[4, 0] == 0


def test_highday_max_at_oldest():
    # 首值最大 → n-1
    df = _panel([5, 4, 3, 2, 1])
    r = highday(df, 5)
    assert r.iloc[4, 0] == 4


def test_lowday_min_at_today():
    df = _panel([5, 4, 3, 2, 1])
    r = lowday(df, 5)
    assert r.iloc[4, 0] == 0


def test_lowday_min_at_oldest():
    df = _panel([1, 2, 3, 4, 5])
    r = lowday(df, 5)
    assert r.iloc[4, 0] == 4


def test_sequence():
    s = sequence(5)
    assert list(s) == [1, 2, 3, 4, 5]


def test_sequence_invalid():
    with pytest.raises(ValueError):
        sequence(0)
