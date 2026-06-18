"""
M3 端到端验证测试

模拟完整验证流程：
  1. 生成合成数据（含时间序列）
  2. Walk Forward 验证
  3. Leakage 检测
  4. Stability 分析
  5. Regime 验证
  6. Robustness 测试
  7. Noise 测试
  8. Benchmark 对比
  9. 汇总 Validation Report
"""

import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 添加项目根目录
sys.path.insert(0, ".")

from quantlab.ml.validation import (
    WalkForwardEngine, ValidationConfig,
    StabilityAnalyzer, RegimeValidator,
    RobustnessTester, NoiseTester,
    BenchmarkEngine, build_validation_report,
)
from quantlab.ml.leakage import LeakageDetector, FeatureLeakageScanner
from quantlab.ml.model import ModelType, create_model


def make_synthetic_data(n_days: int = 1000, seed: int = 42):
    """生成合成数据：3 个特征 + 1 个标签"""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")

    # 三个特征，其中 feature_1 有真实预测力
    feature_1 = pd.Series(rng.randn(n_days).cumsum() * 0.01, index=dates, name="feat_1")
    feature_2 = pd.Series(rng.randn(n_days), index=dates, name="feat_2")
    feature_3 = pd.Series(rng.randn(n_days), index=dates, name="feat_3")

    # 标签：与 feature_1 有相关性 + 噪音
    label = feature_1.shift(-1) * 0.5 + pd.Series(rng.randn(n_days) * 0.01, index=dates)
    label.name = "label"

    features = pd.concat([feature_1, feature_2, feature_3], axis=1)
    # 用前向填充避免 NaN
    features = features.ffill().fillna(0)
    label = label.fillna(0)

    return features, label


def test_walk_forward(features, label):
    """测试 Walk Forward"""
    print("\n=== 1. Walk Forward Engine ===")
    config = ValidationConfig(
        n_splits=3,
        train_size=500,
        test_size=100,
        step_size=100,
        gap=5,
    )
    engine = WalkForwardEngine(config)
    result = engine.run(
        features=features,
        label=label,
        model_type=ModelType.LINEAR_REGRESSION,
    )
    print(f"  n_splits: {result.n_splits}")
    print(f"  avg_ic: {result.avg_ic:.4f}")
    print(f"  avg_sharpe: {result.avg_sharpe:.4f}")
    print(f"  avg_return: {result.avg_return:.6f}")
    print(f"  ic_stability: {result.ic_stability:.4f}")
    return result


def test_leakage(features, label):
    """测试 Leakage 检测"""
    print("\n=== 2. Leakage Detector ===")
    detector = LeakageDetector()
    report = detector.check_data(features, label)
    print(f"  passed: {report.passed}")
    print(f"  critical: {report.n_critical}, warning: {report.n_warning}")

    # FeatureLeakageScanner
    scanner = FeatureLeakageScanner()
    scan_report = scanner.scan_data(features, label)
    print(f"  scanner issues: {len(scan_report.issues)}")
    return report


def test_stability(predictions, label):
    """测试 Stability"""
    print("\n=== 3. Stability Analyzer ===")
    analyzer = StabilityAnalyzer()
    result = analyzer.analyze(predictions, label)
    print(f"  n_years: {result.n_years}")
    print(f"  stability_score: {result.stability_score:.2f}")
    print(f"  grade: {result.grade}")
    print(f"  positive_return_ratio: {result.positive_return_ratio:.0%}")
    return result


def test_regime(predictions, label):
    """测试 Regime"""
    print("\n=== 4. Regime Validator ===")
    validator = RegimeValidator()
    result = validator.validate(predictions, label)
    print(f"  bull_sharpe: {result.bull_sharpe:.4f}")
    print(f"  bear_sharpe: {result.bear_sharpe:.4f}")
    print(f"  sideways_sharpe: {result.sideways_sharpe:.4f}")
    print(f"  best_regime: {result.best_regime}")
    print(f"  consistent: {result.consistent}")
    print(f"  grade: {result.grade}")
    return result


def test_robustness(features, label):
    """测试 Robustness"""
    print("\n=== 5. Robustness Tester ===")
    # 简单切分
    n = len(features)
    split = int(n * 0.7)
    X_train, X_test = features.iloc[:split], features.iloc[split:]
    y_train, y_test = label.iloc[:split], label.iloc[split:]

    tester = RobustnessTester(n_perturbations=3, noise_level=0.05)
    result = tester.test(
        X_train, y_train, X_test, y_test,
        model_type=ModelType.LINEAR_REGRESSION,
    )
    print(f"  baseline_ic: {result.baseline_ic:.4f}")
    print(f"  mean_ic: {result.mean_ic:.4f}")
    print(f"  ic_drop_ratio: {result.ic_drop_ratio:.2%}")
    print(f"  robustness_score: {result.robustness_score:.2f}")
    print(f"  is_overfit: {result.is_overfit}")
    print(f"  grade: {result.grade}")
    return result


def test_noise(features, label):
    """测试 Noise"""
    print("\n=== 6. Noise Tester ===")
    # 训练一个模型
    n = len(features)
    split = int(n * 0.7)
    X_train, X_test = features.iloc[:split], features.iloc[split:]
    y_train, y_test = label.iloc[:split], label.iloc[split:]

    model = create_model(ModelType.LINEAR_REGRESSION, {})
    model.fit(X_train, y_train)

    tester = NoiseTester()
    result = tester.test(model, X_test, y_test)
    print(f"  baseline_ic: {result.baseline_ic:.4f}")
    print(f"  noise_sensitivity: {result.noise_sensitivity:.4f}")
    print(f"  noise_score: {result.noise_score:.2f}")
    print(f"  grade: {result.grade}")
    return result


def test_benchmark(predictions, label):
    """测试 Benchmark"""
    print("\n=== 7. Benchmark Engine ===")
    engine = BenchmarkEngine()
    report = engine.compare(predictions=predictions, label=label)
    print(f"  ML sharpe: {report.ml_result.sharpe:.4f}")
    for b in report.benchmarks:
        print(f"  {b.name}: sharpe={b.sharpe:.4f}")
    print(f"  ml_beats_buy_hold: {report.ml_beats_buy_hold}")
    print(f"  ml_beats_random: {report.ml_beats_random}")
    print(f"  ml_beats_all: {report.ml_beats_all}")
    print(f"  benchmark_score: {report.benchmark_score:.2f}")
    print(f"  grade: {report.grade}")
    return report


def test_validation_report(
    leakage, walk_forward, stability, regime, robustness, noise, benchmark
):
    """测试 Validation Report"""
    print("\n=== 8. Validation Report ===")
    report = build_validation_report(
        name="LGBM_v3",
        leakage_report=leakage,
        walk_forward_result=walk_forward,
        stability_result=stability,
        regime_result=regime,
        robustness_result=robustness,
        noise_result=noise,
        benchmark_report=benchmark,
    )
    print(report.to_summary_text())
    return report


def main():
    print("M3 端到端验证测试")
    print("=" * 60)

    # 1. 生成数据
    features, label = make_synthetic_data(n_days=1000)
    print(f"Features shape: {features.shape}, Label shape: {label.shape}")

    # 2. Walk Forward
    wf_result = test_walk_forward(features, label)
    predictions = wf_result.predictions if wf_result.predictions is not None else pd.Series(0, index=label.index)

    # 3. Leakage
    leakage = test_leakage(features, label)

    # 4. Stability
    stability = test_stability(predictions, label)

    # 5. Regime
    regime = test_regime(predictions, label)

    # 6. Robustness
    robustness = test_robustness(features, label)

    # 7. Noise
    noise = test_noise(features, label)

    # 8. Benchmark
    benchmark = test_benchmark(predictions, label)

    # 9. Validation Report
    report = test_validation_report(
        leakage, wf_result, stability, regime, robustness, noise, benchmark
    )

    print("\n" + "=" * 60)
    print(f"Final Model Score: {report.model_score:.1f} ({report.model_grade})")
    print(f"Overall Status: {report.overall_status.value}")
    print("\nM3 端到端验证测试完成！")


if __name__ == "__main__":
    main()
