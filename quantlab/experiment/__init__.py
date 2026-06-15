"""
V4.4 Experiment Management

实验管理是研究平台真正的核心。

模块：
  artifact   ExperimentArtifact（equity/trades/orders/report 落盘）
  registry   ExperimentRegistry（注册/索引/查找）
  search     ExperimentSearch（多维度搜索/排名）
  compare    ExperimentComparer（指标对比+权益曲线叠加）
  report     ReportGenerator（HTML/Markdown 报告）
  tags       TagManager（标签系统）
"""

from .artifact import ExperimentArtifact
from .registry import ExperimentRegistry
from .search import ExperimentSearch
from .compare import ExperimentComparer
from .report import ReportGenerator
from .tags import TagManager, BUILTIN_TAGS


__all__ = [
    "ExperimentArtifact",
    "ExperimentRegistry",
    "ExperimentSearch",
    "ExperimentComparer",
    "ReportGenerator",
    "TagManager",
    "BUILTIN_TAGS",
]
