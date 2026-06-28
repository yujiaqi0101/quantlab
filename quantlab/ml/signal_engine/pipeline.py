"""
Signal Engine Pipeline — 编排 7 步流水线

执行顺序：
1. Calibrator.calibrate
2. Generator.generate → Signal (有 direction)
3. Filter.filter
4. Ranker.rank
5. Scorer.score
6. PositionAllocator.allocate + 设 holding_period
7. 构造 SignalSet

后处理（可选）：
- Registry.register_signal_set (save_to_registry=True 时)
- Validator.validate_signal_set (需提供 returns 数据)

Pipeline 内每步都把中间状态写入 signal.metadata["explain_trace"]。
任何一步失败不中断整体，记入 SignalSet.metadata["errors"]。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .calibrator import get_calibrator
from .filter import build_filters
from .generator import get_generator
from .position_allocator import get_allocator
from .ranker import get_ranker
from .scorer import get_scorer
from .signal import Prediction, Signal, SignalSet

logger = logging.getLogger("quantlab.ml.signal_engine.pipeline")


@dataclass
class PipelineConfig:
    """Pipeline 配置 — 可来自 Template 或自定义"""

    generator: Dict[str, Any] = field(
        default_factory=lambda: {
            "method": "threshold",
            "long_threshold": 0.02,
            "short_threshold": -0.02,
            "use_short": False,
        }
    )
    calibrator: Dict[str, Any] = field(default_factory=lambda: {"method": "none"})
    filters: List[Dict[str, Any]] = field(default_factory=list)
    ranker: Dict[str, Any] = field(default_factory=lambda: {"method": "none"})
    scorer: Dict[str, Any] = field(default_factory=lambda: {"method": "tanh"})
    allocator: Dict[str, Any] = field(default_factory=lambda: {"method": "equal_weight"})
    holding_period: int = 5
    save_to_registry: bool = False
    model_version: str = ""
    dataset_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator": self.generator,
            "calibrator": self.calibrator,
            "filters": self.filters,
            "ranker": self.ranker,
            "scorer": self.scorer,
            "allocator": self.allocator,
            "holding_period": self.holding_period,
            "save_to_registry": self.save_to_registry,
            "model_version": self.model_version,
            "dataset_id": self.dataset_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineConfig":
        return cls(
            generator=d.get("generator", {"method": "threshold"}),
            calibrator=d.get("calibrator", {"method": "none"}),
            filters=d.get("filters", []),
            ranker=d.get("ranker", {"method": "none"}),
            scorer=d.get("scorer", {"method": "tanh"}),
            allocator=d.get("allocator", {"method": "equal_weight"}),
            holding_period=int(d.get("holding_period", 5)),
            save_to_registry=bool(d.get("save_to_registry", False)),
            model_version=d.get("model_version", ""),
            dataset_id=d.get("dataset_id", ""),
        )


class SignalPipeline:
    """Signal Engine 主流水线"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self._errors: List[Dict[str, Any]] = []

    def run(
        self,
        predictions: List[Prediction],
        market_data_provider: Optional[Callable] = None,
    ) -> SignalSet:
        """
        执行 7 步核心流水线。

        Args:
            predictions: 已适配的统一 Prediction 列表
            market_data_provider: 行情数据回调 (symbol, datetime) -> bar dict
        """
        self._errors = []

        # Step 1: Calibrator
        predictions = self._step_calibrate(predictions)

        # Step 2: Generator
        signals = self._step_generate(predictions)

        # 构造初始 SignalSet
        signal_set = SignalSet(
            signals=signals,
            pipeline_config=self.config.to_dict(),
        )

        # Step 3: Filter
        signal_set = self._step_filter(signal_set, market_data_provider)

        # Step 4: Ranker
        signal_set = self._step_rank(signal_set)

        # Step 5: Scorer
        signal_set = self._step_score(signal_set)

        # Step 6: Position Allocator
        signal_set = self._step_allocate(signal_set)

        # Step 7: 构造最终 SignalSet（计算摘要）
        signal_set.compute_summary()
        signal_set.metadata["errors"] = self._errors

        # 后处理：保存到 Registry
        if self.config.save_to_registry:
            self._post_save(signal_set)

        return signal_set

    # ---- 各步骤 ----

    def _step_calibrate(self, predictions: List[Prediction]) -> List[Prediction]:
        try:
            cal = get_calibrator(**self.config.calibrator)
            return cal.calibrate_batch(predictions)
        except Exception as e:
            self._errors.append({"step": "calibrator", "error": str(e)})
            logger.warning(f"Calibrator failed: {e}")
            return predictions

    def _step_generate(self, predictions: List[Prediction]) -> List[Signal]:
        try:
            gen = get_generator(**self.config.generator)
            signals = gen.generate_batch(predictions)
            # 追加溯源
            for s in signals:
                s.add_trace("generator", {"direction": s.direction.value, "generator": gen.name})
            return signals
        except Exception as e:
            self._errors.append({"step": "generator", "error": str(e)})
            logger.error(f"Generator failed: {e}")
            return []

    def _step_filter(self, signal_set: SignalSet, market_data_provider) -> SignalSet:
        if not self.config.filters:
            for s in signal_set.signals:
                s.add_trace("filter", {"passed": True, "filters": []})
            return signal_set
        try:
            # 注入 market_data_provider 到需要它的 filter
            filter_configs = []
            for cfg in self.config.filters:
                c = dict(cfg)
                if "market_data_provider" not in c and market_data_provider:
                    c["market_data_provider"] = market_data_provider
                filter_configs.append(c)
            composite = build_filters(filter_configs)
            new_set = composite.filter(signal_set)
            for s in new_set.signals:
                s.add_trace("filter", {"passed": True})
            return new_set
        except Exception as e:
            self._errors.append({"step": "filter", "error": str(e)})
            logger.warning(f"Filter failed: {e}")
            return signal_set

    def _step_rank(self, signal_set: SignalSet) -> SignalSet:
        try:
            ranker = get_ranker(**self.config.ranker)
            new_set = ranker.rank(signal_set)
            for s in new_set.signals:
                s.add_trace("ranker", {
                    "rank_position": s.metadata.get("rank_position", -1),
                    "ranker": ranker.name,
                })
            return new_set
        except Exception as e:
            self._errors.append({"step": "ranker", "error": str(e)})
            logger.warning(f"Ranker failed: {e}")
            return signal_set

    def _step_score(self, signal_set: SignalSet) -> SignalSet:
        try:
            scorer = get_scorer(**self.config.scorer)
            new_set = scorer.score(signal_set)
            for s in new_set.signals:
                s.add_trace("scorer", {"score": s.score, "scorer": scorer.name})
            return new_set
        except Exception as e:
            self._errors.append({"step": "scorer", "error": str(e)})
            logger.warning(f"Scorer failed: {e}")
            return signal_set

    def _step_allocate(self, signal_set: SignalSet) -> SignalSet:
        try:
            alloc_params = dict(self.config.allocator)
            alloc_params.setdefault("holding_period", self.config.holding_period)
            allocator = get_allocator(**alloc_params)
            new_set = allocator.allocate(signal_set)
            for s in new_set.signals:
                s.add_trace("allocator", {
                    "suggested_weight": s.suggested_weight,
                    "holding_period": s.holding_period,
                    "allocator": allocator.name,
                })
            return new_set
        except Exception as e:
            self._errors.append({"step": "allocator", "error": str(e)})
            logger.warning(f"Allocator failed: {e}")
            return signal_set

    def _post_save(self, signal_set: SignalSet) -> None:
        try:
            from .signal_registry import get_signal_registry
            reg = get_signal_registry()
            reg.register_signal_set(
                signal_set,
                model_version=self.config.model_version,
                dataset_id=self.config.dataset_id,
            )
            signal_set.metadata["saved_to_registry"] = True
        except Exception as e:
            self._errors.append({"step": "registry", "error": str(e)})
            logger.warning(f"Registry save failed: {e}")


# ---- 便捷函数 ----

def run_pipeline(
    predictions: List[Prediction],
    config: Optional[PipelineConfig] = None,
    market_data_provider: Optional[Callable] = None,
) -> SignalSet:
    """一键运行 pipeline"""
    if config is None:
        config = PipelineConfig()
    pipe = SignalPipeline(config)
    return pipe.run(predictions, market_data_provider)
