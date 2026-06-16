"""
Alpha Evolution Engine — 自动变异 + 评估 + 入池

核心流程：
  1. 选择父 Alpha
  2. 自动变异（阈值/窗口/操作符）
  3. 批量评估
  4. 筛选候选
  5. 记录血缘

这是接近 WorldQuant Alpha 进化体系的核心模块
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..alpha.alpha import Alpha, AlphaStatus
from ..alpha.evaluator import AlphaEvaluator
from ..alpha.store import AlphaStore
from ..alpha.pool import CandidatePool
from .genome import AlphaGenome
from .lineage import AlphaLineage

logger = logging.getLogger("quantlab.alpha_graph.evolution")


class AlphaEvolution:
    """
    Alpha 进化引擎

    用法：
        engine = AlphaEvolution(store)
        result = engine.evolve(
            parent_alpha_id="xxx",
            factor_data=factor_data,
            price_df=price_df,
            mutations=["threshold", "window"],
        )
    """

    def __init__(
        self,
        store: Optional[AlphaStore] = None,
    ) -> None:
        self._store = store or AlphaStore()
        self._evaluator = AlphaEvaluator()
        self._pool = CandidatePool(self._store)
        self._lineage = AlphaLineage(self._store)

    def evolve(
        self,
        parent_alpha_id: str,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        mutations: Optional[List[str]] = None,
        threshold_step: float = 5.0,
        window_steps: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        从父 Alpha 进化出子 Alpha

        参数:
            parent_alpha_id  父 Alpha ID
            factor_data      因子数据
            price_df         价格数据
            mutations        变异类型: ["threshold", "window", "operator"]
            threshold_step   阈值变异步长
            window_steps     窗口变异步长

        返回:
            {"parent": "xxx", "children": [...], "evaluated": 5, "candidates": 2}
        """
        if mutations is None:
            mutations = ["threshold", "window"]

        parent = self._store.get(parent_alpha_id)
        if parent is None:
            return {"error": f"Alpha '{parent_alpha_id}' not found"}

        # 1. 提取基因组
        genome = AlphaGenome.from_alpha(parent)

        # 2. 变异
        child_genomes: List[AlphaGenome] = []
        for mutation in mutations:
            if mutation == "threshold":
                child_genomes.extend(genome.mutate_threshold(threshold_step))
            elif mutation == "window":
                child_genomes.extend(genome.mutate_window(window_steps))
            elif mutation == "operator":
                child_genomes.extend(genome.mutate_operator())

        if not child_genomes:
            return {"parent": parent_alpha_id, "children": [], "evaluated": 0, "candidates": 0}

        # 3. 生成 Alpha 对象
        children: List[Alpha] = []
        for g in child_genomes:
            child_alpha = g.to_alpha()
            if child_alpha.name and child_alpha.factor_name:
                child_alpha.status = AlphaStatus.DRAFT
                children.append(child_alpha)

        # 4. 保存
        self._store.save_batch(children)

        # 5. 记录血缘
        for child in children:
            self._lineage.add_relation(
                parent_alpha_id, child.alpha_id,
                relation_type="evolution",
                metadata={"mutation_types": mutations},
            )

        # 6. 批量评估
        metrics_map = self._evaluator.evaluate_batch(children, factor_data, price_df)

        from datetime import datetime
        for child in children:
            if child.alpha_id in metrics_map:
                child.metrics = metrics_map[child.alpha_id]
                child.status = AlphaStatus.EVALUATED
                child.evaluated_at = datetime.now().isoformat()
                self._store.save(child)

        # 7. 筛选候选
        evaluated = [c for c in children if c.status == AlphaStatus.EVALUATED]
        candidates = self._pool.screen(evaluated)

        logger.info(
            f"evolved from '{parent.name}': {len(children)} children, "
            f"{len(evaluated)} evaluated, {len(candidates)} candidates"
        )

        return {
            "parent_id": parent_alpha_id,
            "parent_name": parent.name,
            "children": [c.to_dict() for c in children],
            "evaluated": len(evaluated),
            "candidates": len(candidates),
        }

    def evolve_batch(
        self,
        alpha_ids: List[str],
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        mutations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        批量进化多个 Alpha

        返回:
            {"total_parents": 5, "total_children": 25, "total_candidates": 8, "results": [...]}
        """
        results = []
        total_children = 0
        total_candidates = 0

        for aid in alpha_ids:
            result = self.evolve(aid, factor_data, price_df, mutations)
            if "error" not in result:
                results.append(result)
                total_children += len(result.get("children", []))
                total_candidates += result.get("candidates", 0)

        return {
            "total_parents": len(alpha_ids),
            "total_children": total_children,
            "total_candidates": total_candidates,
            "results": results,
        }

    def auto_evolve(
        self,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        max_parents: int = 10,
        mutations: Optional[List[str]] = None,
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """
        自动进化：从候选池中选择评分最高的 Alpha 进行进化

        参数:
            factor_data  因子数据
            price_df     价格数据
            max_parents  最多选择多少个父 Alpha
            min_score    最低评分门槛
            mutations    变异类型

        返回:
            进化结果汇总
        """
        # 选择父 Alpha（评分最高的候选）
        candidates = self._store.list_alphas(status="candidate", limit=max_parents * 2)
        candidates = [a for a in candidates if a.metrics.score >= min_score]
        candidates.sort(key=lambda a: a.metrics.score, reverse=True)
        parents = candidates[:max_parents]

        if not parents:
            return {"error": "No eligible parent alphas found"}

        parent_ids = [a.alpha_id for a in parents]
        return self.evolve_batch(parent_ids, factor_data, price_df, mutations)

    def evolve_generation(
        self,
        factor_data: Dict[str, pd.Series],
        price_df: pd.DataFrame,
        n_generations: int = 3,
        max_parents: int = 10,
        mutations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        多代进化

        每一代：选择 top Alpha → 变异 → 评估 → 筛选 → 下一代
        """
        generation_results = []

        for gen in range(n_generations):
            result = self.auto_evolve(factor_data, price_df, max_parents, mutations)
            result["generation"] = gen + 1
            generation_results.append(result)

            if "error" in result:
                break

            logger.info(f"Generation {gen + 1}: {result.get('total_children', 0)} children, {result.get('total_candidates', 0)} candidates")

        return {
            "n_generations": n_generations,
            "generations": generation_results,
            "total_children": sum(g.get("total_children", 0) for g in generation_results),
            "total_candidates": sum(g.get("total_candidates", 0) for g in generation_results),
        }
