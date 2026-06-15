"""
V4.5 Research IDE 演示

演示 8 个核心能力：
  1) ResearchSession — 研究会话
  2) Dataset API — 数据加载/预览
  3) FactorRegistry — 因子注册/计算
  4) FeatureStore — 特征存储/复用
  5) ArtifactStore — 产物保存
  6) Cell 执行模型 — 代码/标记单元
  7) ResearchPipeline — 链式流水线
  8) Research → Experiment 闭环
"""

import os
import sys

# 沙箱画图
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd
import numpy as np

# ── 生成测试数据 ──────────────────────────────────────────────
def make_test_data(symbols=("AAPL", "MSFT", "GOOG"), bars=300):
    np.random.seed(42)
    data = {}
    for sym in symbols:
        dates = pd.date_range("2024-01-01", periods=bars, freq="B")
        close = 100 + np.cumsum(np.random.randn(bars) * 0.5)
        high = close + np.abs(np.random.randn(bars) * 0.3)
        low = close - np.abs(np.random.randn(bars) * 0.3)
        open_ = close + np.random.randn(bars) * 0.2
        volume = (np.random.rand(bars) * 1e6).astype(int)
        data[sym] = pd.DataFrame({
            "open": open_, "high": high, "low": low,
            "close": close, "volume": volume,
        }, index=dates)
    return data


# ══════════════════════════════════════════════════════════════
# 1) ResearchSession
# ══════════════════════════════════════════════════════════════
print("=" * 60)
print("  V4.5 Research IDE Demo")
print("=" * 60)

from quantlab.research import (
    ResearchSession, Cell,
    ResearchCache, FeatureStore, FeatureMetadata,
    FactorRegistry, FactorInfo,
    ArtifactStore, Artifact,
    ResearchPipeline, PipelineStep,
)

session = ResearchSession(name="alpha_research")
print(f"\n1) Session created: {session}")

# ══════════════════════════════════════════════════════════════
# 2) Dataset API
# ══════════════════════════════════════════════════════════════
print("\n2) Dataset API")
data = make_test_data()
# 直接注入数据（不用走 DataLoader）
session._data = data
session._current_dataset = "test_3sym"
session._namespace["data"] = data

print(f"   symbols: {session.symbols()}")
print(f"   head:\n{session.head(n=3)}")
print(f"   dataset_info: {session.dataset_info()}")

# ══════════════════════════════════════════════════════════════
# 3) FactorRegistry
# ══════════════════════════════════════════════════════════════
print("\n3) FactorRegistry")
fr = session.factor_registry
print(f"   registered factors: {[f.name for f in fr.list_factors()]}")
print(f"   categories: {fr.categories()}")
print(f"   stats: {fr.stats()}")

# 计算因子（session.compute_factor 自动遍历所有 symbol）
if fr.get("MA"):
    ma20_all = session.compute_factor("MA", period=20)
    print(f"   MA(20) all symbols shape: {ma20_all.shape if hasattr(ma20_all, 'shape') else type(ma20_all)}")

# ══════════════════════════════════════════════════════════════
# 4) FeatureStore
# ══════════════════════════════════════════════════════════════
print("\n4) FeatureStore")
fs = session.feature_store

# 保存特征（session.compute_factor 自动遍历所有 symbol）
if fr.get("MA"):
    ma5_all = session.compute_factor("MA", period=5)
    ma20_all = session.compute_factor("MA", period=20)
    fs.save("ma5_all", ma5_all, dataset="test_3sym",
            formula="ma(close, 5)", tags=["trend", "fast"])
    fs.save("ma20_all", ma20_all, dataset="test_3sym",
            formula="ma(close, 20)", tags=["trend", "slow"])

# 列出特征
features = fs.list_features()
print(f"   saved features: {[f.name for f in features]}")
for f in features:
    print(f"   - {f.name}: dtype={f.dtype}, shape={f.shape}, formula={f.formula}")

# 复用（cache hit）
ma5_loaded = fs.load("ma5_all")
print(f"   load ma5_all: {type(ma5_loaded).__name__}, shape={ma5_loaded.shape if hasattr(ma5_loaded, 'shape') else 'N/A'}")

# compute + save 一步到位
if fr.get("RSI"):
    rsi14 = fs.compute("rsi14_all", lambda: session.compute_factor("RSI", period=14))
    print(f"   compute rsi14_all: shape={rsi14.shape if hasattr(rsi14, 'shape') else type(rsi14)}")

print(f"   feature store stats: {fs.stats()}")

# ══════════════════════════════════════════════════════════════
# 5) ArtifactStore
# ══════════════════════════════════════════════════════════════
print("\n5) ArtifactStore")
art_store = session.artifact_store

# 保存 DataFrame 产物
corr_df = pd.DataFrame({
    "AAPL": np.random.rand(3),
    "MSFT": np.random.rand(3),
    "GOOG": np.random.rand(3),
}, index=["AAPL", "MSFT", "GOOG"])
art1 = art_store.save("correlation_matrix", corr_df, kind="table",
                       description="3-symbol correlation")
print(f"   saved artifact: {art1.name} [{art1.kind}/{art1.format}] id={art1.artifact_id}")

# 保存 dict 产物
summary = {"total_return": 0.15, "sharpe": 1.2, "max_drawdown": -0.08}
art2 = art_store.save("backtest_summary", summary, kind="notebook_output",
                       description="quick backtest summary")
print(f"   saved artifact: {art2.name} [{art2.kind}/{art2.format}] id={art2.artifact_id}")

# 查询
all_arts = art_store.list_artifacts()
print(f"   total artifacts: {len(all_arts)}")
print(f"   artifact store stats: {art_store.stats()}")

# ══════════════════════════════════════════════════════════════
# 6) Cell 执行模型
# ══════════════════════════════════════════════════════════════
print("\n6) Cell 执行模型")

# markdown cell
md_cell = session.add_markdown("# Alpha Research\n探索均线交叉策略")
print(f"   markdown cell: {md_cell.cell_id} type={md_cell.cell_type}")

# code cell 1: 计算指标
code1 = session.add_code("""
import pandas as pd
import numpy as np
result = {"symbols": len(data), "bars": len(list(data.values())[0])}
print(f"数据概览: {result['symbols']} symbols, {result['bars']} bars")
""")
session.execute(code1)
print(f"   code1 [{code1.status}]: output={code1.output}")

# code cell 2: 简单计算
code2 = session.add_code("""
# 计算每个 symbol 的日收益率
returns = {}
for sym, df in data.items():
    returns[sym] = df["close"].pct_change()
print(f"日收益率计算完成: {list(returns.keys())}")
""")
session.execute(code2)
print(f"   code2 [{code2.status}]: output={code2.output}")

# code cell 3: 错误示例
code3 = session.add_code("1 / 0")
session.execute(code3)
print(f"   code3 [{code3.status}]: error={code3.error}")

print(f"   total cells: {len(session.cells)}")

# ══════════════════════════════════════════════════════════════
# 7) ResearchPipeline
# ══════════════════════════════════════════════════════════════
print("\n7) ResearchPipeline")

from quantlab.signals import MACrossStrategy

pipeline = (
    ResearchPipeline(session)
    .add_factor("MA", period=5, save_as="ma5_pipe")
    .add_factor("MA", period=20, save_as="ma20_pipe")
    .create_signal(MACrossStrategy, fast=5, slow=20, save_as="signal_macross")
    .run_backtest(tag="pipeline_v4.5", note="ResearchPipeline demo")
)

print(f"   pipeline describe:\n{pipeline.describe()}")

# 执行
results = pipeline.execute()

print(f"   pipeline stats: {pipeline.stats()}")
for step in pipeline.steps:
    status_icon = {"success": "OK", "error": "FAIL", "pending": "SKIP"}.get(step.status, step.status)
    print(f"   [{status_icon}] {step.name}")

# ══════════════════════════════════════════════════════════════
# 8) Research → Experiment 闭环
# ══════════════════════════════════════════════════════════════
print("\n8) Research → Experiment 闭环")

# 直接在 session 里跑回测
from quantlab.signals import RSIStrategy
result = session.run_backtest(
    strategy=RSIStrategy(period=14),
    tag="research_rsi",
    note="from ResearchSession",
)
metrics = result.metrics()
print(f"   backtest result: return={metrics.get('total_return', 0):.2%}, "
      f"sharpe={metrics.get('sharpe', 0):.2f}, "
      f"trades={metrics.get('trade_count', 0)}")

# ══════════════════════════════════════════════════════════════
# 总结
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  V4.5 Research IDE Summary")
print("=" * 60)
stats = session.stats()
print(f"  session_id:      {stats['session_id']}")
print(f"  name:            {stats['name']}")
print(f"  symbols:         {stats['symbols']}")
print(f"  cells:           {stats['cells']}")
print(f"  features:        {stats['features']}")
print(f"  artifacts:       {stats['artifacts']}")
print(f"  factors:         {stats['factors']}")
print(f"  cache entries:   {stats['cache']['memory_entries']}")
print(f"  cache hits:      {stats['cache']['total_hits']}")

print("\n  Feature Store:")
for f in fs.list_features():
    print(f"    {f.name}: dtype={f.dtype}, shape={f.shape}, formula={f.formula}")

print("\n  Artifact Store:")
for a in art_store.list_artifacts():
    print(f"    {a.name} [{a.kind}/{a.format}] {a.size_bytes}B")

print("\n  Factor Registry:")
for f in fr.list_factors():
    print(f"    {f.name}: category={f.category}, params={f.parameters}")

print("\n[OK] V4.5 Research IDE demo complete!")
