"""
QuantLab Studio — FastAPI 后端 API

V4.2 Strategy Workspace 的后端支撑

API 端点：
  GET  /api/v1/strategies              策略列表
  GET  /api/v1/strategies/{id}         策略详情
  GET  /api/v1/datasets                数据集列表
  GET  /api/v1/datasets/{name}/symbols 数据集标的
  POST /api/v1/backtests               提交回测
  GET  /api/v1/tasks                   任务列表
  GET  /api/v1/tasks/{id}              任务详情
  GET  /api/v1/experiments/{id}        实验详情
  GET  /api/v1/experiments/{id}/trades 实验交易明细
  POST /api/v1/experiments/compare     实验对比
  WS   /api/v1/ws/tasks               任务实时推送
"""
