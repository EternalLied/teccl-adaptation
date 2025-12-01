"""测试数据大小解析功能"""
import sys
sys.path.insert(0, 'c:/Users/31657/Desktop/TE-CCL')

from teccl.input_data import parse_data_size, TopologyParams

# 测试 parse_data_size 函数
test_cases = [
    ("1KB", 1/1024, "1KB should convert to ~0.001 MB"),
    ("4KB", 4/1024, "4KB"),
    ("256KB", 0.25, "256KB should be 0.25 MB"),
    ("1MB", 1.0, "1MB"),
    ("4MB", 4.0, "4MB"),
    ("1GB", 1024.0, "1GB should be 1024 MB"),
    ("2GB", 2048.0, "2GB"),
    ("1.5GB", 1536.0, "1.5GB should be 1536 MB"),
    ("0.5MB", 0.5, "0.5MB"),
    (1024, 1024.0, "Numeric 1024 should stay 1024 MB"),
    (0.5, 0.5, "Numeric 0.5 should stay 0.5 MB"),
    # 测试不区分大小写和空格
    ("1kb", 1/1024, "Lowercase kb"),
    ("1 GB", 1024.0, "1 GB with space"),
    # 测试简写
    ("1K", 1/1024, "1K shorthand"),
    ("1M", 1.0, "1M shorthand"),
    ("1G", 1024.0, "1G shorthand"),
]

print("="*70)
print("数据大小解析测试")
print("="*70)

passed = 0
failed = 0

for input_val, expected, description in test_cases:
    try:
        result = parse_data_size(input_val)
        if abs(result - expected) < 1e-9:
            print(f"✅ PASS: {description}")
            print(f"   输入: {input_val} → 输出: {result:.10f} MB")
            passed += 1
        else:
            print(f"❌ FAIL: {description}")
            print(f"   输入: {input_val} → 期望: {expected}, 实际: {result}")
            failed += 1
    except Exception as e:
        print(f"❌ ERROR: {description}")
        print(f"   输入: {input_val} → 异常: {e}")
        failed += 1

print("\n" + "="*70)
print(f"测试结果: {passed} 通过, {failed} 失败")
print("="*70)

# 测试 TopologyParams 集成
print("\n" + "="*70)
print("TopologyParams 集成测试")
print("="*70)

test_configs = [
    {"total_data": "1KB"},
    {"total_data": "256KB"},
    {"total_data": "4GB"},
    {"total_data_MB": 1024},  # 传统方式
    {"total_data": "1GB", "total_data_MB": 999},  # total_data 应该覆盖 total_data_MB
]

for i, config in enumerate(test_configs, 1):
    try:
        params = TopologyParams(**config)
        print(f"\n测试 {i}: {config}")
        print(f"  → total_data_MB = {params.total_data_MB}")
    except Exception as e:
        print(f"\n测试 {i}: {config}")
        print(f"  → 错误: {e}")

print("\n" + "="*70)
