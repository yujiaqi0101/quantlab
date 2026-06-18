"""
ML Lab V2 端到端测试 — Alpha 生产线

测试 10 层架构：
  L1: ML Data Pipeline      — TrainingDataset
  L2: FeatureSet            — 特征集合
  L3: LabelSet              — 标签集合
  L4: Training Job System   — dataset + feature_set + label_set + model
  L5: Experiment Tracker    — 实验追踪
  L6: Hyperparameter Search — GridSearch + RandomSearch
  L7: Walk Forward Engine   — 滚动验证（TDS 支持）
  L8: Feature Importance    — Gain / Permutation / SHAP
  L9: Model Comparison      — Model Arena
  L10: ML Strategy Generator — FeatureSet + LabelSet + Model → Strategy
"""

import numpy as np
import pandas as pd
import pytest

from quantlab.ml import (
    # L1: Pipeline
    TrainingDataset, MLPipeline, get_pipeline,
    # L2: FeatureSet
    FeatureSet, FeatureSetRegistry, get_feature_set_registry,
    # L3: LabelSet
    LabelSet, LabelSetRegistry, get_label_set_registry,
    # L4: Training
    TrainingJob, get_training_manager,
    # L5: Experiment
    Experiment, ExperimentTracker, get_experiment_tracker,
    # L6: Search
    GridSearch, RandomSearch,
    # L7: Validation
    WalkForward, ValidationConfig,
    # L8: Feature Importance
    FeatureImportanceAnalyzer,
    compute_gain_importance, compute_permutation_importance,
    # L9: Comparison
    ModelArena, ModelResult, compare_models, get_model_arena,
    # L10: Strategy
    MLStrategy, MLStrategyBuilder, MLStrategyConfig,
    # Common
    ModelType, Dataset, DatasetManager, get_dataset_manager,
    get_feature_registry, get_label_registry,
)
from quantlab.ml.model import create_model


# ==================================================================
# 测试数据
# ==================================================================

def make_synthetic_ohlc(n: int = 500, seed: int = 42) -> pd.DataFrame:
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


@pytest.fixture
def dataset(ohlc_data):
    """创建带数据的 Dataset"""
    mgr = get_dataset_manager()
    ds = mgr.create_dataset(name="V2Test_DS", symbols=["BTC"], frequency="1d")
    ds.set_data(ohlc_data)
    return ds


# ==================================================================
# L1: ML Data Pipeline — TrainingDataset
# ==================================================================

class TestL1Pipeline:
    def test_training_dataset_creation(self):
        X = pd.DataFrame({"f1": [1, 2, 3], "f2": [4, 5, 6]})
        y = pd.Series([0.1, 0.2, 0.3], name="label")
        tds = TrainingDataset(X=X, y=y)
        assert tds.X.shape == (3, 2)
        assert tds.y.shape == (3,)
        assert tds.tds_id.startswith("TDS-")
        assert tds.metadata == {}

    def test_training_dataset_split(self):
        n = 100
        X = pd.DataFrame({"f1": np.arange(n), "f2": np.arange(n) * 2})
        y = pd.Series(np.arange(n) * 0.1, name="label")
        tds = TrainingDataset(X=X, y=y)
        splits = tds.split(train_ratio=0.7, val_ratio=0.15)
        assert "train" in splits
        assert "val" in splits
        assert "test" in splits
        assert len(splits["train"].X) == 70
        assert len(splits["val"].X) == 15
        assert len(splits["test"].X) == 15

    def test_pipeline_build_from_raw(self, ohlc_data):
        pipeline = get_pipeline()
        tds = pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20"],
            label_id="future_return_5",
        )
        assert isinstance(tds, TrainingDataset)
        assert tds.X.shape[0] == tds.y.shape[0]
        assert "rsi14" in tds.X.columns
        assert "momentum20" in tds.X.columns

    def test_pipeline_build_with_dataset(self, dataset):
        pipeline = get_pipeline()
        tds = pipeline.build_from_raw(
            df=dataset.get_data(),
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            label_id="future_return_5",
        )
        assert tds.X.shape[0] > 0
        assert tds.metadata.get("dataset_id") is None  # raw build 不带 dataset_id


# ==================================================================
# L2: FeatureSet — 特征集合
# ==================================================================

class TestL2FeatureSet:
    def test_create_feature_set(self):
        fs = FeatureSet(
            name="test_momentum_v1",
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            description="动量特征集合",
            tags=["momentum", "test"],
        )
        assert fs.name == "test_momentum_v1"
        assert len(fs.feature_ids) == 3
        assert fs.fs_id.startswith("FS-")

    def test_feature_set_compute(self, ohlc_data):
        fs = FeatureSet(
            name="test_compute",
            feature_ids=["rsi14", "momentum20"],
        )
        features = fs.compute(ohlc_data)
        assert "rsi14" in features.columns
        assert "momentum20" in features.columns
        assert features.shape[0] == len(ohlc_data)

    def test_feature_set_registry(self):
        reg = get_feature_set_registry()
        # 清理可能存在的同名
        existing = reg.get("registry_test")
        if existing is None:
            fs = FeatureSet(name="registry_test", feature_ids=["rsi14"])
            reg.register(fs)
        assert reg.get("registry_test") is not None

    def test_feature_set_to_dict(self):
        fs = FeatureSet(
            name="dict_test",
            feature_ids=["rsi14"],
            description="test",
            version="2.0",
        )
        d = fs.to_dict()
        assert d["name"] == "dict_test"
        assert d["version"] == "2.0"
        assert d["feature_ids"] == ["rsi14"]


# ==================================================================
# L3: LabelSet — 标签集合
# ==================================================================

class TestL3LabelSet:
    def test_create_label_set(self):
        ls = LabelSet(
            name="test_return_5d",
            label_id="future_return_5",
            description="5日未来收益",
            label_type="regression",
        )
        assert ls.name == "test_return_5d"
        assert ls.label_id == "future_return_5"
        assert ls.ls_id.startswith("LS-")

    def test_label_set_generate(self, ohlc_data):
        ls = LabelSet(
            name="test_gen",
            label_id="future_return_5",
            label_type="regression",
        )
        label = ls.generate(ohlc_data)
        assert label is not None
        assert len(label) == len(ohlc_data)

    def test_label_set_registry(self):
        reg = get_label_set_registry()
        existing = reg.get("registry_label_test")
        if existing is None:
            ls = LabelSet(name="registry_label_test", label_id="future_return_5")
            reg.register(ls)
        assert reg.get("registry_label_test") is not None

    def test_label_set_classification_type(self):
        ls = LabelSet(
            name="test_direction",
            label_id="updown_5",
            label_type="classification",
            classes=["Down", "Neutral", "Up"],
        )
        d = ls.to_dict()
        assert d["label_type"] == "classification"
        assert len(d["classes"]) == 3


# ==================================================================
# L4: Training Job System — 集合模式
# ==================================================================

class TestL4TrainingJob:
    def test_training_job_with_sets(self, dataset, ohlc_data):
        # 注册 FeatureSet 和 LabelSet
        fs_reg = get_feature_set_registry()
        ls_reg = get_label_set_registry()

        fs = FeatureSet(
            name="v2_train_fs",
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
        )
        ls = LabelSet(
            name="v2_train_ls",
            label_id="future_return_5",
            label_type="regression",
        )
        fs_reg.register(fs)
        ls_reg.register(ls)

        # 创建 TrainingJob
        job = TrainingJob(
            dataset_id=dataset.dataset_id,
            feature_set_id="v2_train_fs",
            label_set_id="v2_train_ls",
            model_type=ModelType.LIGHTGBM,
            is_classifier=False,
        )
        assert job.feature_set_id == "v2_train_fs"
        assert job.label_set_id == "v2_train_ls"

    def test_training_job_run_with_sets(self, dataset, ohlc_data):
        fs_reg = get_feature_set_registry()
        ls_reg = get_label_set_registry()

        if not fs_reg.get("v2_run_fs"):
            fs_reg.register(FeatureSet(
                name="v2_run_fs",
                feature_ids=["rsi14", "momentum20"],
            ))
        if not ls_reg.get("v2_run_ls"):
            ls_reg.register(LabelSet(
                name="v2_run_ls",
                label_id="future_return_5",
            ))

        mgr = get_training_manager()
        job = TrainingJob(
            dataset_id=dataset.dataset_id,
            feature_set_id="v2_run_fs",
            label_set_id="v2_run_ls",
            model_type=ModelType.LINEAR_REGRESSION,
            is_classifier=False,
        )
        result = mgr.submit(job)
        assert result is not None
        assert result.model is not None


# ==================================================================
# L5: Experiment Tracker — 实验追踪
# ==================================================================

class TestL5ExperimentTracker:
    def test_create_experiment(self):
        exp = Experiment(
            name="test_exp_v2",
            dataset_id="DS-TEST",
            feature_set_id="FS-TEST",
            label_set_id="LS-TEST",
            model_type="LIGHTGBM",
            model_params={"n_estimators": 100},
            is_classifier=False,
            metrics={"ic": 0.15, "rmse": 0.02},
        )
        assert exp.name == "test_exp_v2"
        assert exp.experiment_id.startswith("EXP-")
        assert exp.metrics["ic"] == 0.15

    def test_experiment_tracker_register(self):
        tracker = get_experiment_tracker()
        exp = Experiment(
            name="tracker_test",
            model_type="LINEAR_REGRESSION",
            metrics={"ic": 0.1},
        )
        tracker.save(exp)
        assert tracker.get(exp.experiment_id) is not None

    def test_experiment_to_dict(self):
        exp = Experiment(
            name="dict_test",
            model_type="LIGHTGBM",
            metrics={"ic": 0.2, "rmse": 0.01},
            feature_importance={"rsi14": 0.5, "momentum20": 0.3},
        )
        d = exp.to_dict()
        assert d["name"] == "dict_test"
        assert d["metrics"]["ic"] == 0.2
        assert d["feature_importance"]["rsi14"] == 0.5


# ==================================================================
# L6: Hyperparameter Search — 超参搜索
# ==================================================================

class TestL6HyperparameterSearch:
    @pytest.fixture
    def tds(self, ohlc_data):
        pipeline = get_pipeline()
        return pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            label_id="future_return_5",
        )

    def test_grid_search(self, tds):
        search = GridSearch(
            model_type=ModelType.LINEAR_REGRESSION,
            param_grid={"fit_intercept": [True, False]},
            metric="ic",
            is_classifier=False,
        )
        result = search.run(tds)
        assert result is not None
        assert result.best_params is not None
        assert len(result.trials) == 2

    def test_random_search(self, tds):
        search = RandomSearch(
            model_type=ModelType.LINEAR_REGRESSION,
            param_space={"fit_intercept": [True, False]},
            n_trials=3,
            metric="ic",
            is_classifier=False,
        )
        result = search.run(tds)
        assert result is not None
        assert len(result.trials) == 3


# ==================================================================
# L7: Walk Forward Engine — TDS 支持
# ==================================================================

class TestL7WalkForward:
    def test_walk_forward_with_tds(self, ohlc_data):
        pipeline = get_pipeline()
        tds = pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20"],
            label_id="future_return_5",
        )
        wf = WalkForward(ValidationConfig(
            train_size=200,
            test_size=50,
            step_size=50,
        ))
        result = wf.run_tds(
            tds=tds,
            model_type=ModelType.LINEAR_REGRESSION,
            is_classifier=False,
        )
        assert result is not None
        assert len(result.metrics_per_fold) > 0 or result.n_splits > 0


# ==================================================================
# L8: Feature Importance — 特征重要性
# ==================================================================

class TestL8FeatureImportance:
    @pytest.fixture
    def trained_model(self, ohlc_data):
        feat_reg = get_feature_registry()
        label_reg = get_label_registry()
        X = feat_reg.compute_many(["rsi14", "momentum20", "vol_zscore20"], ohlc_data)
        y = label_reg.generate("future_return_5", ohlc_data)
        # 对齐并 dropna
        df = pd.concat([X, y], axis=1).dropna()
        X_clean = df[X.columns]
        y_clean = df[y.name]
        model = create_model(ModelType.LIGHTGBM, {"n_estimators": 30, "verbose": -1})
        model.fit(X_clean, y_clean)
        return model, X_clean, y_clean

    def test_gain_importance(self, trained_model):
        model, X, y = trained_model
        result = compute_gain_importance(model)
        assert result is not None
        assert len(result.importances) > 0
        assert result.method == "gain"

    def test_permutation_importance(self, trained_model):
        model, X, y = trained_model
        result = compute_permutation_importance(
            model, X=X, y=y, metric="ic", n_repeats=2,
        )
        assert result is not None
        assert len(result.importances) > 0
        assert result.method == "permutation"

    def test_feature_importance_analyzer(self, trained_model):
        model, X, y = trained_model
        analyzer = FeatureImportanceAnalyzer()
        results = analyzer.analyze(model, X=X, y=y, methods=["gain"])
        assert "gain" in results
        assert len(results["gain"].importances) > 0


# ==================================================================
# L9: Model Comparison — Model Arena
# ==================================================================

class TestL9ModelComparison:
    @pytest.fixture
    def tds(self, ohlc_data):
        pipeline = get_pipeline()
        return pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            label_id="future_return_5",
        )

    def test_compare_models(self, tds):
        arena = compare_models(
            tds=tds,
            model_types=[ModelType.LINEAR_REGRESSION, ModelType.LIGHTGBM],
            is_classifier=False,
        )
        assert arena is not None
        leaderboard = arena.get_leaderboard(metric="ic")
        assert len(leaderboard) == 2

    def test_model_arena_singleton(self):
        arena1 = get_model_arena()
        arena2 = get_model_arena()
        assert arena1 is arena2

    def test_model_result_to_dict(self):
        result = ModelResult(
            name="TestModel",
            model_type="LIGHTGBM",
            model_params={"n_estimators": 100},
            metrics={"ic": 0.15, "rmse": 0.02},
        )
        d = result.to_dict()
        assert d["model_type"] == "LIGHTGBM"
        assert d["metrics"]["ic"] == 0.15


# ==================================================================
# L10: ML Strategy Generator — 集合模式
# ==================================================================

class TestL10MLStrategyGenerator:
    def test_build_strategy_from_sets(self, dataset, ohlc_data):
        fs_reg = get_feature_set_registry()
        ls_reg = get_label_set_registry()

        if not fs_reg.get("v2_strategy_fs"):
            fs_reg.register(FeatureSet(
                name="v2_strategy_fs",
                feature_ids=["rsi14", "momentum20"],
            ))
        if not ls_reg.get("v2_strategy_ls"):
            ls_reg.register(LabelSet(
                name="v2_strategy_ls",
                label_id="future_return_5",
            ))

        builder = MLStrategyBuilder()
        builder.set_registries(
            feature_registry=get_feature_registry(),
            label_registry=get_label_registry(),
            feature_set_registry=fs_reg,
            label_set_registry=ls_reg,
        )

        # 训练
        model = builder.train_with_sets(
            df=ohlc_data,
            feature_set_id="v2_strategy_fs",
            label_set_id="v2_strategy_ls",
            model_type=ModelType.LINEAR_REGRESSION,
        )
        assert model is not None

        # 构建策略
        strategy = builder.build_from_sets(
            feature_set_id="v2_strategy_fs",
            label_set_id="v2_strategy_ls",
            model=model,
            model_type=ModelType.LINEAR_REGRESSION,
            long_threshold=0.0,
            use_short=False,
        )
        assert strategy.strategy_id.startswith("MLS-")
        assert strategy.config.feature_set_id == "v2_strategy_fs"

    def test_strategy_predict_signal_position(self, dataset, ohlc_data):
        fs_reg = get_feature_set_registry()
        ls_reg = get_label_set_registry()

        if not fs_reg.get("v2_predict_fs"):
            fs_reg.register(FeatureSet(
                name="v2_predict_fs",
                feature_ids=["rsi14", "momentum20"],
            ))
        if not ls_reg.get("v2_predict_ls"):
            ls_reg.register(LabelSet(
                name="v2_predict_ls",
                label_id="future_return_5",
            ))

        builder = MLStrategyBuilder()
        builder.set_registries(
            feature_registry=get_feature_registry(),
            label_registry=get_label_registry(),
            feature_set_registry=fs_reg,
            label_set_registry=ls_reg,
        )

        model = builder.train_with_sets(
            df=ohlc_data,
            feature_set_id="v2_predict_fs",
            label_set_id="v2_predict_ls",
            model_type=ModelType.LINEAR_REGRESSION,
        )

        strategy = builder.build_from_sets(
            feature_set_id="v2_predict_fs",
            label_set_id="v2_predict_ls",
            model=model,
            model_type=ModelType.LINEAR_REGRESSION,
            long_threshold=0.0,
            use_short=True,
            short_threshold=0.0,
        )

        # 预测
        preds = strategy.predict(ohlc_data)
        assert len(preds) == len(ohlc_data)

        # 信号
        signals = strategy.signal(ohlc_data)
        assert signals.isin([1, 0, -1]).all()

        # 持仓
        positions = strategy.position(ohlc_data)
        assert len(positions) == len(ohlc_data)


# ==================================================================
# 端到端：完整 Alpha 生产线
# ==================================================================

class TestEndToEndV2:
    def test_full_alpha_pipeline(self, dataset, ohlc_data):
        """
        完整流程：
          Dataset → FeatureSet → LabelSet → TrainingDataset
          → Train → Experiment → Importance → Strategy
        """
        # 1. 注册 FeatureSet
        fs_reg = get_feature_set_registry()
        ls_reg = get_label_set_registry()

        if not fs_reg.get("e2e_v2_fs"):
            fs_reg.register(FeatureSet(
                name="e2e_v2_fs",
                feature_ids=["rsi14", "momentum20", "vol_zscore20"],
                description="E2E test feature set",
                tags=["e2e"],
            ))
        if not ls_reg.get("e2e_v2_ls"):
            ls_reg.register(LabelSet(
                name="e2e_v2_ls",
                label_id="future_return_5",
                label_type="regression",
                tags=["e2e"],
            ))

        # 2. 构建 TrainingDataset
        pipeline = get_pipeline()
        tds = pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            label_id="future_return_5",
        )
        assert tds.X.shape[0] > 0

        # 3. 训练模型
        builder = MLStrategyBuilder()
        builder.set_registries(
            feature_registry=get_feature_registry(),
            label_registry=get_label_registry(),
            feature_set_registry=fs_reg,
            label_set_registry=ls_reg,
        )
        model = builder.train_with_sets(
            df=ohlc_data,
            feature_set_id="e2e_v2_fs",
            label_set_id="e2e_v2_ls",
            model_type=ModelType.LIGHTGBM,
            model_params={"n_estimators": 30, "verbose": -1},
        )
        assert model is not None

        # 4. 计算特征重要性
        fi = compute_gain_importance(model)
        assert len(fi.importances) > 0

        # 5. 构建策略
        strategy = builder.build_from_sets(
            feature_set_id="e2e_v2_fs",
            label_set_id="e2e_v2_ls",
            model=model,
            model_type=ModelType.LIGHTGBM,
            long_threshold=0.0,
            use_short=False,
        )
        assert strategy.strategy_id.startswith("MLS-")

        # 6. 生成信号
        signals = strategy.signal(ohlc_data)
        assert signals.isin([1, 0, -1]).all()

        # 7. 生成持仓
        positions = strategy.position(ohlc_data)
        assert len(positions) == len(ohlc_data)

    def test_alpha_pipeline_with_comparison(self, dataset, ohlc_data):
        """完整流程 + 模型对比"""
        pipeline = get_pipeline()
        tds = pipeline.build_from_raw(
            df=ohlc_data,
            feature_ids=["rsi14", "momentum20", "vol_zscore20"],
            label_id="future_return_5",
        )

        # 对比多个模型
        arena = compare_models(
            tds=tds,
            model_types=[
                ModelType.LINEAR_REGRESSION,
                ModelType.LIGHTGBM,
            ],
            is_classifier=False,
        )
        leaderboard = arena.get_leaderboard(metric="ic")
        assert len(leaderboard) == 2

        # 排行榜应该按 ic 降序
        if len(leaderboard) == 2:
            assert leaderboard[0]["metrics"]["ic"] >= leaderboard[1]["metrics"]["ic"]
