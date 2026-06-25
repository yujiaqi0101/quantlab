"""
因子库 (factors)
================

目录结构:
    operators/   — 算子库（时序/截面/统计/平滑/回归/工具）
    alpha191/    — 国泰君安 Alpha191 因子（191 个）
    alpha101/    — WorldQuant Alpha101 因子（101 个）
    context.py   — FactorContext 数据上下文

因子函数签名约定:
    def alpha_XXX(ctx: FactorContext) -> pd.DataFrame
    输入输出统一为 pd.DataFrame (index=date, columns=symbol)
"""
