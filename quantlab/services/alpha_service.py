"""
AlphaService — Alpha Factory 业务入口

V2.0 Service Layer + V3.0 Alpha Factory

统一入口：
  - 生成 Alpha（Generator）
  - 评估 Alpha（Evaluator）
  - 持久化（Store）
  - 排名（Ranking）
  - 候选池（Pool）
  - 相关性（Correlation）
  - 衰减（Decay）
  - 组合（Combiner）
  - 组合构建（Portfolio）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..research.alpha.alpha import Alpha, AlphaMetrics, AlphaStatus, AlphaType
from ..research.alpha.generator import AlphaGenerator
from ..research.alpha.evaluator import AlphaEvaluator
from ..research.alpha.store import AlphaStore
from ..research.alpha.ranking import AlphaRanking
from ..research.alpha.pool import CandidatePool
from ..research.alpha.correlation import AlphaCorrelation
from ..research.alpha.decay import AlphaDecay
from ..research.alpha.combiner import AlphaCombiner
from ..research.alpha.portfolio import AlphaPortfolio
from ..research.alpha_graph.genome import AlphaGenome
from ..research.alpha_graph.similarity import AlphaSimilarity
from ..research.alpha_graph.clustering import AlphaCluster
from ..research.alpha_graph.lineage import AlphaLineage
from ..research.alpha_graph.evolution import AlphaEvolution
from ..research.alpha.cross_section import CrossSectionEvaluator
from ..research.alpha.hybrid import HybridAlpha
from ..research.portfolio_research.portfolio_research import PortfolioResearch
from ..research.regime.regime import RegimeAnalyzer
from ..research.pipeline.pipeline import ResearchPipeline
from ..research.pipeline.context import ResearchContext, PipelineType, PipelineResult
from ..research.pipeline.registry import PipelineRegistry
from ..research.pipeline.executor import PipelineExecutor

logger = logging.getLogger("quantlab.services.alpha")


class AlphaService:
    """
    Alpha 服务（Facade）

    统一入口：API / CLI / Jupyter → AlphaService → Alpha 模块
    """

    def __init__(self) -> None:
        self._generator = AlphaGenerator()
        self._evaluator = AlphaEvaluator()
        self._store = AlphaStore()
        self._ranking = AlphaRanking(self._store)
        self._pool = CandidatePool(self._store)
        self._correlation = AlphaCorrelation(self._store)
        self._decay = AlphaDecay()
        self._combiner = AlphaCombiner()
        self._portfolio = AlphaPortfolio(self._store)
        # V3.0 Alpha Graph
        self._similarity = AlphaSimilarity(self._store)
        self._clustering = AlphaCluster(self._store)
        self._lineage = AlphaLineage(self._store)
        self._evolution = AlphaEvolution(self._store)
        # V3.0 Research Mode
        self._cross_section = CrossSectionEvaluator()
        self._hybrid = HybridAlpha()
        self._portfolio_research = PortfolioResearch(self._store)
        self._regime = RegimeAnalyzer(self._store)
        # V2 Pipeline — 统一研究调度
        self._pipeline_registry = PipelineRegistry()
        self._pipeline_executor = PipelineExecutor(self._pipeline_registry)
        self._pipeline = ResearchPipeline(self._pipeline_registry, self._pipeline_executor)

    # ---- Generator ----

    def generate_alphas(
        self,
        factor_name: str,
        methods: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """从因子批量生成 Alpha"""
        alphas = self._generator.generate(factor_name, methods)
        # 保存到 store
        self._store.save_batch(alphas)
        return [a.to_dict() for a in alphas]

    def generate_batch(
        self,
        factor_names: List[str],
        methods: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """批量生成"""
        result = self._generator.generate_batch(factor_names, methods)
        all_alphas = []
        for alphas in result.values():
            all_alphas.extend(alphas)
        self._store.save_batch(all_alphas)
        return {k: [a.to_dict() for a in v] for k, v in result.items()}

    # ---- Evaluator ----

    def evaluate_alpha(
        self,
        alpha_id: str,
        factor_values: pd.Series,
        price_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """评估单个 Alpha"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return {"error": f"Alpha '{alpha_id}' not found"}

        metrics = self._evaluator.evaluate(alpha, factor_values, price_df)
        alpha.metrics = metrics
        alpha.status = AlphaStatus.EVALUATED

        from datetime import datetime
        alpha.evaluated_at = datetime.now().isoformat()

        self._store.save(alpha)
        return {"alpha_id": alpha_id, "metrics": metrics.to_dict()}

    def evaluate_and_screen(
        self,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        factor_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        批量评估 + 筛选

        1. 从 store 加载未评估的 Alpha
        2. 批量评估
        3. 筛选候选
        """
        # 加载待评估 Alpha
        if factor_name:
            alphas = self._store.list_alphas(limit=10000)
            alphas = [a for a in alphas if a.factor_name == factor_name and a.status == AlphaStatus.DRAFT]
        else:
            alphas = self._store.list_alphas(status="draft", limit=10000)

        if not alphas:
            return {"evaluated": 0, "candidates": 0}

        # 批量评估
        metrics_map = self._evaluator.evaluate_batch(alphas, factor_data, price_df)

        # 更新 Alpha
        from datetime import datetime
        for alpha in alphas:
            if alpha.alpha_id in metrics_map:
                alpha.metrics = metrics_map[alpha.alpha_id]
                alpha.status = AlphaStatus.EVALUATED
                alpha.evaluated_at = datetime.now().isoformat()
                self._store.save(alpha)

        # 筛选候选
        candidates = self._pool.screen(alphas)

        return {
            "evaluated": len(alphas),
            "candidates": len(candidates),
        }

    # ---- Store ----

    def get_alpha(self, alpha_id: str) -> Optional[Dict[str, Any]]:
        """获取 Alpha 详情"""
        alpha = self._store.get(alpha_id)
        return alpha.to_dict() if alpha else None

    def list_alphas(
        self,
        status: Optional[str] = None,
        factor_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出 Alpha"""
        alphas = self._store.list_alphas(status=status, factor_name=factor_name, limit=limit)
        return [a.to_dict() for a in alphas]

    def delete_alpha(self, alpha_id: str) -> bool:
        """删除 Alpha"""
        return self._store.delete(alpha_id)

    def search_alphas(
        self,
        q: str = "",
        ic_min: Optional[float] = None,
        ir_min: Optional[float] = None,
        coverage_min: Optional[float] = None,
        score_min: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """搜索 Alpha"""
        alphas = self._store.search(
            q=q, ic_min=ic_min, ir_min=ir_min,
            coverage_min=coverage_min, score_min=score_min, limit=limit,
        )
        return [a.to_dict() for a in alphas]

    # ---- Ranking ----

    def get_leaderboard(
        self,
        metric: str = "score",
        limit: int = 20,
        factor_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取排行榜"""
        return self._ranking.get_leaderboard(metric=metric, limit=limit, factor_name=factor_name)

    # ---- Pool ----

    def screen_candidates(
        self,
        ic_min: float = 0.03,
        ir_min: float = 0.5,
        coverage_min: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """筛选候选"""
        self._pool.set_criteria({
            "ic_min": ic_min, "ir_min": ir_min, "coverage_min": coverage_min,
        })
        candidates = self._pool.screen()
        return [a.to_dict() for a in candidates]

    def get_candidates(
        self,
        factor_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """获取候选池"""
        alphas = self._pool.get_candidates(factor_name=factor_name, limit=limit)
        return [a.to_dict() for a in alphas]

    def promote_alpha(self, alpha_id: str) -> bool:
        """提升为生产"""
        return self._pool.promote_to_production(alpha_id)

    def get_pool_stats(self) -> Dict[str, Any]:
        """候选池统计"""
        return self._pool.get_pool_stats()

    # ---- Correlation ----

    def compute_correlation(
        self,
        signal_data: Dict[str, pd.Series],
        method: str = "spearman",
    ) -> Dict[str, Any]:
        """计算相关性矩阵"""
        corr_matrix = self._correlation.compute_correlation(signal_data, method)
        return self._correlation.get_heatmap_data(corr_matrix)

    def find_redundant(
        self,
        signal_data: Dict[str, pd.Series],
        threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """找出冗余 Alpha"""
        corr_matrix = self._correlation.compute_correlation(signal_data)
        return self._correlation.find_redundant(corr_matrix, threshold)

    # ---- Decay ----

    def analyze_decay(
        self,
        alpha_id: str,
        factor_values: pd.Series,
        price_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """分析 Alpha 衰减"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return {"error": f"Alpha '{alpha_id}' not found"}
        return self._decay.analyze(alpha, factor_values, price_df)

    # ---- Combiner ----

    def combine_alphas(
        self,
        alpha_ids: List[str],
        method: str = "weighted",
        weights: Optional[Dict[str, float]] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """组合 Alpha"""
        composite = self._combiner.create_composite_alpha(
            alpha_ids, method, weights, name,
        )
        self._store.save(composite)
        return composite.to_dict()

    # ---- Portfolio ----

    def construct_portfolio(
        self,
        method: str = "ic_weight",
        max_alphas: int = 20,
    ) -> Dict[str, Any]:
        """构建组合"""
        return self._portfolio.construct(method=method, max_alphas=max_alphas)

    # ---- Stats / Overview ----

    def get_overview(self) -> Dict[str, Any]:
        """全局概览"""
        stats = self._store.get_stats()
        status_counts = self._store.count_by_status()
        factor_names = self._store.get_factor_names()

        return {
            "total_alphas": stats["total"],
            "candidates": stats["candidates"],
            "top_ic": stats.get("top_ic"),
            "top_ir": stats.get("top_ir"),
            "status_counts": status_counts,
            "factor_names": factor_names,
        }

    def update_alpha_status(self, alpha_id: str, status: str) -> bool:
        """更新状态"""
        return self._store.update_status(alpha_id, status)

    def update_alpha_tags(self, alpha_id: str, tags: List[str]) -> bool:
        """更新标签"""
        return self._store.update_tags(alpha_id, tags)

    def update_alpha_note(self, alpha_id: str, note: str) -> bool:
        """更新备注"""
        return self._store.update_note(alpha_id, note)

    # ---- V3.0 Alpha Graph ----

    # ---- Genome ----

    def get_genome(self, alpha_id: str) -> Optional[Dict[str, Any]]:
        """获取 Alpha 基因组"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return None
        genome = AlphaGenome.from_alpha(alpha)
        return genome.to_dict()

    def diff_genomes(self, alpha_id_1: str, alpha_id_2: str) -> Optional[Dict[str, Any]]:
        """比较两个 Alpha 基因组差异"""
        a1 = self._store.get(alpha_id_1)
        a2 = self._store.get(alpha_id_2)
        if a1 is None or a2 is None:
            return None
        g1 = AlphaGenome.from_alpha(a1)
        g2 = AlphaGenome.from_alpha(a2)
        return g1.diff(g2)

    # ---- Similarity ----

    def compute_similarity(
        self,
        alpha_id_1: str,
        alpha_id_2: str,
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Optional[Dict[str, Any]]:
        """计算两个 Alpha 的多维相似度"""
        a1 = self._store.get(alpha_id_1)
        a2 = self._store.get(alpha_id_2)
        if a1 is None or a2 is None:
            return None
        return self._similarity.compute(a1, a2, signal_data)

    def find_similar_alphas(
        self,
        alpha_id: str,
        threshold: float = 0.8,
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> List[Dict[str, Any]]:
        """找出与目标 Alpha 相似的其他 Alpha"""
        target = self._store.get(alpha_id)
        if target is None:
            return []
        alphas = self._store.list_alphas(limit=10000)
        return self._similarity.find_similar(target, alphas, threshold, signal_data)

    # ---- Clustering ----

    def cluster_alphas(
        self,
        n_clusters: Optional[int] = None,
        method: str = "genome",
    ) -> Dict[str, Any]:
        """聚类 Alpha"""
        return self._clustering.cluster(n_clusters=n_clusters, method=method)

    # ---- Lineage ----

    def get_ancestors(self, alpha_id: str) -> List[Dict[str, Any]]:
        """获取 Alpha 祖先链"""
        return self._lineage.get_ancestors(alpha_id)

    def get_children(self, alpha_id: str) -> List[Dict[str, Any]]:
        """获取 Alpha 子节点"""
        return self._lineage.get_children(alpha_id)

    def get_family_tree(self, alpha_id: str) -> Dict[str, Any]:
        """获取 Family Tree"""
        return self._lineage.get_family_tree(alpha_id)

    def get_graph_data(self, alpha_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取图可视化数据（节点 + 边）"""
        return self._lineage.get_graph_data(alpha_ids)

    def get_lineage_stats(self) -> Dict[str, Any]:
        """血缘统计"""
        return self._lineage.get_lineage_stats()

    # ---- Evolution ----

    def evolve_alpha(
        self,
        parent_alpha_id: str,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        mutations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """进化单个 Alpha"""
        return self._evolution.evolve(parent_alpha_id, factor_data, price_df, mutations)

    def evolve_batch(
        self,
        alpha_ids: List[str],
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        mutations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """批量进化"""
        return self._evolution.evolve_batch(alpha_ids, factor_data, price_df, mutations)

    def auto_evolve(
        self,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        max_parents: int = 10,
        mutations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """自动进化（从候选池选 top Alpha）"""
        return self._evolution.auto_evolve(factor_data, price_df, max_parents, mutations)

    def evolve_generation(
        self,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        n_generations: int = 3,
        max_parents: int = 10,
    ) -> Dict[str, Any]:
        """多代进化"""
        return self._evolution.evolve_generation(factor_data, price_df, n_generations, max_parents)

    # ---- V3.0 Research Mode ----

    # ---- Cross Section ----

    def evaluate_cross_section(
        self,
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame,
        n_quantiles: int = 5,
    ) -> Dict[str, Any]:
        """截面 Alpha 评估"""
        return self._cross_section.evaluate(factor_values, forward_returns, n_quantiles)

    # ---- Hybrid ----

    def evaluate_hybrid(
        self,
        cross_section_signal: pd.DataFrame,
        time_series_signal: pd.DataFrame,
        forward_returns: pd.DataFrame,
        top_n: int = 50,
        combine_method: str = "and",
    ) -> Dict[str, Any]:
        """混合 Alpha 评估（选股 + 择时）"""
        return self._hybrid.evaluate(
            cross_section_signal, time_series_signal,
            forward_returns, top_n, combine_method=combine_method,
        )

    # ---- Portfolio Research ----

    def compute_weights(
        self,
        alpha_ids: List[str],
        method: str = "ic_weight",
        signal_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """计算 Alpha 权重"""
        return self._portfolio_research.compute_weights(alpha_ids, method, signal_data)

    def compute_contribution(
        self,
        alpha_ids: List[str],
        returns_df: pd.DataFrame,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Alpha 收益贡献归因"""
        return self._portfolio_research.compute_contribution(alpha_ids, returns_df, weights)

    def analyze_stability(
        self,
        alpha_id: str,
        ic_series: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """Alpha 稳定性分析"""
        return self._portfolio_research.analyze_stability(alpha_id, ic_series)

    # ---- Regime ----

    def identify_regimes(
        self,
        price_df: pd.DataFrame,
        window: int = 60,
    ) -> Dict[str, Any]:
        """识别市场状态"""
        return self._regime.identify_regimes(price_df, window)

    def analyze_alpha_regime(
        self,
        alpha_id: str,
        price_df: pd.DataFrame,
        factor_values: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """分析 Alpha 在不同市场环境下的表现"""
        alpha = self._store.get(alpha_id)
        if alpha is None:
            return {"error": f"Alpha '{alpha_id}' not found"}
        return self._regime.analyze_alpha_performance(alpha, price_df, factor_values)

    def analyze_alpha_regime_batch(
        self,
        alpha_ids: List[str],
        price_df: pd.DataFrame,
        factor_data: Optional[Dict[str, pd.Series]] = None,
    ) -> Dict[str, Any]:
        """批量分析 Alpha 环境适应性"""
        return self._regime.analyze_alpha_batch(alpha_ids, price_df, factor_data)

    # ---- V2 Pipeline — 统一研究调度 ----

    def run_pipeline(self, context: ResearchContext) -> PipelineResult:
        """
        执行 Research Pipeline

        所有研究 = Pipeline 执行
        三种模式：SINGLE_EXPERIMENT / PARAMETER_SWEEP / ALPHA_BATCH
        """
        return self._pipeline.run(context)

    def run_single(
        self,
        name: str = "",
        dataset_id: str = "default",
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        factors: Optional[List[Dict[str, Any]]] = None,
        strategy_id: str = "",
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        便捷方法：单实验 Pipeline

        用法：
            result = svc.run_single(
                name="rsi_test",
                factors=[{"name": "RSI", "params": {"period": 14}}],
                strategy_id="ma_cross",
                strategy_params={"fast": 5, "slow": 20},
            )
        """
        from ..research.pipeline.context import FactorConfig, StrategyConfig
        factor_configs = [FactorConfig(**f) for f in (factors or [])]
        strategy_config = StrategyConfig(
            strategy_id=strategy_id,
            params=strategy_params or {},
        ) if strategy_id else None

        ctx = ResearchContext(
            name=name,
            pipeline_type=PipelineType.SINGLE_EXPERIMENT,
            dataset_id=dataset_id,
            symbols=symbols,
            start=start,
            end=end,
            factors=factor_configs,
            strategy=strategy_config,
        )
        return self._pipeline.run(ctx)

    def run_sweep(
        self,
        name: str = "",
        dataset_id: str = "default",
        strategy_id: str = "",
        param_space: Optional[Dict[str, List[Any]]] = None,
        metric: str = "sharpe",
        top_n: int = 10,
        strategy_params: Optional[Dict[str, Any]] = None,
    ) -> PipelineResult:
        """
        便捷方法：参数扫描 Pipeline

        用法：
            result = svc.run_sweep(
                strategy_id="ma_cross",
                param_space={"fast": [5,10,20], "slow": [60,120]},
            )
        """
        from ..research.pipeline.context import StrategyConfig, SweepConfig
        strategy_config = StrategyConfig(
            strategy_id=strategy_id,
            params=strategy_params or {},
        ) if strategy_id else None

        ctx = ResearchContext(
            name=name,
            pipeline_type=PipelineType.PARAMETER_SWEEP,
            dataset_id=dataset_id,
            strategy=strategy_config,
            sweep=SweepConfig(
                param_space=param_space or {},
                metric=metric,
                top_n=top_n,
            ),
        )
        return self._pipeline.run(ctx)

    def run_alpha_batch(
        self,
        name: str = "",
        factor_names: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
        ic_min: float = 0.03,
        ir_min: float = 0.5,
    ) -> PipelineResult:
        """
        便捷方法：Alpha 批处理 Pipeline

        用法：
            result = svc.run_alpha_batch(
                factor_names=["RSI", "MA"],
                methods=["threshold", "cross"],
            )
        """
        from ..research.pipeline.context import AlphaBatchConfig
        ctx = ResearchContext(
            name=name,
            pipeline_type=PipelineType.ALPHA_BATCH,
            alpha_batch=AlphaBatchConfig(
                factor_names=factor_names or [],
                methods=methods or ["threshold"],
                ic_min=ic_min,
                ir_min=ir_min,
            ),
        )
        return self._pipeline.run(ctx)

    def get_pipeline_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """查询 Pipeline 执行历史"""
        results = self._pipeline.history(limit)
        return [r.to_dict() for r in results]

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Pipeline 统计信息"""
        return self._pipeline.stats()
