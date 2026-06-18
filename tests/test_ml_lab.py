"""
ML Lab 端到端测试

测试完整闭环：
  DataHub → Feature Engineering → Label Engineering → Model Training
  → Walk Forward → Backtest → Deploy

覆盖：
  ML1: Dataset Center
  ML2: Feature Lab
  ML3: Label Lab
  ML4: Feature Analysis
  ML5: Model Lab
  ML6: Training Center
  ML7: Validation Center
  ML8: Leakage Detector
  ML9: Model Registry
  ML10: ML Strategy Builder
"""

import numpy as np
import pandas as pd
import pytest

from quantlab.ml import (
    # Dataset
    Dataset, DatasetManager, get_dataset_manager,
    # Feature
    Feature, FeatureRegistry, get_feature_registry,
    # Label
    Label, LabelRegistry, get_label_registry,
    # Feature Analysis
    FeatureAnalyzer,
    # Model
    Model, ModelType,
    # Training
    TrainingJob, TrainingManager, get_training_manager,
    # Validation
    WalkForward, ValidationConfig,
    # Leakage
    LeakageDetector, LeakageReport,
    # Model Registry
    ModelVersion, ModelRegistry, get_model_registry,
    # Strategy Builder
    MLStrategy, MLStrategyBuilder, MLStrategyConfig,
)


# ==================================================================
# 测试数据生成
# ==================================================================

def make_synthetic_ohlc(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """生成合成 OHLCV 数据"""
    np.random.seed(seed)
    dates = pd.date_range("2022-01-01", periods=n, freq="D")
    returns = np.random.normal(0.0005, 0.02, n)
    close = 100 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.normal(0, 0.01, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, n)))
    open_ = close * (1 + np.random.normal(0, 0.005, n))
    volume = np.random.lognormal(10, 1, n)
    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=dates)


@pytest.fixture
def ohlc_data():
    return make_synthetic_ohlc(500)


# ==================================================================
# ML1: Dataset Center
# ==================================================================

class TestDatasetCenter:
    def test_create_dataset(self):
        mgr = DatasetManager()
        ds = mgr.create_dataset(
            name="Test_DS",
            symbols=["BTC"],
            frequency="1d",
            description="test",
        )
        assert ds.dataset_id != ""
        assert ds.name == "Test_DS"
        assert ds.symbols == ["BTC"]

    def test_set_data_and_stats(self, ohlc_data):
        ds = Dataset(name="Test", symbols=["BTC"])
        ds.set_data(ohlc_data)
        stats = ds.get_stats()
        assert stats.n_rows == 500
        assert stats.n_cols == 5

    def test_load_csv(self, tmp_path, ohlc_data):
        csv_path = tmp_path / "test.csv"
        ohlc_data.to_csv(csv_path)
        mgr = DatasetManager()
        ds = mgr.create_dataset(name="CSV_DS", symbols=["BTC"])
        assert mgr.load_csv(ds.dataset_id, str(csv_path)) is True
        assert ds.get_data() is not None


# ==================================================================
# ML2: Feature Lab
# ==================================================================

class TestFeatureLab:
    def test_registry_singleton(self):
        reg1 = get_feature_registry()
        reg2 = get_feature_registry()
        assert reg1 is reg2

    def test_builtin_features_registered(self):
        reg = get_feature_registry()
        assert reg.has("rsi14")
        assert reg.has("macd_12_26_9")
        assert reg.has("atr14")
        assert reg.has("momentum20")
        assert reg.has("vol_zscore20")

    def test_compute_rsi(self, ohlc_data):
        reg = get_feature_registry()
        rsi = reg.compute("rsi14", ohlc_data)
        assert rsi is not None
        assert len(rsi) == 500
        assert ((rsi >= 0) & (rsi <= 100)).all()

    def test_compute_many(self, ohlc_data):
        reg = get_feature_registry()
        df = reg.compute_many(["rsi14", "momentum20", "atr14"], ohlc_data)
        assert len(df.columns) == 3
        assert len(df) == 500

    def test_list_by_category(self):
        reg = get_feature_registry()
        momentum_feats = reg.list_features(category="momentum")
        assert len(momentum_feats) > 0


# ==================================================================
# ML3: Label Lab
# ==================================================================

class TestLabelLab:
    def test_builtin_labels_registered(self):
        reg = get_label_registry()
        assert reg.has("future_return_10")
        assert reg.has("updown_10_0.01")

    def test_future_return(self, ohlc_data):
        reg = get_label_registry()
        label = reg.generate("future_return_10", ohlc_data)
        assert label is not None
        assert len(label) == 500
        # 最后 10 期应为 NaN
        assert label.iloc[-1] != label.iloc[-1]  # NaN check

    def test_updown_label(self, ohlc_data):
        reg = get_label_registry()
        label = reg.generate("updown_10_0.01", ohlc_data)
        assert label is not None
        # 应该只有 0, 1, 2, NaN
        valid_values = set(label.dropna().unique())
        assert valid_values.issubset({0, 1, 2})


# ==================================================================
# ML4: Feature Analysis
# ==================================================================

class TestFeatureAnalysis:
    def test_analyze(self, ohlc_data):
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()

        features = feat_reg.compute_many(["rsi14", "momentum20", "atr14"], ohlc_data)
        label = label_reg.generate("future_return_10", ohlc_data)

        analyzer = FeatureAnalyzer()
        results = analyzer.analyze(features, label)
        assert len(results) == 3
        assert all(r.n_samples > 0 for r in results)

    def test_correlation_matrix(self, ohlc_data):
        feat_reg = get_feature_registry()
        features = feat_reg.compute_many(["rsi14", "momentum20"], ohlc_data)
        analyzer = FeatureAnalyzer()
        corr = analyzer.correlation_matrix(features)
        assert corr.shape == (2, 2)

    def test_rank_features(self, ohlc_data):
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        features = feat_reg.compute_many(["rsi14", "momentum20"], ohlc_data)
        label = label_reg.generate("future_return_10", ohlc_data)
        analyzer = FeatureAnalyzer()
        results = analyzer.analyze(features, label)
        df = analyzer.rank_features(results)
        assert len(df) == 2


# ==================================================================
# ML5: Model Lab
# ==================================================================

class TestModelLab:
    def test_linear_regression(self, ohlc_data):
        from quantlab.ml.model import create_model
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        features = feat_reg.compute_many(["rsi14", "momentum20"], ohlc_data)
        label = label_reg.generate("future_return_10", ohlc_data)

        model = create_model(ModelType.LINEAR_REGRESSION)
        model.fit(features.iloc[:400], label.iloc[:400])
        assert model.is_fitted

        preds = model.predict(features.iloc[400:])
        assert len(preds) == 100

        metrics = model.evaluate(features.iloc[400:], label.iloc[400:])
        # 最后 10 期标签为 NaN（未来数据），所以有效样本为 90
        assert metrics.n_samples == 90

    def test_random_forest(self, ohlc_data):
        from quantlab.ml.model import create_model
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        features = feat_reg.compute_many(["rsi14", "momentum20"], ohlc_data)
        label = label_reg.generate("future_return_10", ohlc_data)

        model = create_model(ModelType.RANDOM_FOREST, {"n_estimators": 10})
        model.fit(features.iloc[:400], label.iloc[:400])
        assert model.is_fitted

        fi = model.feature_importance()
        assert fi is not None
        assert len(fi) == 2

    def test_list_supported_models(self):
        from quantlab.ml.model import list_supported_models
        models = list_supported_models()
        assert len(models) == 5
        types = [m["type"] for m in models]
        assert "LINEAR_REGRESSION" in types
        assert "LIGHTGBM" in types


# ==================================================================
# ML6: Training Center
# ==================================================================

class TestTrainingCenter:
    def test_training_job(self, ohlc_data):
        # 准备数据集
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.create_dataset(name="Train_DS", symbols=["BTC"])
        ds.set_data(ohlc_data)

        # 训练
        job = TrainingJob(
            dataset_id=ds.dataset_id,
            feature_ids=["rsi14", "momentum20"],
            label_id="future_return_10",
            model_type=ModelType.LINEAR_REGRESSION,
            train_ratio=0.7,
            val_ratio=0.15,
        )
        result = job.run()
        assert result.status.value == "COMPLETED"
        assert result.n_train_samples > 0
        assert result.metrics is not None

    def test_training_manager(self, ohlc_data):
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.create_dataset(name="Mgr_DS", symbols=["BTC"])
        ds.set_data(ohlc_data)

        mgr = TrainingManager()
        job = TrainingJob(
            dataset_id=ds.dataset_id,
            feature_ids=["rsi14"],
            label_id="future_return_10",
            model_type=ModelType.LINEAR_REGRESSION,
        )
        result = mgr.submit(job)
        assert result.status.value == "COMPLETED"
        assert len(mgr.list_jobs()) == 1


# ==================================================================
# ML7: Validation Center (Walk Forward)
# ==================================================================

class TestValidationCenter:
    def test_walk_forward(self, ohlc_data):
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        features = feat_reg.compute_many(["rsi14", "momentum20"], ohlc_data)
        label = label_reg.generate("future_return_10", ohlc_data)

        config = ValidationConfig(
            n_splits=3,
            train_size=200,
            test_size=50,
            step_size=50,
        )
        wf = WalkForward(config)
        result = wf.run(
            features=features,
            label=label,
            model_type=ModelType.LINEAR_REGRESSION,
        )
        assert result.n_splits > 0
        assert len(result.metrics_per_fold) > 0
        assert len(result.fold_details) > 0


# ==================================================================
# ML8: Leakage Detector
# ==================================================================

class TestLeakageDetector:
    def test_detect_future_function_in_code(self):
        detector = LeakageDetector()

        # 构造一个使用 shift(-1) 的类
        class BadFeature:
            def compute(self, df):
                return df["close"].shift(-1)

        report = detector.check_code(BadFeature)
        assert not report.passed
        assert report.n_critical > 0

    def test_detect_centered_rolling(self):
        detector = LeakageDetector()

        class BadFeature2:
            def compute(self, df):
                return df["close"].rolling(10, center=True).mean()

        report = detector.check_code(BadFeature2)
        assert not report.passed

    def test_detect_time_overlap(self):
        detector = LeakageDetector()
        idx1 = pd.date_range("2022-01-01", periods=100)
        idx2 = pd.date_range("2022-02-20", periods=100)  # overlap
        report = detector.check_time_overlap(idx1, idx2)
        assert not report.passed

    def test_no_overlap_passes(self):
        detector = LeakageDetector()
        idx1 = pd.date_range("2022-01-01", periods=100)
        idx2 = pd.date_range("2022-12-31", periods=100)
        report = detector.check_time_overlap(idx1, idx2)
        assert report.passed


# ==================================================================
# ML9: Model Registry
# ==================================================================

class TestModelRegistry:
    def test_register_and_get(self):
        reg = ModelRegistry()
        version = ModelVersion(
            name="LGBM_v1",
            model_type=ModelType.LIGHTGBM,
            metrics={"sharpe": 1.4, "ic": 0.1},
            feature_ids=["rsi14"],
            label_id="future_return_10",
        )
        vid = reg.register(version)
        assert reg.get_version(vid) is not None

    def test_list_versions(self):
        reg = ModelRegistry()
        reg.register(ModelVersion(name="v1", model_type=ModelType.LIGHTGBM))
        reg.register(ModelVersion(name="v2", model_type=ModelType.RANDOM_FOREST))
        all_versions = reg.list_versions()
        assert len(all_versions) == 2
        lgbm_versions = reg.list_versions(model_type=ModelType.LIGHTGBM)
        assert len(lgbm_versions) == 1

    def test_get_latest(self):
        reg = ModelRegistry()
        reg.register(ModelVersion(name="old", model_type=ModelType.LIGHTGBM))
        import time
        time.sleep(0.01)
        reg.register(ModelVersion(name="new", model_type=ModelType.LIGHTGBM))
        latest = reg.get_latest(ModelType.LIGHTGBM)
        assert latest.name == "new"


# ==================================================================
# ML10: ML Strategy Builder
# ==================================================================

class TestMLStrategyBuilder:
    def test_build_strategy(self, ohlc_data):
        builder = MLStrategyBuilder()

        # 训练模型
        model = builder.train(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20"],
            label_id="future_return_10",
            model_type=ModelType.LINEAR_REGRESSION,
        )
        assert model.is_fitted

        # 构建策略
        strategy = builder.build(
            feature_ids=["rsi14", "momentum20"],
            label_id="future_return_10",
            model=model,
            model_type=ModelType.LINEAR_REGRESSION,
            long_threshold=0.0,
            use_short=False,
        )
        assert strategy.strategy_id != ""

        # 预测
        preds = strategy.predict(ohlc_data)
        assert len(preds) == 500

        # 信号
        signals = strategy.signal(ohlc_data)
        assert signals.isin([0, 1, -1]).all()

        # 持仓
        positions = strategy.position(ohlc_data)
        assert positions.isin([0, 1, -1]).all()

    def test_strategy_with_short(self, ohlc_data):
        builder = MLStrategyBuilder()
        model = builder.train(
            df=ohlc_data,
            feature_ids=["rsi14"],
            label_id="future_return_10",
            model_type=ModelType.LINEAR_REGRESSION,
        )
        strategy = builder.build(
            feature_ids=["rsi14"],
            label_id="future_return_10",
            model=model,
            long_threshold=0.001,
            short_threshold=-0.001,
            use_short=True,
        )
        signals = strategy.signal(ohlc_data)
        assert signals.isin([0, 1, -1]).all()


# ==================================================================
# 完整闭环测试
# ==================================================================

class TestEndToEnd:
    """端到端：DataHub → Feature → Label → Train → Validate → Strategy"""

    def test_full_pipeline(self, ohlc_data):
        # 1. Dataset
        ds_mgr = get_dataset_manager()
        ds = ds_mgr.create_dataset(name="E2E_DS", symbols=["BTC"])
        ds.set_data(ohlc_data)

        # 2. Feature + Label
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        features = feat_reg.compute_many(
            ["rsi14", "momentum20", "atr14", "vol_zscore20"],
            ohlc_data,
        )
        label = label_reg.generate("future_return_10", ohlc_data)
        assert not features.empty
        assert label is not None

        # 3. Feature Analysis
        analyzer = FeatureAnalyzer()
        analysis = analyzer.analyze(features, label)
        assert len(analysis) == 4

        # 4. Leakage Detection
        detector = LeakageDetector()
        leak_report = detector.check_data(features, label)
        # 合成数据不应有严重泄漏
        assert leak_report.n_critical == 0

        # 5. Walk Forward Validation
        config = ValidationConfig(
            n_splits=3,
            train_size=200,
            test_size=50,
            step_size=50,
        )
        wf = WalkForward(config)
        wf_result = wf.run(
            features=features,
            label=label,
            model_type=ModelType.LINEAR_REGRESSION,
        )
        assert wf_result.n_splits > 0

        # 6. Train final model
        builder = MLStrategyBuilder()
        model = builder.train(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20", "atr14", "vol_zscore20"],
            label_id="future_return_10",
            model_type=ModelType.LINEAR_REGRESSION,
        )

        # 7. Build Strategy
        strategy = builder.build(
            feature_ids=["rsi14", "momentum20", "atr14", "vol_zscore20"],
            label_id="future_return_10",
            model=model,
            model_type=ModelType.LINEAR_REGRESSION,
            long_threshold=0.0,
        )

        # 8. Generate signals
        signals = strategy.signal(ohlc_data)
        positions = strategy.position(ohlc_data)
        assert len(signals) == 500
        assert len(positions) == 500

        # 9. Register Model
        reg = get_model_registry()
        version = ModelVersion(
            name="E2E_LGBM_v1",
            model_type=ModelType.LINEAR_REGRESSION,
            metrics={"ic": wf_result.avg_ic},
            feature_ids=["rsi14", "momentum20", "atr14", "vol_zscore20"],
            label_id="future_return_10",
        )
        version.set_model(model)
        vid = reg.register(version)
        assert reg.get_version(vid) is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
