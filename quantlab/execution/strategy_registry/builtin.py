"""
Builtin Strategies — 内置策略目录

T1 第九模块：本地策略目录

  RSI Strategy
  Momentum Strategy
  LGBM Strategy
  MA Cross Strategy
  Portfolio Rotation
"""

from __future__ import annotations

from typing import List

from .registry import (
    StrategyInfo,
    StrategyParameter,
    StrategyRegistry,
)


def _rsi_strategy() -> StrategyInfo:
    return StrategyInfo(
        strategy_id="rsi",
        name="RSI Strategy",
        description="RSI 超买超卖策略：RSI < 30 买入，RSI > 70 卖出",
        category="mean_reversion",
        tags=["rsi", "mean_reversion", "classic"],
        parameters=[
            StrategyParameter(
                name="period",
                type="int",
                default=14,
                min=2,
                max=100,
                description="RSI 周期",
            ),
            StrategyParameter(
                name="oversold",
                type="float",
                default=30.0,
                min=0.0,
                max=50.0,
                description="超卖阈值",
            ),
            StrategyParameter(
                name="overbought",
                type="float",
                default=70.0,
                min=50.0,
                max=100.0,
                description="超买阈值",
            ),
        ],
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="1h",
        author="QuantLab",
        version="1.0.0",
    )


def _momentum_strategy() -> StrategyInfo:
    return StrategyInfo(
        strategy_id="momentum",
        name="Momentum Strategy",
        description="动量策略：过去 N 天涨幅最高的标的",
        category="momentum",
        tags=["momentum", "trend", "classic"],
        parameters=[
            StrategyParameter(
                name="lookback",
                type="int",
                default=20,
                min=1,
                max=250,
                description="回看周期（天）",
            ),
            StrategyParameter(
                name="holdings",
                type="int",
                default=3,
                min=1,
                max=20,
                description="持有标的数量",
            ),
            StrategyParameter(
                name="rebalance_freq",
                type="choice",
                default="weekly",
                choices=["daily", "weekly", "monthly"],
                description="调仓频率",
            ),
        ],
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
        timeframe="1d",
        author="QuantLab",
        version="1.0.0",
    )


def _lgbm_strategy() -> StrategyInfo:
    return StrategyInfo(
        strategy_id="lgbm_trend",
        name="LGBM Trend Strategy",
        description="LightGBM 趋势预测策略：基于多因子特征预测下一期收益方向",
        category="ml",
        tags=["lgbm", "ml", "trend", "advanced"],
        parameters=[
            StrategyParameter(
                name="n_estimators",
                type="int",
                default=100,
                min=10,
                max=1000,
                description="树的数量",
            ),
            StrategyParameter(
                name="max_depth",
                type="int",
                default=6,
                min=1,
                max=20,
                description="最大深度",
            ),
            StrategyParameter(
                name="learning_rate",
                type="float",
                default=0.05,
                min=0.001,
                max=1.0,
                description="学习率",
            ),
            StrategyParameter(
                name="feature_window",
                type="int",
                default=30,
                min=5,
                max=200,
                description="特征窗口（天）",
            ),
        ],
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="1h",
        author="QuantLab",
        version="1.0.0",
    )


def _ma_cross_strategy() -> StrategyInfo:
    return StrategyInfo(
        strategy_id="ma_cross",
        name="MA Cross Strategy",
        description="均线交叉策略：快线上穿慢线买入，下穿卖出",
        category="trend",
        tags=["ma", "trend", "classic"],
        parameters=[
            StrategyParameter(
                name="fast",
                type="int",
                default=20,
                min=2,
                max=200,
                description="快线周期",
            ),
            StrategyParameter(
                name="slow",
                type="int",
                default=60,
                min=10,
                max=500,
                description="慢线周期",
            ),
        ],
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="1h",
        author="QuantLab",
        version="1.0.0",
    )


def _portfolio_rotation_strategy() -> StrategyInfo:
    return StrategyInfo(
        strategy_id="portfolio_rotation",
        name="Portfolio Rotation",
        description="组合轮动策略：基于动量 + 波动率的风险平价轮动",
        category="portfolio",
        tags=["portfolio", "rotation", "risk_parity"],
        parameters=[
            StrategyParameter(
                name="rebalance_freq",
                type="choice",
                default="monthly",
                choices=["weekly", "monthly", "quarterly"],
                description="调仓频率",
            ),
            StrategyParameter(
                name="max_weight",
                type="float",
                default=0.4,
                min=0.1,
                max=1.0,
                description="单标的最大权重",
            ),
            StrategyParameter(
                name="vol_lookback",
                type="int",
                default=20,
                min=5,
                max=100,
                description="波动率回看周期",
            ),
        ],
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"],
        timeframe="1d",
        author="QuantLab",
        version="1.0.0",
    )


def register_all_builtin(reg: StrategyRegistry) -> int:
    """注册所有内置策略"""
    builtins = [
        _rsi_strategy(),
        _momentum_strategy(),
        _lgbm_strategy(),
        _ma_cross_strategy(),
        _portfolio_rotation_strategy(),
    ]
    for info in builtins:
        reg.register(info)
    return len(builtins)
