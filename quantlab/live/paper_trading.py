"""
V3.1：旧文件改 re-export
  实际定义已迁移到 live/broker/paper_broker.py
  这个文件保持向后兼容
"""
from .broker.paper_broker import (
    PaperBroker,
)

__all__ = ["PaperBroker"]
