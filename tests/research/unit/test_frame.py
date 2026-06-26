"""
ResearchFrame 单元测试
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.research.frame import ResearchFrame


def _make_panel_df(n_dates=5, symbols=("BTC", "ETH")) -> pd.DataFrame:
    """构造 (datetime, symbol) MultiIndex 的 OHLCV DataFrame。"""
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="D")
    rows = []
    for dt in dates:
        for sym in symbols:
            rows.append({
                "datetime": dt,
                "symbol": sym,
                "open": 100.0,
                "high": 105.0,
                "low": 95.0,
                "close": float(np.random.rand() * 10 + 100),
                "volume": 1000.0,
            })
    df = pd.DataFrame(rows)
    df.set_index(["datetime", "symbol"], inplace=True)
    return df


def _make_single_symbol_df(n_dates=5) -> pd.DataFrame:
    """构造单标的 DatetimeIndex DataFrame。"""
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="D")
    return pd.DataFrame(
        {"close": [100.0, 101.0, 102.0, 103.0, 104.0]},
        index=dates,
    )


class TestResearchFrameConstruction:
    def test_from_panel_multiindex(self):
        df = _make_panel_df()
        rf = ResearchFrame.from_panel(df, name="ohlcv")
        assert rf.name == "ohlcv"
        assert isinstance(rf.data.index, pd.MultiIndex)
        assert rf.data.index.names == ["datetime", "symbol"]
        assert set(rf.symbols) == {"BTC", "ETH"}
        assert len(rf.datetimes) == 5

    def test_from_ohlcv_multiindex(self):
        df = _make_panel_df()
        rf = ResearchFrame.from_ohlcv(df)
        assert rf.data.index.names == ["datetime", "symbol"]

    def test_from_ohlcv_datetimeindex(self):
        """DatetimeIndex 自动补 symbol='default'。"""
        df = _make_single_symbol_df()
        rf = ResearchFrame.from_ohlcv(df, name="btc_close")
        assert isinstance(rf.data.index, pd.MultiIndex)
        assert rf.data.index.names == ["datetime", "symbol"]
        assert rf.symbols == ["default"]
        assert rf.name == "btc_close"

    def test_from_single_symbol(self):
        df = _make_single_symbol_df()
        rf = ResearchFrame.from_single_symbol(df, symbol="BTC")
        assert rf.symbols == ["BTC"]
        assert len(rf.datetimes) == 5

    def test_invalid_index_raises(self):
        df = pd.DataFrame({"close": [1, 2, 3]})  # 默认 RangeIndex
        with pytest.raises(ValueError, match="MultiIndex"):
            ResearchFrame(data=df)

    def test_empty_columns_meta(self):
        df = _make_panel_df()
        rf = ResearchFrame.from_panel(df)
        assert rf.columns_meta == {}


class TestResearchFrameDegradation:
    def test_as_time_series(self):
        df = _make_panel_df(symbols=("BTC", "ETH"))
        rf = ResearchFrame.from_panel(df)
        ts = rf.as_time_series("BTC")
        assert isinstance(ts, pd.DataFrame)
        assert len(ts) == 5
        assert "close" in ts.columns

    def test_as_time_series_missing_symbol(self):
        df = _make_panel_df(symbols=("BTC", "ETH"))
        rf = ResearchFrame.from_panel(df)
        with pytest.raises(KeyError):
            rf.as_time_series("SOL")

    def test_as_cross_section(self):
        df = _make_panel_df(symbols=("BTC", "ETH"))
        rf = ResearchFrame.from_panel(df)
        dt = rf.datetimes[0]
        cs = rf.as_cross_section(dt)
        assert isinstance(cs, pd.DataFrame)
        assert len(cs) == 2  # BTC + ETH


class TestResearchFrameProperties:
    def test_symbols(self):
        df = _make_panel_df(symbols=("BTC", "ETH", "SOL"))
        rf = ResearchFrame.from_panel(df)
        assert set(rf.symbols) == {"BTC", "ETH", "SOL"}

    def test_columns(self):
        df = _make_panel_df()
        rf = ResearchFrame.from_panel(df)
        assert "close" in rf.columns
        assert "volume" in rf.columns

    def test_shape_and_len(self):
        df = _make_panel_df(n_dates=5, symbols=("BTC", "ETH"))
        rf = ResearchFrame.from_panel(df)
        assert rf.shape == (10, 5)  # 5 dates * 2 symbols, 5 cols
        assert len(rf) == 10

    def test_to_dict(self):
        df = _make_panel_df(symbols=("BTC",))
        rf = ResearchFrame.from_panel(df, name="btc")
        d = rf.to_dict()
        assert d["name"] == "btc"
        assert "BTC" in d["symbols"]
        assert "close" in d["columns"]

    def test_repr(self):
        df = _make_panel_df()
        rf = ResearchFrame.from_panel(df, name="ohlcv")
        s = repr(rf)
        assert "ResearchFrame" in s
        assert "ohlcv" in s
