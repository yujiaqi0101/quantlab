"""
Alpha Factory — V3.0 量化研究平台核心

Alpha ≠ Strategy。Alpha 是预测信号，是专业量化研究的核心对象。

三级模型扩展：
  Factor → Alpha → Strategy

  Factor: 连续值（RSI=45.3）
  Alpha:  因子 + 信号规则的组合（RSI < 30 → 做多）
  Strategy: 多 Alpha 组合 + 风控 + 仓位管理

目录：
  alpha.py       Alpha / AlphaMetrics 数据模型
  generator.py   AlphaGenerator — 从因子批量生成 Alpha
  evaluator.py   AlphaEvaluator — 自动计算 IC/IR/Coverage/Turnover
  store.py       AlphaStore — SQLite 持久化
  ranking.py     AlphaRanking — 评分排序
  pool.py        CandidatePool — 候选池筛选
  correlation.py AlphaCorrelation — 相关性矩阵
  decay.py       AlphaDecay — 信号衰减分析
  combiner.py    AlphaCombiner — Alpha 组合
  portfolio.py   AlphaPortfolio — 组合构建
  report.py      AlphaReport — 分析报告
"""

from .alpha import Alpha, AlphaMetrics, AlphaRecord, AlphaStatus
from .generator import AlphaGenerator
from .evaluator import AlphaEvaluator
from .store import AlphaStore
from .ranking import AlphaRanking
from .pool import CandidatePool
from .correlation import AlphaCorrelation
from .decay import AlphaDecay
from .combiner import AlphaCombiner
from .portfolio import AlphaPortfolio

__all__ = [
    "Alpha", "AlphaMetrics", "AlphaRecord", "AlphaStatus",
    "AlphaGenerator",
    "AlphaEvaluator",
    "AlphaStore",
    "AlphaRanking",
    "CandidatePool",
    "AlphaCorrelation",
    "AlphaDecay",
    "AlphaCombiner",
    "AlphaPortfolio",
]
