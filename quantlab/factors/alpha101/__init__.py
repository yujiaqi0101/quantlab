"""
WorldQuant Alpha101 因子库
==========================

来源: Kakushadze (2015), "101 Formulaic Alphas", Wilmott Magazine.
共 101 个公式化 Alpha 因子。

数据约定:
    - open/high/low/close/volume: 日频 OHLCV
    - returns: 日收益率, 定义为 close/delay(close,1)-1
    - adv{d}: d 日平均成交额 (amount 的 d 日均值)
    - cap: 市值 (部分因子需要)
    - IndClass: 行业分类 (中性化类因子需要)

文件命名: alpha_XXX.py (XXX 为三位编号)
每个因子文件必须包含完整备注 (10 个必填字段)。
"""
from quantlab.factors.alpha101.alpha_001 import alpha_001, DIRECTION as ALPHA001_DIRECTION
from quantlab.factors.alpha101.alpha_002 import alpha_002, DIRECTION as ALPHA002_DIRECTION
from quantlab.factors.alpha101.alpha_003 import alpha_003, DIRECTION as ALPHA003_DIRECTION
from quantlab.factors.alpha101.alpha_004 import alpha_004, DIRECTION as ALPHA004_DIRECTION
from quantlab.factors.alpha101.alpha_005 import alpha_005, DIRECTION as ALPHA005_DIRECTION
from quantlab.factors.alpha101.alpha_006 import alpha_006, DIRECTION as ALPHA006_DIRECTION
from quantlab.factors.alpha101.alpha_007 import alpha_007, DIRECTION as ALPHA007_DIRECTION
from quantlab.factors.alpha101.alpha_008 import alpha_008, DIRECTION as ALPHA008_DIRECTION
from quantlab.factors.alpha101.alpha_009 import alpha_009, DIRECTION as ALPHA009_DIRECTION
from quantlab.factors.alpha101.alpha_010 import alpha_010, DIRECTION as ALPHA010_DIRECTION
from quantlab.factors.alpha101.alpha_011 import alpha_011, DIRECTION as ALPHA011_DIRECTION
from quantlab.factors.alpha101.alpha_012 import alpha_012, DIRECTION as ALPHA012_DIRECTION
from quantlab.factors.alpha101.alpha_013 import alpha_013, DIRECTION as ALPHA013_DIRECTION
from quantlab.factors.alpha101.alpha_014 import alpha_014, DIRECTION as ALPHA014_DIRECTION
from quantlab.factors.alpha101.alpha_015 import alpha_015, DIRECTION as ALPHA015_DIRECTION
from quantlab.factors.alpha101.alpha_016 import alpha_016, DIRECTION as ALPHA016_DIRECTION
from quantlab.factors.alpha101.alpha_017 import alpha_017, DIRECTION as ALPHA017_DIRECTION
from quantlab.factors.alpha101.alpha_018 import alpha_018, DIRECTION as ALPHA018_DIRECTION
from quantlab.factors.alpha101.alpha_019 import alpha_019, DIRECTION as ALPHA019_DIRECTION
from quantlab.factors.alpha101.alpha_020 import alpha_020, DIRECTION as ALPHA020_DIRECTION
from quantlab.factors.alpha101.alpha_021 import alpha_021, DIRECTION as ALPHA021_DIRECTION
from quantlab.factors.alpha101.alpha_022 import alpha_022, DIRECTION as ALPHA022_DIRECTION
from quantlab.factors.alpha101.alpha_023 import alpha_023, DIRECTION as ALPHA023_DIRECTION
from quantlab.factors.alpha101.alpha_024 import alpha_024, DIRECTION as ALPHA024_DIRECTION
from quantlab.factors.alpha101.alpha_025 import alpha_025, DIRECTION as ALPHA025_DIRECTION
from quantlab.factors.alpha101.alpha_026 import alpha_026, DIRECTION as ALPHA026_DIRECTION
from quantlab.factors.alpha101.alpha_027 import alpha_027, DIRECTION as ALPHA027_DIRECTION
from quantlab.factors.alpha101.alpha_028 import alpha_028, DIRECTION as ALPHA028_DIRECTION
from quantlab.factors.alpha101.alpha_029 import alpha_029, DIRECTION as ALPHA029_DIRECTION
from quantlab.factors.alpha101.alpha_030 import alpha_030, DIRECTION as ALPHA030_DIRECTION
from quantlab.factors.alpha101.alpha_031 import alpha_031, DIRECTION as ALPHA031_DIRECTION
from quantlab.factors.alpha101.alpha_032 import alpha_032, DIRECTION as ALPHA032_DIRECTION
from quantlab.factors.alpha101.alpha_033 import alpha_033, DIRECTION as ALPHA033_DIRECTION
from quantlab.factors.alpha101.alpha_034 import alpha_034, DIRECTION as ALPHA034_DIRECTION
from quantlab.factors.alpha101.alpha_035 import alpha_035, DIRECTION as ALPHA035_DIRECTION
from quantlab.factors.alpha101.alpha_036 import alpha_036, DIRECTION as ALPHA036_DIRECTION
from quantlab.factors.alpha101.alpha_037 import alpha_037, DIRECTION as ALPHA037_DIRECTION
from quantlab.factors.alpha101.alpha_038 import alpha_038, DIRECTION as ALPHA038_DIRECTION
from quantlab.factors.alpha101.alpha_039 import alpha_039, DIRECTION as ALPHA039_DIRECTION
from quantlab.factors.alpha101.alpha_040 import alpha_040, DIRECTION as ALPHA040_DIRECTION
from quantlab.factors.alpha101.alpha_041 import alpha_041, DIRECTION as ALPHA041_DIRECTION
from quantlab.factors.alpha101.alpha_042 import alpha_042, DIRECTION as ALPHA042_DIRECTION
from quantlab.factors.alpha101.alpha_043 import alpha_043, DIRECTION as ALPHA043_DIRECTION
from quantlab.factors.alpha101.alpha_044 import alpha_044, DIRECTION as ALPHA044_DIRECTION
from quantlab.factors.alpha101.alpha_045 import alpha_045, DIRECTION as ALPHA045_DIRECTION
from quantlab.factors.alpha101.alpha_046 import alpha_046, DIRECTION as ALPHA046_DIRECTION
from quantlab.factors.alpha101.alpha_047 import alpha_047, DIRECTION as ALPHA047_DIRECTION
from quantlab.factors.alpha101.alpha_049 import alpha_049, DIRECTION as ALPHA049_DIRECTION
from quantlab.factors.alpha101.alpha_050 import alpha_050, DIRECTION as ALPHA050_DIRECTION
from quantlab.factors.alpha101.alpha_051 import alpha_051, DIRECTION as ALPHA051_DIRECTION
from quantlab.factors.alpha101.alpha_052 import alpha_052, DIRECTION as ALPHA052_DIRECTION
from quantlab.factors.alpha101.alpha_053 import alpha_053, DIRECTION as ALPHA053_DIRECTION
from quantlab.factors.alpha101.alpha_054 import alpha_054, DIRECTION as ALPHA054_DIRECTION
from quantlab.factors.alpha101.alpha_055 import alpha_055, DIRECTION as ALPHA055_DIRECTION
from quantlab.factors.alpha101.alpha_057 import alpha_057, DIRECTION as ALPHA057_DIRECTION

__all__ = [
    "alpha_001", "ALPHA001_DIRECTION",
    "alpha_002", "ALPHA002_DIRECTION",
    "alpha_003", "ALPHA003_DIRECTION",
    "alpha_004", "ALPHA004_DIRECTION",
    "alpha_005", "ALPHA005_DIRECTION",
    "alpha_006", "ALPHA006_DIRECTION",
    "alpha_007", "ALPHA007_DIRECTION",
    "alpha_008", "ALPHA008_DIRECTION",
    "alpha_009", "ALPHA009_DIRECTION",
    "alpha_010", "ALPHA010_DIRECTION",
    "alpha_011", "ALPHA011_DIRECTION",
    "alpha_012", "ALPHA012_DIRECTION",
    "alpha_013", "ALPHA013_DIRECTION",
    "alpha_014", "ALPHA014_DIRECTION",
    "alpha_015", "ALPHA015_DIRECTION",
    "alpha_016", "ALPHA016_DIRECTION",
    "alpha_017", "ALPHA017_DIRECTION",
    "alpha_018", "ALPHA018_DIRECTION",
    "alpha_019", "ALPHA019_DIRECTION",
    "alpha_020", "ALPHA020_DIRECTION",
    "alpha_021", "ALPHA021_DIRECTION",
    "alpha_022", "ALPHA022_DIRECTION",
    "alpha_023", "ALPHA023_DIRECTION",
    "alpha_024", "ALPHA024_DIRECTION",
    "alpha_025", "ALPHA025_DIRECTION",
    "alpha_026", "ALPHA026_DIRECTION",
    "alpha_027", "ALPHA027_DIRECTION",
    "alpha_028", "ALPHA028_DIRECTION",
    "alpha_029", "ALPHA029_DIRECTION",
    "alpha_030", "ALPHA030_DIRECTION",
    "alpha_031", "ALPHA031_DIRECTION",
    "alpha_032", "ALPHA032_DIRECTION",
    "alpha_033", "ALPHA033_DIRECTION",
    "alpha_034", "ALPHA034_DIRECTION",
    "alpha_035", "ALPHA035_DIRECTION",
    "alpha_036", "ALPHA036_DIRECTION",
    "alpha_037", "ALPHA037_DIRECTION",
    "alpha_038", "ALPHA038_DIRECTION",
    "alpha_039", "ALPHA039_DIRECTION",
    "alpha_040", "ALPHA040_DIRECTION",
    "alpha_041", "ALPHA041_DIRECTION",
    "alpha_042", "ALPHA042_DIRECTION",
    "alpha_043", "ALPHA043_DIRECTION",
    "alpha_044", "ALPHA044_DIRECTION",
    "alpha_045", "ALPHA045_DIRECTION",
    "alpha_046", "ALPHA046_DIRECTION",
    "alpha_047", "ALPHA047_DIRECTION",
    "alpha_049", "ALPHA049_DIRECTION",
    "alpha_050", "ALPHA050_DIRECTION",
    "alpha_051", "ALPHA051_DIRECTION",
    "alpha_052", "ALPHA052_DIRECTION",
    "alpha_053", "ALPHA053_DIRECTION",
    "alpha_054", "ALPHA054_DIRECTION",
    "alpha_055", "ALPHA055_DIRECTION",
    "alpha_057", "ALPHA057_DIRECTION",
]
