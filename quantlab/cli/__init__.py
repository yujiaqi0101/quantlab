"""QuantLab CLI — 统一命令行入口包。

导出 create_parser / main 供外部调用，例如：
    from quantlab.cli import create_parser, main
"""
from __future__ import annotations

from .main import create_parser, main

__all__ = ["create_parser", "main"]
