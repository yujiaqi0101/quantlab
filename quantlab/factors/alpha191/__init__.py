"""
国泰君安 Alpha191 因子库
=======================

来源: 国泰君安证券《基于短周期价量特征的多因子选股体系》(2017)
共 191 个短周期价量因子，分 8 大类:
    - 量价因子 (volume_price): 32 个
    - 均值回复因子 (mean_reversion): 17 个
    - 动量因子 (momentum): 56 个
    - 波动率因子 (volatility): 26 个
    - 相关性因子 (correlation): 24 个
    - 成交量因子 (volume): 16 个
    - 价格因子 (price): 1 个
    - 基准因子 (benchmark): 4 个

文件命名: alpha_XXX.py (XXX 为三位编号，如 alpha_014.py)
每个因子文件必须包含完整备注 (10 个必填字段)。
"""
from quantlab.factors.alpha191.alpha_014 import alpha_014, DIRECTION as ALPHA014_DIRECTION
from quantlab.factors.alpha191.alpha_015 import alpha_015, DIRECTION as ALPHA015_DIRECTION
from quantlab.factors.alpha191.alpha_054 import alpha_054, DIRECTION as ALPHA054_DIRECTION
from quantlab.factors.alpha191.alpha_070 import alpha_070, DIRECTION as ALPHA070_DIRECTION
from quantlab.factors.alpha191.alpha_076 import alpha_076, DIRECTION as ALPHA076_DIRECTION
from quantlab.factors.alpha191.alpha_095 import alpha_095, DIRECTION as ALPHA095_DIRECTION
from quantlab.factors.alpha191.alpha_097 import alpha_097, DIRECTION as ALPHA097_DIRECTION
from quantlab.factors.alpha191.alpha_100 import alpha_100, DIRECTION as ALPHA100_DIRECTION
from quantlab.factors.alpha191.alpha_118 import alpha_118, DIRECTION as ALPHA118_DIRECTION
from quantlab.factors.alpha191.alpha_127 import alpha_127, DIRECTION as ALPHA127_DIRECTION
from quantlab.factors.alpha191.alpha_137 import alpha_137, DIRECTION as ALPHA137_DIRECTION
from quantlab.factors.alpha191.alpha_158 import alpha_158, DIRECTION as ALPHA158_DIRECTION
from quantlab.factors.alpha191.alpha_161 import alpha_161, DIRECTION as ALPHA161_DIRECTION
from quantlab.factors.alpha191.alpha_165 import alpha_165, DIRECTION as ALPHA165_DIRECTION
from quantlab.factors.alpha191.alpha_175 import alpha_175, DIRECTION as ALPHA175_DIRECTION
from quantlab.factors.alpha191.alpha_183 import alpha_183, DIRECTION as ALPHA183_DIRECTION
from quantlab.factors.alpha191.alpha_188 import alpha_188, DIRECTION as ALPHA188_DIRECTION
from quantlab.factors.alpha191.alpha_189 import alpha_189, DIRECTION as ALPHA189_DIRECTION
# Phase 4 批次1: 动量类
from quantlab.factors.alpha191.alpha_006 import alpha_006, DIRECTION as ALPHA006_DIRECTION
from quantlab.factors.alpha191.alpha_008 import alpha_008, DIRECTION as ALPHA008_DIRECTION
from quantlab.factors.alpha191.alpha_017 import alpha_017, DIRECTION as ALPHA017_DIRECTION
from quantlab.factors.alpha191.alpha_018 import alpha_018, DIRECTION as ALPHA018_DIRECTION
from quantlab.factors.alpha191.alpha_020 import alpha_020, DIRECTION as ALPHA020_DIRECTION
from quantlab.factors.alpha191.alpha_021 import alpha_021, DIRECTION as ALPHA021_DIRECTION
# Phase 4 批次2: 动量/量价/均值回复
from quantlab.factors.alpha191.alpha_024 import alpha_024, DIRECTION as ALPHA024_DIRECTION
from quantlab.factors.alpha191.alpha_027 import alpha_027, DIRECTION as ALPHA027_DIRECTION
from quantlab.factors.alpha191.alpha_028 import alpha_028, DIRECTION as ALPHA028_DIRECTION
from quantlab.factors.alpha191.alpha_029 import alpha_029, DIRECTION as ALPHA029_DIRECTION
from quantlab.factors.alpha191.alpha_038 import alpha_038, DIRECTION as ALPHA038_DIRECTION
# Phase 4 批次3: 动量类
from quantlab.factors.alpha191.alpha_041 import alpha_041, DIRECTION as ALPHA041_DIRECTION
from quantlab.factors.alpha191.alpha_048 import alpha_048, DIRECTION as ALPHA048_DIRECTION
from quantlab.factors.alpha191.alpha_053 import alpha_053, DIRECTION as ALPHA053_DIRECTION
from quantlab.factors.alpha191.alpha_057 import alpha_057, DIRECTION as ALPHA057_DIRECTION
from quantlab.factors.alpha191.alpha_058 import alpha_058, DIRECTION as ALPHA058_DIRECTION
from quantlab.factors.alpha191.alpha_067 import alpha_067, DIRECTION as ALPHA067_DIRECTION
from quantlab.factors.alpha191.alpha_079 import alpha_079, DIRECTION as ALPHA079_DIRECTION
# Phase 4 批次4: 均值回复类
from quantlab.factors.alpha191.alpha_002 import alpha_002, DIRECTION as ALPHA002_DIRECTION
from quantlab.factors.alpha191.alpha_012 import alpha_012, DIRECTION as ALPHA012_DIRECTION
from quantlab.factors.alpha191.alpha_013 import alpha_013, DIRECTION as ALPHA013_DIRECTION
from quantlab.factors.alpha191.alpha_019 import alpha_019, DIRECTION as ALPHA019_DIRECTION
from quantlab.factors.alpha191.alpha_022 import alpha_022, DIRECTION as ALPHA022_DIRECTION
from quantlab.factors.alpha191.alpha_026 import alpha_026, DIRECTION as ALPHA026_DIRECTION
# Phase 4 批次5: 均值回复类
from quantlab.factors.alpha191.alpha_031 import alpha_031, DIRECTION as ALPHA031_DIRECTION
from quantlab.factors.alpha191.alpha_034 import alpha_034, DIRECTION as ALPHA034_DIRECTION
from quantlab.factors.alpha191.alpha_046 import alpha_046, DIRECTION as ALPHA046_DIRECTION
from quantlab.factors.alpha191.alpha_047 import alpha_047, DIRECTION as ALPHA047_DIRECTION
from quantlab.factors.alpha191.alpha_065 import alpha_065, DIRECTION as ALPHA065_DIRECTION
from quantlab.factors.alpha191.alpha_066 import alpha_066, DIRECTION as ALPHA066_DIRECTION
from quantlab.factors.alpha191.alpha_071 import alpha_071, DIRECTION as ALPHA071_DIRECTION
from quantlab.factors.alpha191.alpha_072 import alpha_072, DIRECTION as ALPHA072_DIRECTION
from quantlab.factors.alpha191.alpha_078 import alpha_078, DIRECTION as ALPHA078_DIRECTION
from quantlab.factors.alpha191.alpha_082 import alpha_082, DIRECTION as ALPHA082_DIRECTION
# Phase 4 批次6a: 量价相关性类
from quantlab.factors.alpha191.alpha_001 import alpha_001, DIRECTION as ALPHA001_DIRECTION
from quantlab.factors.alpha191.alpha_003 import alpha_003, DIRECTION as ALPHA003_DIRECTION
from quantlab.factors.alpha191.alpha_005 import alpha_005, DIRECTION as ALPHA005_DIRECTION
from quantlab.factors.alpha191.alpha_007 import alpha_007, DIRECTION as ALPHA007_DIRECTION
from quantlab.factors.alpha191.alpha_011 import alpha_011, DIRECTION as ALPHA011_DIRECTION
from quantlab.factors.alpha191.alpha_016 import alpha_016, DIRECTION as ALPHA016_DIRECTION
from quantlab.factors.alpha191.alpha_032 import alpha_032, DIRECTION as ALPHA032_DIRECTION
from quantlab.factors.alpha191.alpha_035 import alpha_035, DIRECTION as ALPHA035_DIRECTION
from quantlab.factors.alpha191.alpha_036 import alpha_036, DIRECTION as ALPHA036_DIRECTION
from quantlab.factors.alpha191.alpha_040 import alpha_040, DIRECTION as ALPHA040_DIRECTION
from quantlab.factors.alpha191.alpha_042 import alpha_042, DIRECTION as ALPHA042_DIRECTION
# Phase 4 批次6b: 量价相关性类剩余
from quantlab.factors.alpha191.alpha_043 import alpha_043, DIRECTION as ALPHA043_DIRECTION
from quantlab.factors.alpha191.alpha_044 import alpha_044, DIRECTION as ALPHA044_DIRECTION
from quantlab.factors.alpha191.alpha_045 import alpha_045, DIRECTION as ALPHA045_DIRECTION
from quantlab.factors.alpha191.alpha_060 import alpha_060, DIRECTION as ALPHA060_DIRECTION
from quantlab.factors.alpha191.alpha_062 import alpha_062, DIRECTION as ALPHA062_DIRECTION
from quantlab.factors.alpha191.alpha_068 import alpha_068, DIRECTION as ALPHA068_DIRECTION
from quantlab.factors.alpha191.alpha_074 import alpha_074, DIRECTION as ALPHA074_DIRECTION
from quantlab.factors.alpha191.alpha_083 import alpha_083, DIRECTION as ALPHA083_DIRECTION
from quantlab.factors.alpha191.alpha_084 import alpha_084, DIRECTION as ALPHA084_DIRECTION
from quantlab.factors.alpha191.alpha_090 import alpha_090, DIRECTION as ALPHA090_DIRECTION
from quantlab.factors.alpha191.alpha_091 import alpha_091, DIRECTION as ALPHA091_DIRECTION
from quantlab.factors.alpha191.alpha_099 import alpha_099, DIRECTION as ALPHA099_DIRECTION
from quantlab.factors.alpha191.alpha_104 import alpha_104, DIRECTION as ALPHA104_DIRECTION
from quantlab.factors.alpha191.alpha_108 import alpha_108, DIRECTION as ALPHA108_DIRECTION
# Phase 4 批次7: 成交量类 + 价格类
from quantlab.factors.alpha191.alpha_080 import alpha_080, DIRECTION as ALPHA080_DIRECTION
from quantlab.factors.alpha191.alpha_081 import alpha_081, DIRECTION as ALPHA081_DIRECTION
from quantlab.factors.alpha191.alpha_102 import alpha_102, DIRECTION as ALPHA102_DIRECTION
from quantlab.factors.alpha191.alpha_111 import alpha_111, DIRECTION as ALPHA111_DIRECTION
from quantlab.factors.alpha191.alpha_120 import alpha_120, DIRECTION as ALPHA120_DIRECTION
from quantlab.factors.alpha191.alpha_124 import alpha_124, DIRECTION as ALPHA124_DIRECTION
from quantlab.factors.alpha191.alpha_126 import alpha_126, DIRECTION as ALPHA126_DIRECTION
from quantlab.factors.alpha191.alpha_128 import alpha_128, DIRECTION as ALPHA128_DIRECTION
from quantlab.factors.alpha191.alpha_132 import alpha_132, DIRECTION as ALPHA132_DIRECTION
from quantlab.factors.alpha191.alpha_134 import alpha_134, DIRECTION as ALPHA134_DIRECTION
from quantlab.factors.alpha191.alpha_145 import alpha_145, DIRECTION as ALPHA145_DIRECTION
from quantlab.factors.alpha191.alpha_150 import alpha_150, DIRECTION as ALPHA150_DIRECTION
from quantlab.factors.alpha191.alpha_155 import alpha_155, DIRECTION as ALPHA155_DIRECTION
from quantlab.factors.alpha191.alpha_168 import alpha_168, DIRECTION as ALPHA168_DIRECTION
from quantlab.factors.alpha191.alpha_178 import alpha_178, DIRECTION as ALPHA178_DIRECTION
from quantlab.factors.alpha191.alpha_191 import alpha_191, DIRECTION as ALPHA191_DIRECTION
# Phase 4 批次8: 动量类 + 波动率类
from quantlab.factors.alpha191.alpha_010 import alpha_010, DIRECTION as ALPHA010_DIRECTION
from quantlab.factors.alpha191.alpha_085 import alpha_085, DIRECTION as ALPHA085_DIRECTION
from quantlab.factors.alpha191.alpha_088 import alpha_088, DIRECTION as ALPHA088_DIRECTION
from quantlab.factors.alpha191.alpha_089 import alpha_089, DIRECTION as ALPHA089_DIRECTION
from quantlab.factors.alpha191.alpha_096 import alpha_096, DIRECTION as ALPHA096_DIRECTION
from quantlab.factors.alpha191.alpha_103 import alpha_103, DIRECTION as ALPHA103_DIRECTION
from quantlab.factors.alpha191.alpha_106 import alpha_106, DIRECTION as ALPHA106_DIRECTION
from quantlab.factors.alpha191.alpha_107 import alpha_107, DIRECTION as ALPHA107_DIRECTION
from quantlab.factors.alpha191.alpha_109 import alpha_109, DIRECTION as ALPHA109_DIRECTION
from quantlab.factors.alpha191.alpha_112 import alpha_112, DIRECTION as ALPHA112_DIRECTION
from quantlab.factors.alpha191.alpha_116 import alpha_116, DIRECTION as ALPHA116_DIRECTION
from quantlab.factors.alpha191.alpha_117 import alpha_117, DIRECTION as ALPHA117_DIRECTION
from quantlab.factors.alpha191.alpha_144 import alpha_144, DIRECTION as ALPHA144_DIRECTION
from quantlab.factors.alpha191.alpha_160 import alpha_160, DIRECTION as ALPHA160_DIRECTION
from quantlab.factors.alpha191.alpha_174 import alpha_174, DIRECTION as ALPHA174_DIRECTION

__all__ = [
    "alpha_014", "ALPHA014_DIRECTION",
    "alpha_015", "ALPHA015_DIRECTION",
    "alpha_054", "ALPHA054_DIRECTION",
    "alpha_070", "ALPHA070_DIRECTION",
    "alpha_076", "ALPHA076_DIRECTION",
    "alpha_095", "ALPHA095_DIRECTION",
    "alpha_097", "ALPHA097_DIRECTION",
    "alpha_100", "ALPHA100_DIRECTION",
    "alpha_118", "ALPHA118_DIRECTION",
    "alpha_127", "ALPHA127_DIRECTION",
    "alpha_137", "ALPHA137_DIRECTION",
    "alpha_158", "ALPHA158_DIRECTION",
    "alpha_161", "ALPHA161_DIRECTION",
    "alpha_165", "ALPHA165_DIRECTION",
    "alpha_175", "ALPHA175_DIRECTION",
    "alpha_183", "ALPHA183_DIRECTION",
    "alpha_188", "ALPHA188_DIRECTION",
    "alpha_189", "ALPHA189_DIRECTION",
    # Phase 4 批次1
    "alpha_006", "ALPHA006_DIRECTION",
    "alpha_008", "ALPHA008_DIRECTION",
    "alpha_017", "ALPHA017_DIRECTION",
    "alpha_018", "ALPHA018_DIRECTION",
    "alpha_020", "ALPHA020_DIRECTION",
    "alpha_021", "ALPHA021_DIRECTION",
    # Phase 4 批次2
    "alpha_024", "ALPHA024_DIRECTION",
    "alpha_027", "ALPHA027_DIRECTION",
    "alpha_028", "ALPHA028_DIRECTION",
    "alpha_029", "ALPHA029_DIRECTION",
    "alpha_038", "ALPHA038_DIRECTION",
    # Phase 4 批次3
    "alpha_041", "ALPHA041_DIRECTION",
    "alpha_048", "ALPHA048_DIRECTION",
    "alpha_053", "ALPHA053_DIRECTION",
    "alpha_057", "ALPHA057_DIRECTION",
    "alpha_058", "ALPHA058_DIRECTION",
    "alpha_067", "ALPHA067_DIRECTION",
    "alpha_079", "ALPHA079_DIRECTION",
    # Phase 4 批次4
    "alpha_002", "ALPHA002_DIRECTION",
    "alpha_012", "ALPHA012_DIRECTION",
    "alpha_013", "ALPHA013_DIRECTION",
    "alpha_019", "ALPHA019_DIRECTION",
    "alpha_022", "ALPHA022_DIRECTION",
    "alpha_026", "ALPHA026_DIRECTION",
    # Phase 4 批次5
    "alpha_031", "ALPHA031_DIRECTION",
    "alpha_034", "ALPHA034_DIRECTION",
    "alpha_046", "ALPHA046_DIRECTION",
    "alpha_047", "ALPHA047_DIRECTION",
    "alpha_065", "ALPHA065_DIRECTION",
    "alpha_066", "ALPHA066_DIRECTION",
    "alpha_071", "ALPHA071_DIRECTION",
    "alpha_072", "ALPHA072_DIRECTION",
    "alpha_078", "ALPHA078_DIRECTION",
    "alpha_082", "ALPHA082_DIRECTION",
    # Phase 4 批次6a
    "alpha_001", "ALPHA001_DIRECTION",
    "alpha_003", "ALPHA003_DIRECTION",
    "alpha_005", "ALPHA005_DIRECTION",
    "alpha_007", "ALPHA007_DIRECTION",
    "alpha_011", "ALPHA011_DIRECTION",
    "alpha_016", "ALPHA016_DIRECTION",
    "alpha_032", "ALPHA032_DIRECTION",
    "alpha_035", "ALPHA035_DIRECTION",
    "alpha_036", "ALPHA036_DIRECTION",
    "alpha_040", "ALPHA040_DIRECTION",
    "alpha_042", "ALPHA042_DIRECTION",
    # Phase 4 批次6b
    "alpha_043", "ALPHA043_DIRECTION",
    "alpha_044", "ALPHA044_DIRECTION",
    "alpha_045", "ALPHA045_DIRECTION",
    "alpha_060", "ALPHA060_DIRECTION",
    "alpha_062", "ALPHA062_DIRECTION",
    "alpha_068", "ALPHA068_DIRECTION",
    "alpha_074", "ALPHA074_DIRECTION",
    "alpha_083", "ALPHA083_DIRECTION",
    "alpha_084", "ALPHA084_DIRECTION",
    "alpha_090", "ALPHA090_DIRECTION",
    "alpha_091", "ALPHA091_DIRECTION",
    "alpha_099", "ALPHA099_DIRECTION",
    "alpha_104", "ALPHA104_DIRECTION",
    "alpha_108", "ALPHA108_DIRECTION",
    # Phase 4 批次7
    "alpha_080", "ALPHA080_DIRECTION",
    "alpha_081", "ALPHA081_DIRECTION",
    "alpha_102", "ALPHA102_DIRECTION",
    "alpha_111", "ALPHA111_DIRECTION",
    "alpha_120", "ALPHA120_DIRECTION",
    "alpha_124", "ALPHA124_DIRECTION",
    "alpha_126", "ALPHA126_DIRECTION",
    "alpha_128", "ALPHA128_DIRECTION",
    "alpha_132", "ALPHA132_DIRECTION",
    "alpha_134", "ALPHA134_DIRECTION",
    "alpha_145", "ALPHA145_DIRECTION",
    "alpha_150", "ALPHA150_DIRECTION",
    "alpha_155", "ALPHA155_DIRECTION",
    "alpha_168", "ALPHA168_DIRECTION",
    "alpha_178", "ALPHA178_DIRECTION",
    "alpha_191", "ALPHA191_DIRECTION",
    # Phase 4 批次8
    "alpha_010", "ALPHA010_DIRECTION",
    "alpha_085", "ALPHA085_DIRECTION",
    "alpha_088", "ALPHA088_DIRECTION",
    "alpha_089", "ALPHA089_DIRECTION",
    "alpha_096", "ALPHA096_DIRECTION",
    "alpha_103", "ALPHA103_DIRECTION",
    "alpha_106", "ALPHA106_DIRECTION",
    "alpha_107", "ALPHA107_DIRECTION",
    "alpha_109", "ALPHA109_DIRECTION",
    "alpha_112", "ALPHA112_DIRECTION",
    "alpha_116", "ALPHA116_DIRECTION",
    "alpha_117", "ALPHA117_DIRECTION",
    "alpha_144", "ALPHA144_DIRECTION",
    "alpha_160", "ALPHA160_DIRECTION",
    "alpha_174", "ALPHA174_DIRECTION",
]
