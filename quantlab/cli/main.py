"""
QuantLab CLI 主入口
===================

使用 argparse 实现，支持子命令扩展。

当前可用子命令：
    trading  — 统一交易核心（backtest / paper / live）

用法：
    python main.py --help
    python main.py trading --help
    python main.py trading --status --mode paper --capital 1000000
    python main.py trading --run-backtest data/bars.csv --symbols 000001.SZ
"""
from __future__ import annotations

import argparse

from .trading_cli import add_trading_subparser


def create_parser() -> argparse.ArgumentParser:
    """创建顶层 argparse 解析器，挂载所有子命令。

    Returns:
        argparse.ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog="quantlab",
        description="QuantLab 量化交易平台",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    # 注册 trading 子命令
    add_trading_subparser(subparsers)
    return parser


def main() -> int:
    """CLI 主入口：解析参数并分发到对应子命令处理函数。"""
    parser = create_parser()
    args = parser.parse_args()

    # 通过 func 回调分发（各子命令在 set_defaults 中绑定 func）
    func = getattr(args, "func", None)
    if func is not None:
        func(args)
        return 0

    # 未指定子命令时打印帮助
    parser.print_help()
    return 0


if __name__ == "__main__":
    main()
