# Signal Engine 实施计划（Tasks List）

> 配套设计文档：`docs/plans/2026-06-28-signal-engine-design.md`
> 日期：2026-06-28
> 状态：待实施

## 任务清单

### Phase 1: 基础对象 + 存储
- [ ] T1.1 创建 `quantlab/ml/signal_engine/__init__.py`
- [ ] T1.2 实现 `signal.py`：`Prediction` / `Signal` / `SignalSet` / `SignalDirection`
- [ ] T1.3 实现 `storage.py`：SQLite schema 初始化 + CRUD 原子操作
- [ ] T1.4 实现 `signal_registry.py`：`SignalRegistry` + `SignalVersion`
- [ ] T1.5 单元测试：`test_signal.py` / `test_signal_registry.py`

### Phase 2: 核心生成链
- [ ] T2.1 实现 `prediction_adapter.py`：5 种 adapt 方法 + 批量
- [ ] T2.2 实现 `calibrator.py`：4 种校准器 + 工厂
- [ ] T2.3 实现 `generator.py`：6 种生成器 + 工厂（核心）
- [ ] T2.4 实现 `filter.py`：6 种过滤器 + CompositeFilter
- [ ] T2.5 实现 `ranker.py`：4 种排序器
- [ ] T2.6 实现 `scorer.py`：4 种评分器
- [ ] T2.7 实现 `position_allocator.py`：5 种分配器
- [ ] T2.8 单元测试：每个模块一个 test 文件

### Phase 3: 编排 + 验证
- [ ] T3.1 实现 `pipeline.py`：`PipelineConfig` + `SignalPipeline.run()`
- [ ] T3.2 实现 `signal_validator.py`：`ValidationReport` + `SignalValidator`
- [ ] T3.3 实现 `templates.py`：8 个内置模板
- [ ] T3.4 实现 `explainability.py`：`ExplainTrace` + `ExplainabilityEngine`
- [ ] T3.5 集成测试：`test_pipeline.py` 端到端

### Phase 4: API + 前端
- [ ] T4.1 实现 `quantlab/api/signal_engine.py`：8 个端点
- [ ] T4.2 在 `app.py` 注册 router
- [ ] T4.3 实现 `frontend/src/api/signalEngine.ts`
- [ ] T4.4 实现 `SignalEngine.vue` 主面板
- [ ] T4.5 实现 `SignalRegistry.vue` 仓库面板
- [ ] T4.6 实现 `SignalExplainability.vue` 解释面板
- [ ] T4.7 修改 `MLLab.vue` 插入 Stage 7

### Phase 5: 迁移 + 验证
- [ ] T5.1 标记 `ml/strategy/signal_generator.py` 为 deprecated
- [ ] T5.2 API 端点测试（FastAPI TestClient）
- [ ] T5.3 前端面板手动验证
- [ ] T5.4 全套单元测试通过

## 验收标准 (Definition of Done)

1. ✅ 11 个模块全部实现且有单元测试
2. ✅ Pipeline 端到端跑通：10 个 mock predictions → SignalSet
3. ✅ 所有 API 端点返回 200（无 404）
4. ✅ 前端三个面板可正常渲染
5. ✅ ML Lab Stage 7 顺序正确显示
6. ✅ SQLite 表结构正确创建（不破坏现有表）
7. ✅ 旧 `signal_generator.py` 标记 deprecated 但不破坏现有调用
8. ✅ 无模拟数据写入正式数据库

## 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| Filter 行情数据未接入 | 默认 `BlacklistFilter` 可用，其他透传；后续接入数据源 |
| Calibrator 需历史数据 | 默认 `NoCalibration`，有数据时再 fit |
| 前端面板复杂度高 | 优先实现 SignalEngine.vue 主面板，Registry/Explainability 后做 |
| 旧调用方迁移风险 | 旧 `signal_generator.py` 保留，仅加 deprecated 注释 |
