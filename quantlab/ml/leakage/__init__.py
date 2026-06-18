"""
Leakage Detector — 数据泄漏检测器

ML Lab 第八部分：检测未来函数 / 数据穿越 / 标签泄漏

  检查：
    - shift(-1) / shift(-N) 等未来函数
    - 标签泄漏（标签使用了未来数据）
    - 训练集和测试集重叠
    - 滚动统计使用了未来数据

  M3 第二部分：FeatureLeakageScanner 扫描 FeatureSet
"""

from .detector import LeakageDetector, LeakageReport, LeakageType, LeakageIssue
from .scanner import FeatureLeakageScanner

__all__ = [
    "LeakageDetector",
    "LeakageReport",
    "LeakageType",
    "LeakageIssue",
    "FeatureLeakageScanner",
]
