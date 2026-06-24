# Validation 架构升级计划：从附属步骤到质量控制中心

> 计划日期：2026-06-24
> 状态：待确认
> 范围：ML Lab Validation 模块重构 + Champion Challenge 新增

---

## 一、现状分析

### 1.1 已有基础（可复用）

| 模块 | 位置 | 状态 |
|------|------|------|
| Walk Forward | `ml/validation/walk_forward.py` | 已实现 |
| Stability | `ml/validation/stability.py` | 已实现 |
| Regime | `ml/validation/regime.py` | 已实现 |
| Robustness | `ml/validation/robustness.py` | 已实现 |
| Noise | `ml/validation/noise.py` | 已实现 |
| Benchmark | `ml/validation/benchmark.py` | 已实现 |
| ValidationReport | `ml/validation/report.py` | 已实现（含 score/grade） |
| Lifecycle 状态机 | `ml/registry/lifecycle.py` | 已实现（DRAFT→TRAINING→VALIDATING→VALIDATED→CANDIDATE→CHAMPION→ARCHIVED→DEPRECATED） |
| ChampionManager | `ml/registry/champion.py` | 已实现（challenge 方法） |
| ModelPackage | `ml/registry/package.py` | 已实现 |
| ArtifactStore | `ml/registry/artifacts.py` | 已实现 |

### 1.2 核心缺失

1. **Validation Pipeline + Gate 架构**：当前验证是"一次性调用"，不是"流水线+门禁"
2. **Raw Model 概念**：训练产物没有明确标记为"未验证的原始模型"
3. **ValidationScore 体系**：report.py 有 score 但没有独立 ValidationScore 数据结构
4. **Validation Artifact 持久化**：验证结果没有作为独立产物保存
5. **Champion Challenge 模块**：champion.py 有 challenge 方法但没有独立模块
6. **前端 Validation Dashboard**：ValidationCenter.vue 只是空壳展示页

---

## 二、目标架构

```
Dataset → FeatureSet → LabelSet → Training Plan → Training Run
                                                          ↓
                                                      Raw Model
                                                          ↓
                                                    ★★★★★
                                                Validation Pipeline
                                                   ↓        ↓
                                                Gate1      Gate2      Gate3 ...
                                                Leakage   WalkForward  Benchmark
                                                   ↓        ↓        ↓
                                                ValidationScore (0-100, A-F)
                                                   ↓
                                                PASS → Model Package → Registry (CANDIDATE)
                                                FAIL → Rejected
                                                   ↓
                                                Champion Challenge
                                                   ↓
                                                Promote / Reject
                                                   ↓
                                                Champion → Strategy
```

---

## 三、Tasks List

### Phase 1：后端 Validation Pipeline 核心架构

#### Task 1.1：创建 `ml/validation/pipeline/` 目录结构
- [ ] `pipeline/__init__.py` — 导出
- [ ] `pipeline/core.py` — ValidationPipeline + ValidationContext
- [ ] `pipeline/gate.py` — ValidationGate 基类 + GateResult
- [ ] `pipeline/registry.py` — Gate 注册表（按名称获取 Gate）

**核心接口设计**：
```python
class ValidationGate(ABC):
    name: str
    level: ValidationLevel  # L1-L6
    enabled: bool = True
    def execute(self, ctx: ValidationContext) -> GateResult: ...

class ValidationPipeline:
    gates: List[ValidationGate]
    def run(self, raw_model, dataset, features, labels) -> ValidationReport: ...
```

#### Task 1.2：实现 6 级 Validation Gates
- [ ] `gates/data_gate.py` — L1 Data Validation（缺失值/重复/分布）
- [ ] `gates/training_gate.py` — L2 Training Validation（Loss/Convergence/Overfit Ratio）
- [ ] `gates/timeseries_gate.py` — L3 Time Series Validation（Walk Forward / Rolling / Expanding）
- [ ] `gates/trading_gate.py` — L4 Trading Validation（IC/RankIC/Sharpe/MaxDD/Turnover）
- [ ] `gates/robustness_gate.py` — L5 Robustness Validation（Noise/FeatureDrop/Perturbation/Bootstrap）
- [ ] `gates/benchmark_gate.py` — L6 Benchmark Validation（vs Buy&Hold/Momentum/Random/Champion）

**复用策略**：每个 Gate 内部调用已有的 walk_forward.py / robustness.py / benchmark.py 等，不重写算法。

#### Task 1.3：实现 ValidationScore 体系
- [ ] `pipeline/score.py` — ValidationScore 数据结构
```python
@dataclass
class ValidationScore:
    gate_name: str
    score: float        # 0-100
    grade: str           # A/B/C/D/F
    status: GateStatus   # PASS/WARNING/FAIL/SKIP
    weight: float
    details: dict
```
- [ ] `pipeline/scorer.py` — 综合评分计算器（加权汇总 → Overall Score + Grade）

#### Task 1.4：实现 Validation Artifact 持久化
- [ ] `pipeline/artifacts.py` — ValidationArtifact 保存/加载
```python
validation/
  summary.json
  walkforward.json
  benchmark.json
  robustness.json
  report.html
  plots/
```
- 复用已有 `ArtifactStore`，新增 validation 专用子目录

#### Task 1.5：实现 ValidationReport 升级
- [ ] 升级 `report.py` → 支持 Pipeline 模式输出
- [ ] 新增 `to_html()` 方法生成 Validation Dashboard HTML

### Phase 2：后端 Champion Challenge 模块

#### Task 2.1：创建 `ml/challenge/` 目录
- [ ] `challenge/__init__.py` — 导出
- [ ] `challenge/core.py` — ChampionChallenge 核心类
- [ ] `challenge/comparator.py` — Candidate vs Champion 对比器
- [ ] `challenge/decision.py` — 决策引擎（Promote/Reject 规则）

**核心接口设计**：
```python
class ChampionChallenge:
    def challenge(
        self, candidate_id: str, family: str,
        metrics: List[str],  # ["walk_forward_ic", "sharpe", "max_dd", "robustness"]
    ) -> ChallengeResult: ...
```

**对比维度**：WalkForward IC / Sharpe / MaxDD / Robustness / Benchmark（不是 Accuracy）

### Phase 3：后端 API 端点

#### Task 3.1：Validation Pipeline API
- [ ] `POST /ml/validation/pipeline/run` — 运行完整验证流水线
- [ ] `GET /ml/validation/pipeline/config` — 获取 Gate 配置
- [ ] `PUT /ml/validation/pipeline/config` — 更新 Gate 开关
- [ ] `GET /ml/validation/results/{validation_id}` — 获取验证结果
- [ ] `GET /ml/validation/artifacts/{validation_id}` — 下载验证产物

#### Task 3.2：Champion Challenge API
- [ ] `POST /ml/challenge/run` — 发起 Champion 挑战
- [ ] `GET /ml/challenge/history/{family}` — 挑战历史
- [ ] `GET /ml/challenge/current/{family}` — 当前 Champion

### Phase 4：前端 Validation Dashboard

#### Task 4.1：重构 ValidationCenter.vue
- [ ] 移除空白展示页，改为 Validation Dashboard
- [ ] Gate 配置面板（开关每个 Gate）
- [ ] 运行验证按钮（选择 Raw Model → 运行 Pipeline）
- [ ] Gate 结果展示（每个 Gate 的 Score/Grade/Status）
- [ ] Overall Score 大数字展示
- [ ] Walk Forward 折详情表
- [ ] Benchmark 对比图
- [ ] Robustness 雷达图
- [ ] Artifact 下载入口

#### Task 4.2：新增 Champion Challenge 面板
- [ ] 在 ValidationCenter 内新增 "Champion Challenge" 子标签
- [ ] Candidate 选择 → Champion 选择 → 对比维度选择
- [ ] 对比结果表（Candidate vs Champion 逐项对比）
- [ ] Promote/Reject 决策展示

### Phase 5：ML Lab UI 结构调整

#### Task 5.1：调整 MLLab.vue Tab 顺序
- [ ] 按新 Pipeline 顺序排列：Dataset → Feature → Label → Training → **Validation** → Registry → Strategy
- [ ] Validation tab 标记为"质量控制中心"

### Phase 6：测试

#### Task 6.1：后端单元测试
- [ ] `tests/test_validation_pipeline.py` — Pipeline + Gate 测试
- [ ] `tests/test_champion_challenge.py` — Champion Challenge 测试
- [ ] `tests/test_validation_score.py` — Score 计算测试

#### Task 6.2：端到端测试
- [ ] Training → Validation Pipeline → Registry (CANDIDATE) → Champion Challenge → Promote

---

## 四、Checklist

### 后端
- [ ] `ml/validation/pipeline/` 目录创建完成
- [ ] ValidationPipeline + ValidationGate 基类实现
- [ ] 6 个 Gate 实现完成（L1-L6）
- [ ] ValidationScore 数据结构实现
- [ ] Validation Artifact 持久化实现
- [ ] `ml/challenge/` 目录创建完成
- [ ] ChampionChallenge 核心类实现
- [ ] API 端点实现（validation/pipeline + challenge）
- [ ] `ml/__init__.py` 导出更新
- [ ] 后端单元测试通过

### 前端
- [ ] ValidationCenter.vue 重构为 Dashboard
- [ ] Gate 配置面板实现
- [ ] Gate 结果展示实现
- [ ] Overall Score 展示实现
- [ ] Champion Challenge 面板实现
- [ ] MLLab.vue Tab 顺序调整

### 集成
- [ ] Training → Validation → Registry 流程打通
- [ ] Registry → Champion Challenge 流程打通
- [ ] 端到端测试通过

---

## 五、实施顺序

1. **Phase 1**（后端 Pipeline 核心）— 最高优先级
2. **Phase 2**（Champion Challenge）— 依赖 Phase 1
3. **Phase 3**（API 端点）— 依赖 Phase 1+2
4. **Phase 4**（前端 Dashboard）— 依赖 Phase 3
5. **Phase 5**（UI 调整）— 低优先级
6. **Phase 6**（测试）— 每个 Phase 完成后立即做

---

## 六、复用策略（避免重写）

| 新模块 | 复用已有代码 |
|--------|-------------|
| DataGate | `ml/diagnostics/feature_diagnostics.py` + `label_diagnostics.py` |
| TrainingGate | `ml/training/job.py` 的 TrainingResult |
| TimeseriesGate | `ml/validation/walk_forward.py` |
| TradingGate | `ml/metrics/metrics.py` |
| RobustnessGate | `ml/validation/robustness.py` + `noise.py` |
| BenchmarkGate | `ml/validation/benchmark.py` |
| ValidationScore | `ml/validation/report.py` 的 ValidationItem |
| ChampionChallenge | `ml/registry/champion.py` 的 ChampionManager |
| ArtifactStore | `ml/registry/artifacts.py` |

---

## 七、风险与约束

1. **不破坏现有 API**：已有的 `/ml/validation/walk-forward` 端点保留，新增 `/ml/validation/pipeline/run`
2. **不重写算法**：Gate 内部调用已有模块，只做编排
3. **数据库不变**：复用现有 SQLite 表结构，不新增表
4. **渐进式**：先做后端 Pipeline，前端 Dashboard 可后续迭代
