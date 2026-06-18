"""
Validation Center — 验证中心

ML Lab M3：模型验证全流程

  M3 第一部分：Walk Forward Engine     — 滚动验证，避免随机切分
  M3 第二部分：Leakage Detector         — 数据泄漏检测（见 ml.leakage）
  M3 第三部分：Stability Analyzer       — 年度稳定性分析
  M3 第四部分：Regime Validator         — 牛/熊/震荡市场验证
  M3 第五部分：Robustness Tester        — 参数扰动抗过拟合
  M3 第六部分：Noise Tester             — 噪音注入测试
  M3 第七部分：Benchmark Engine         — vs Buy&Hold/Momentum/Random
  M3 第八部分：Validation Report        — 汇总评分 0~100
"""

from .walk_forward import (
    WalkForward, WalkForwardEngine,
    ValidationConfig, WalkForwardResult,
)
from .stability import StabilityAnalyzer, StabilityResult, YearlyStat
from .regime import RegimeValidator, RegimeResult, RegimeStat, MarketRegime
from .robustness import RobustnessTester, RobustnessResult, PerturbationResult
from .noise import NoiseTester, NoiseTestResult, NoiseTestItem
from .benchmark import BenchmarkEngine, BenchmarkReport, BenchmarkResult
from .report import (
    ValidationReport, ValidationItem, ValidationStatus,
    build_validation_report,
)

__all__ = [
    # Walk Forward
    "WalkForward",
    "WalkForwardEngine",
    "ValidationConfig",
    "WalkForwardResult",
    # Stability
    "StabilityAnalyzer",
    "StabilityResult",
    "YearlyStat",
    # Regime
    "RegimeValidator",
    "RegimeResult",
    "RegimeStat",
    "MarketRegime",
    # Robustness
    "RobustnessTester",
    "RobustnessResult",
    "PerturbationResult",
    # Noise
    "NoiseTester",
    "NoiseTestResult",
    "NoiseTestItem",
    # Benchmark
    "BenchmarkEngine",
    "BenchmarkReport",
    "BenchmarkResult",
    # Report
    "ValidationReport",
    "ValidationItem",
    "ValidationStatus",
    "build_validation_report",
]
