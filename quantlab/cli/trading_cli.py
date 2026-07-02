"""
Trading CLI — 统一交易核心子命令
===============================

子命令：trading
    --mode          运行模式（backtest / paper / live，默认 paper）
    --capital       初始资金（默认 1,000,000）
    --status        查看账户状态
    --positions     查看持仓
    --orders        查看订单
    --run-backtest  用CSV历史数据运行回测（列：date,open,high,low,close,volume）
    --strategy      策略ID（默认 demo）
    --symbols       交易标的（默认 000001.SZ）
    --bar-csv       单标的K线CSV文件路径（用于回测，等同 --run-backtest）

回测流程：
    1. pandas 读取 CSV
    2. 创建 BacktestMode + TradingCore
    3. 部署内置 DemoStrategy
    4. 逐行构造 Bar，调用 core.on_bar(bar)
    5. 打印总资产 / 现金 / 持仓 / 收益率
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import List

import pandas as pd

from quantlab.trading_core import (
    Bar,
    EventStrategy,
    OrderIntent,
    TradingCore,
)
from quantlab.trading_core.modes import BacktestMode, PaperMode


class DemoStrategy(EventStrategy):
    """演示策略：第一天全仓买入 100 股，之后持有。

    用于 --run-backtest 回测验证，证明 TradingCore 全链路可用。
    """

    name = "demo"
    version = "1.0"

    def __init__(self) -> None:
        self._bought = False

    def on_init(self) -> None:
        return None

    def on_exit(self, ctx) -> List[OrderIntent]:
        return []

    def on_bar(self, bar: Bar, ctx) -> List[OrderIntent]:
        # 尚未买入且现金足够买 100 股，则市价买入
        if not self._bought and ctx.cash > bar.close * 100:
            self._bought = True
            return [
                OrderIntent(
                    symbol=bar.symbol,
                    side="buy",
                    quantity=100,
                    order_type="market",
                    reason="demo_buy",
                )
            ]
        return []


def add_trading_subparser(subparsers: "argparse._SubParsersAction") -> None:
    """注册 trading 子命令到顶层 subparsers。"""
    parser = subparsers.add_parser("trading", help="统一交易核心")
    parser.add_argument(
        "--mode",
        choices=["backtest", "paper", "live"],
        default="paper",
        help="运行模式（默认 paper）",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=1_000_000,
        help="初始资金（默认 1000000）",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="查看账户状态",
    )
    parser.add_argument(
        "--positions",
        action="store_true",
        help="查看持仓",
    )
    parser.add_argument(
        "--orders",
        action="store_true",
        help="查看订单",
    )
    parser.add_argument(
        "--run-backtest",
        metavar="CSV_PATH",
        dest="run_backtest",
        help="用CSV历史数据运行回测（列：date,open,high,low,close,volume）",
    )
    parser.add_argument(
        "--strategy",
        default="demo",
        help="策略ID（默认 demo）",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=["000001.SZ"],
        help="交易标的（默认 000001.SZ）",
    )
    parser.add_argument(
        "--bar-csv",
        dest="bar_csv",
        help="单标的K线CSV文件路径（用于回测，等同 --run-backtest）",
    )
    parser.set_defaults(func=handle_trading)


def _create_core(mode: str, capital: float) -> TradingCore:
    """根据模式创建 TradingCore 实例。

    Args:
        mode: 运行模式（backtest / paper / live）
        capital: 初始资金

    Returns:
        TradingCore 实例
    """
    if mode == "backtest":
        trading_mode = BacktestMode()
    elif mode == "live":
        # live 暂未接入真实券商，以 PaperMode 兜底
        trading_mode = PaperMode()
    else:
        trading_mode = PaperMode()
    return TradingCore(trading_mode, initial_capital=capital)


def _print_account(core: TradingCore) -> None:
    """打印账户状态。"""
    account = core.get_account()
    print("=" * 56)
    print("账户状态")
    print("=" * 56)
    print(f"模式:         {core.mode.name}")
    print(f"初始资金:     {account['initial_capital']:,.2f}")
    print(f"现金:         {account['cash']:,.2f}")
    print(f"总资产:       {account['equity']:,.2f}")
    print(f"持仓市值:     {account['invested_value']:,.2f}")
    print(f"已实现盈亏:   {account['realized_pnl']:,.2f}")
    print(f"未实现盈亏:   {account['unrealized_pnl']:,.2f}")
    print(f"总盈亏:       {account['total_pnl']:,.2f}")
    print(f"总收益率:     {account['total_return'] * 100:.2f}%")
    print(f"持仓数量:     {account['n_open_positions']}")
    print(f"最大回撤:     {account['max_drawdown'] * 100:.2f}%")
    print("=" * 56)


def _print_positions(core: TradingCore) -> None:
    """打印持仓明细。"""
    positions = core.get_positions()
    print("=" * 76)
    print("持仓明细")
    print("=" * 76)
    if not positions:
        print("（无持仓）")
    else:
        header = (
            f"{'标的':<12}{'方向':>6}{'数量':>12}{'均价':>12}"
            f"{'现价':>12}{'市值':>14}{'浮盈':>14}"
        )
        print(header)
        print("-" * 76)
        for p in positions:
            qty = float(p.get("qty", 0))
            avg_price = float(p.get("avg_price", 0))
            market_price = float(p.get("market_price", 0))
            value = qty * market_price
            pnl = float(p.get("unrealized_pnl", 0))
            print(
                f"{str(p.get('symbol','')):<12}{str(p.get('side','')):>6}"
                f"{qty:>12.2f}{avg_price:>12.4f}{market_price:>12.4f}"
                f"{value:>14.2f}{pnl:>14.2f}"
            )
    print("=" * 76)


def _print_orders(core: TradingCore) -> None:
    """打印订单列表。"""
    orders = core.get_orders()
    print("=" * 86)
    print("订单列表")
    print("=" * 86)
    if not orders:
        print("（无订单）")
    else:
        header = (
            f"{'订单ID':<22}{'标的':<12}{'方向':>6}{'数量':>10}"
            f"{'类型':>8}{'状态':>12}{'成交价':>12}"
        )
        print(header)
        print("-" * 86)
        for o in orders:
            print(
                f"{str(o.get('id','')):<22}{str(o.get('symbol','')):<12}"
                f"{str(o.get('side','')):>6}{float(o.get('quantity',0)):>10.2f}"
                f"{str(o.get('order_type','')):>8}{str(o.get('state','')):>12}"
                f"{float(o.get('avg_fill_price',0) or 0):>12.4f}"
            )
    print("=" * 86)


def _run_backtest(args) -> None:
    """用 CSV 历史数据运行回测并打印结果。"""
    # --run-backtest 与 --bar-csv 均可指定 CSV，前者优先
    csv_path = args.run_backtest or args.bar_csv
    if not csv_path:
        print("错误：--run-backtest 需要指定 CSV 文件路径")
        return
    if not os.path.exists(csv_path):
        print(f"错误：CSV 文件不存在: {csv_path}")
        return

    # 1. 读取 CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"读取 CSV 失败: {e}")
        return

    required = {"date", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        print(f"错误：CSV 缺少必要列，需要: {sorted(required)}，实际: {sorted(df.columns)}")
        return

    symbol = args.symbols[0] if args.symbols else "000001.SZ"
    capital = args.capital

    # 2. 创建 BacktestMode + TradingCore（回测强制使用 backtest 模式）
    mode = BacktestMode()
    core = TradingCore(mode, initial_capital=capital)

    # 3. 部署内置 DemoStrategy
    strategy = DemoStrategy()
    core.deploy_strategy(args.strategy, strategy, symbols=[symbol])

    # 4. 逐行构造 Bar 并驱动核心
    n = 0
    for _, row in df.iterrows():
        try:
            ts = pd.to_datetime(row["date"])
        except Exception:
            ts = datetime.now()
        bar = Bar(
            timestamp=ts,
            symbol=symbol,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        core.on_bar(bar)
        n += 1

    # 5. 打印回测结果
    print("=" * 60)
    print(f"回测完成 — 共处理 {n} 根K线（标的: {symbol}）")
    print("=" * 60)
    _print_account(core)
    _print_positions(core)
    print("=" * 60)


def handle_trading(args) -> None:
    """处理 trading 子命令：根据 args 分发到对应操作。"""
    # 回测优先（会部署策略并运行，强制 backtest 模式）
    if args.run_backtest or args.bar_csv:
        _run_backtest(args)
        return

    # 查询类命令：初始化 TradingCore 后展示对应信息
    core = _create_core(args.mode, args.capital)

    if args.status:
        _print_account(core)
    if args.positions:
        _print_positions(core)
    if args.orders:
        _print_orders(core)

    # 无任何操作时给出提示
    if not any([args.status, args.positions, args.orders]):
        print("QuantLab 统一交易核心")
        print(f"模式: {args.mode}  初始资金: {args.capital:,.2f}")
        print("提示：使用 --status / --positions / --orders 查看状态，")
        print("      使用 --run-backtest CSV_PATH 运行回测。")
