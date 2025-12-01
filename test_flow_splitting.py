"""
测试 AlltoAll 求解器的流量分割功能
比较 LP (允许分割) 和 MILP (不允许分割) 的差异
"""

import json
import os
import subprocess
import time

# 准备两个配置文件
config_base = {
    "TopologyParams": {
        "name": "Mesh",
        "chassis": 1,
        "total_data_MB": 1024,
        "side_length": 2
    },
    "GurobiParams": {
        "time_limit": 5.0,
        "output_flag": 0,
        "log_to_console": 0
    },
    "InstanceParams": {
        "collective": 2,
        "num_chunks": 1,
        "epoch_type": 1,
        "epoch_duration": -1,
        "epoch_multiplier": 1,
        "num_epochs": 50,
        "alpha_threshold": 0.1,
        "switch_copy": False,
        "switch_to_gpu_link_on": True,
        "debug": False,
        "debug_output_file": "",
        "objective_type": 3,
        "solution_method": 2,
        "schedule_output_folder": "teccl/examples/schedules"
    }
}

print("="*70)
print("测试 AlltoAll 流量分割功能")
print("="*70)

# 测试 1: MILP (不允许流量分割)
print("\n【测试 1: MILP - 不允许流量分割】")
config_milp = config_base.copy()
config_milp["InstanceParams"]["allow_flow_splitting"] = False

with open("test_milp.json", "w") as f:
    json.dump(config_milp, f, indent=2)

print("  配置: allow_flow_splitting = False")
print("  运行命令: teccl solve --input_args test_milp.json")
start_time = time.time()
result = subprocess.run(
    ["teccl", "solve", "--input_args", "test_milp.json"],
    capture_output=True,
    text=True
)
milp_time = time.time() - start_time

print(f"  求解时间: {milp_time:.2f} 秒")
if "WARNING" in result.stdout:
    for line in result.stdout.split('\n'):
        if "WARNING" in line or "AllToAll" in line:
            print(f"  {line}")
else:
    print("  ✓ 求解成功")

# 测试 2: LP (允许流量分割)
print("\n【测试 2: LP - 允许流量分割】")
config_lp = config_base.copy()
config_lp["InstanceParams"]["allow_flow_splitting"] = True

with open("test_lp.json", "w") as f:
    json.dump(config_lp, f, indent=2)

print("  配置: allow_flow_splitting = True")
print("  运行命令: teccl solve --input_args test_lp.json")
start_time = time.time()
result = subprocess.run(
    ["teccl", "solve", "--input_args", "test_lp.json"],
    capture_output=True,
    text=True
)
lp_time = time.time() - start_time

print(f"  求解时间: {lp_time:.2f} 秒")
if "WARNING" in result.stdout:
    for line in result.stdout.split('\n'):
        if "WARNING" in line or "AllToAll" in line:
            print(f"  {line}")
else:
    print("  ✓ 求解成功")

# 比较结果
print("\n" + "="*70)
print("结果对比")
print("="*70)
print(f"  MILP 求解时间: {milp_time:.2f} 秒")
print(f"  LP 求解时间: {lp_time:.2f} 秒")
print(f"  速度提升: {(milp_time / lp_time - 1) * 100:.1f}%")

print("\n【说明】")
print("  • MILP (整数规划): 不允许流量分割，变量为整数")
print("    - 优点: 调度更实际，每个 chunk 不会被分割")
print("    - 缺点: 求解时间长，可能无法找到全局最优解")
print("\n  • LP (线性规划): 允许流量分割，变量为连续值")
print("    - 优点: 求解快速，更容易找到最优解")
print("    - 缺点: 可能产生分数 chunk，需要后处理")

# 清理临时文件
os.remove("test_milp.json")
os.remove("test_lp.json")

print("\n" + "="*70)
