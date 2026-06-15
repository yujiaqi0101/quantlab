"""
V4.6 Analytics Platform — 完整演示

从 "赚没赚钱" 到 "为什么赚钱"
"""

import os
import sys
import tempfile

import numpy as np
import pandas as pd

# 确保可以 import quantlab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.analytics import (
    AnalyticsEngine,
    AttributionAnalyzer,
    BenchmarkAnalyzer,
    CapacityAnalyzer,
    ExposureAnalyzer,
    FactorExposureAnalyzer,
    MetricRegistry,
    SharpeMetric,
    SortinoMetric,
    MaxDDMetric,
    ReturnMetric,
    TurnoverAnalyzer,
)


def generate_sample_data():
    """生成模拟回测数据"""
    np.random.seed(42)
    n_days = 252
    symbols = ["BTC", "ETH", "SOL"]

    # 价格数据
    prices = {}
    for sym in symbols:
        base = {"BTC": 30000, "ETH": 2000, "SOL": 100}[sym]
        returns = np.random.normal(0.0005, 0.03, n_days)
        prices[sym] = base * np.cumprod(1 + returns)

    # 权重历史 (每日再平衡)
    weights_list = []
    for i in range(n_days):
        raw = np.random.dirichlet([1, 1, 1])
        weights_list.append({sym: raw[j] for j, sym in enumerate(symbols)})

    # 净值曲线
    equity = 1_000_000 * np.cumprod(1 + np.random.normal(0.0003, 0.01, n_days))

    # Benchmark (BTC Buy & Hold)
    benchmark = 1_000_000 * np.cumprod(1 + np.random.normal(0.0002, 0.015, n_days))

    # Fills
    fills = []
    for i in range(0, n_days, 10):
        sym = symbols[i % len(symbols)]
        side = "BUY" if i % 20 == 0 else "SELL"
        fills.append({
            "symbol": sym,
            "side": side,
            "price": prices[sym][i],
            "qty": np.random.randint(1, 10),
            "pnl": np.random.normal(500, 1000),
        })

    # 因子值
    factor_values = {
        "momentum": {sym: np.random.normal(0, 1) for sym in symbols},
        "volatility": {sym: np.random.normal(0, 1) for sym in symbols},
        "size": {sym: np.random.normal(0, 1) for sym in symbols},
    }

    return {
        "prices": prices,
        "weights_list": weights_list,
        "equity": equity,
        "benchmark": benchmark,
        "fills": fills,
        "factor_values": factor_values,
        "symbols": symbols,
        "n_days": n_days,
    }


def demo_turnover():
    """[1] Turnover 换手率分析"""
    print("=" * 60)
    print("[1] TurnoverAnalyzer - 换手率分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = TurnoverAnalyzer()

    # List[Dict] 输入
    result = analyzer.analyze(data["weights_list"])
    print(f"  日均换手率: {result['daily_turnover_avg']:.2%}")
    print(f"  年化换手率: {result['annual_turnover']:.2%}")
    print(f"  最大日换手: {result['daily_turnover_max']:.2%}")
    print(f"  再平衡次数: {result['n_rebalances']}")

    # DataFrame 输入
    df = pd.DataFrame(data["weights_list"]).fillna(0)
    result_df = analyzer.analyze(df)
    print(f"  [DataFrame] 年化换手率: {result_df['annual_turnover']:.2%}")

    # 关键判断
    if result["annual_turnover"] > 20:
        print("  [!] 警告: 年换手率超过 2000%, 实盘可能无法执行!")
    else:
        print("  [OK] 换手率在合理范围")
    print()


def demo_exposure():
    """[2] Exposure 暴露分析"""
    print("=" * 60)
    print("[2] ExposureAnalyzer - 暴露分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = ExposureAnalyzer()

    result = analyzer.analyze(data["weights_list"])
    print(f"  Long Exposure (avg): {result['long_exposure_avg']:.2%}")
    print(f"  Short Exposure (avg): {result['short_exposure_avg']:.2%}")
    print(f"  Gross Exposure (avg): {result['gross_exposure_avg']:.2%}")
    print(f"  Net Exposure (avg):   {result['net_exposure_avg']:.2%}")

    # 单期分析
    single = analyzer.analyze_single(data["weights_list"][-1])
    print(f"  最新一期 Gross: {single['gross_exposure']:.2%}, Net: {single['net_exposure']:.2%}")
    print()


def demo_benchmark():
    """[3] Benchmark 基准对比"""
    print("=" * 60)
    print("[3] BenchmarkAnalyzer - 基准对比分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = BenchmarkAnalyzer()

    result = analyzer.analyze(data["equity"], data["benchmark"])
    print(f"  Alpha (年化):     {result['alpha_annualized']:.4f}")
    print(f"  Beta:             {result['beta']:.4f}")
    print(f"  Tracking Error:   {result['tracking_error']:.4f}")
    print(f"  Information Ratio:{result['information_ratio']:.4f}")
    print(f"  Correlation:      {result['correlation']:.4f}")
    print(f"  策略总收益:       {result['strategy_total_return']:.2%}")
    print(f"  基准总收益:       {result['benchmark_total_return']:.2%}")
    print(f"  超额收益:         {result['outperformance']:.2%}")
    print()


def demo_attribution():
    """[4] Attribution 归因分析"""
    print("=" * 60)
    print("[4] AttributionAnalyzer - 归因分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = AttributionAnalyzer()

    # 从 fills 分析
    result = analyzer.analyze(data["fills"])
    print(f"  总 PnL:           {result['total_pnl']:.2f}")
    print(f"  盈利 Symbol 数:   {result['winning_symbols']}")
    print(f"  亏损 Symbol 数:   {result['losing_symbols']}")
    print(f"  平均盈利:         {result['avg_win']:.2f}")
    print(f"  平均亏损:         {result['avg_loss']:.2f}")
    print(f"  盈亏比:           {result['win_loss_ratio']:.2f}")
    print(f"  Symbol PnL:")
    for sym, pnl in result["symbol_pnl"].items():
        tag = "[+]" if pnl > 0 else "[-]"
        print(f"    {tag} {sym}: {pnl:.2f}")
    print(f"  Top Contributors: {result['top_contributors'][:3]}")
    print()

    # 从 trades 分析
    trades = [
        {"symbol": "BTC", "entry_price": 28000, "exit_price": 32000, "pnl": 4000},
        {"symbol": "ETH", "entry_price": 2100, "exit_price": 1800, "pnl": -3000},
        {"symbol": "SOL", "entry_price": 90, "exit_price": 120, "pnl": 3000},
    ]
    result2 = analyzer.analyze_trades(trades)
    print(f"  [Trades] 胜率: {result2['win_rate']:.2%}")
    print(f"  [Trades] Profit Factor: {result2['profit_factor']:.2f}")
    print()


def demo_factor_exposure():
    """[5] Factor Exposure 因子暴露"""
    print("=" * 60)
    print("[5] FactorExposureAnalyzer - 因子暴露分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = FactorExposureAnalyzer()

    weights = data["weights_list"][-1]
    factor_values = data["factor_values"]

    result = analyzer.analyze(weights, factor_values)
    print(f"  因子暴露:")
    for factor, exp in result["factor_exposures"].items():
        direction = "偏向" if exp > 0 else "反向"
        magnitude = "严重" if abs(exp) > 0.5 else "轻微"
        print(f"    {factor}: {exp:+.4f} ({magnitude}{direction})")
    print(f"  主导因子: {result['dominant_factor']} ({result['dominant_exposure']:+.4f})")
    print(f"  高暴露因子: {result['high_exposure']}")
    print()


def demo_capacity():
    """[6] Capacity 容量分析"""
    print("=" * 60)
    print("[6] CapacityAnalyzer - 容量分析")
    print("=" * 60)

    data = generate_sample_data()
    analyzer = CapacityAnalyzer()

    # 从 trades 分析
    result = analyzer.analyze(data["fills"])
    print(f"  策略容量:     {result['total_capacity']:,.0f}")
    print(f"  容量等级:     {result['capacity_tier']}")
    for sym, sc in result["symbol_capacity"].items():
        print(f"    {sym}: avg_trade={sc['avg_trade_size']:,.0f}, capacity={sc['estimated_capacity']:,.0f}")

    # 从 weights 分析
    result2 = analyzer.analyze_from_weights(
        pd.DataFrame(data["weights_list"]).fillna(0),
        data["equity"],
    )
    print(f"  [Weights] 策略容量: {result2['total_capacity']:,.0f}")
    print(f"  [Weights] 容量等级: {result2['capacity_tier']}")
    print()


def demo_metric_registry():
    """[7] MetricRegistry 指标注册"""
    print("=" * 60)
    print("[7] MetricRegistry - 指标注册中心")
    print("=" * 60)

    data = generate_sample_data()
    registry = MetricRegistry()

    # 注册内置指标
    registry.register(SharpeMetric)
    registry.register(SortinoMetric)
    registry.register(MaxDDMetric)
    registry.register(ReturnMetric)

    print(f"  已注册指标: {registry.list()}")
    print(f"  按类别: {registry.list_by_category()}")

    # 计算所有指标
    results = registry.compute_all(data["equity"])
    for name, value in results.items():
        print(f"    {name}: {value}")

    # 注册自定义指标
    def custom_metric(equity_curve, **kwargs):
        if len(equity_curve) < 2:
            return 0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        return float(np.median(returns))

    registry.register_function("median_return", custom_metric, category="custom")
    print(f"  自定义指标 median_return: {registry.compute('median_return', data['equity']):.6f}")
    print()


def demo_analytics_engine():
    """[8] AnalyticsEngine 统一分析引擎"""
    print("=" * 60)
    print("[8] AnalyticsEngine - 统一分析引擎")
    print("=" * 60)

    data = generate_sample_data()
    engine = AnalyticsEngine()

    # 运行全部分析
    result = engine.run(
        equity_curve=data["equity"],
        weights_history=data["weights_list"],
        fills=data["fills"],
        benchmark_equity=data["benchmark"],
        factor_values=data["factor_values"],
    )

    # Metrics
    print("  [Metrics]")
    for k, v in result["metrics"].items():
        print(f"    {k}: {v}")

    # Turnover
    print(f"  [Turnover] 年化换手率: {result['turnover']['annual_turnover']:.2%}")

    # Exposure
    print(f"  [Exposure] Gross: {result['exposure']['gross_exposure_avg']:.2%}, Net: {result['exposure']['net_exposure_avg']:.2%}")

    # Attribution
    print(f"  [Attribution] 总 PnL: {result['attribution']['total_pnl']:.2f}")

    # Benchmark
    print(f"  [Benchmark] Alpha: {result['benchmark']['alpha_annualized']:.4f}, IR: {result['benchmark']['information_ratio']:.4f}")

    # Factor Exposure
    print(f"  [FactorExposure] 主导因子: {result['factor_exposure'].get('dominant_factor', 'N/A')}")

    # Capacity
    print(f"  [Capacity] 容量等级: {result['capacity'].get('capacity_tier', 'N/A')}")

    # 保存到文件
    print()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "exp_001")
        saved = engine.run_and_save(
            output_dir=output_dir,
            equity_curve=data["equity"],
            weights_history=data["weights_list"],
            fills=data["fills"],
            benchmark_equity=data["benchmark"],
            factor_values=data["factor_values"],
        )
        print("  [保存结果]")
        for key, path in saved.items():
            print(f"    {key}.json -> {path}")
    print()


def demo_backward_compatibility():
    """[9] 向后兼容: 旧 analytics.py"""
    print("=" * 60)
    print("[9] 向后兼容 - 旧 analytics.py")
    print("=" * 60)

    from quantlab.analytics import sharpe_ratio, max_drawdown, total_return

    data = generate_sample_data()
    equity = data["equity"]

    old_sharpe = sharpe_ratio(equity)
    old_mdd = max_drawdown(equity)
    old_ret = total_return(equity)

    print(f"  旧 sharpe_ratio:  {old_sharpe:.4f}")
    print(f"  旧 max_drawdown:  {old_mdd:.4f}")
    print(f"  旧 total_return:  {old_ret:.4f}")

    # 新 MetricRegistry 对比
    engine = AnalyticsEngine()
    new_metrics = engine.registry.compute_all(equity)

    print(f"  新 SharpeMetric:  {new_metrics['sharpe']:.4f}")
    print(f"  新 MaxDDMetric:   {new_metrics['max_drawdown']:.4f}")
    print(f"  新 ReturnMetric:  {new_metrics['total_return']:.4f}")

    # 验证一致性
    assert abs(old_sharpe - new_metrics["sharpe"]) < 0.01, "Sharpe 不一致!"
    assert abs(old_mdd - new_metrics["max_drawdown"]) < 0.01, "MaxDD 不一致!"
    assert abs(old_ret - new_metrics["total_return"]) < 0.01, "Return 不一致!"
    print("  [OK] 新旧指标计算一致!")
    print()


if __name__ == "__main__":
    print("QuantLab V4.6 Analytics Platform")
    print("从 '赚没赚钱' 到 '为什么赚钱'")
    print()

    demo_turnover()
    demo_exposure()
    demo_benchmark()
    demo_attribution()
    demo_factor_exposure()
    demo_capacity()
    demo_metric_registry()
    demo_analytics_engine()
    demo_backward_compatibility()

    print("=" * 60)
    print("All demos completed!")
    print("=" * 60)
