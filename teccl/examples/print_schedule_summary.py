#!/usr/bin/env python3
"""
TE-CCL 调度结果摘要显示工具
从生成的 schedule JSON 文件中提取关键指标并以带单位的格式显示
"""

import json
import sys
from pathlib import Path


def print_schedule_summary(json_file: str):
    """读取并打印 schedule JSON 的前5项关键结果"""
    
    # 读取 JSON 文件
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 '{json_file}'")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ 错误: 文件 '{json_file}' 不是有效的 JSON 格式")
        sys.exit(1)
    
    # 提取关键字段
    epoch_duration = data.get("1-Epoch_Duration", "N/A")
    expected_epoch_duration = data.get("2-Expected_Epoch_Duration", "N/A")
    epochs_required = data.get("3-Epochs_Required", "N/A")
    collective_finish_time = data.get("4-Collective_Finish_Time", "N/A")
    algo_bandwidth = data.get("5-Algo_Bandwidth", "N/A")
    
    # 计算额外的有用信息
    solver_time = data.get("Solver_Time", "N/A")
    
    # 打印美观的结果
    print("\n" + "="*70)
    print("  TE-CCL 调度结果摘要")
    print("="*70)
    print(f"📁 文件: {Path(json_file).name}")
    print("-"*70)
    
    # 主要结果（前5项）
    print("\n【主要性能指标】")
    print(f"  1️⃣  Epoch 时长 (Epoch Duration)")
    print(f"      {epoch_duration:.6f} 秒 (s)")
    
    print(f"\n  2️⃣  预期 Epoch 时长 (Expected Epoch Duration)")
    print(f"      {expected_epoch_duration:.6f} 秒 (s)")
    
    print(f"\n  3️⃣  所需 Epoch 数 (Epochs Required)")
    print(f"      {epochs_required} 个")
    
    print(f"\n  4️⃣  集合通信完成时间 (Collective Finish Time)")
    if collective_finish_time != "N/A":
        print(f"      {collective_finish_time:.6f} 秒 (s)")
        # 转换为毫秒显示
        print(f"      = {collective_finish_time * 1000:.3f} 毫秒 (ms)")
    else:
        print(f"      {collective_finish_time}")
    
    print(f"\n  5️⃣  算法带宽 (Algorithm Bandwidth)")
    if algo_bandwidth != "N/A":
        print(f"      {algo_bandwidth:.2f} GB/s")
    else:
        print(f"      {algo_bandwidth}")
    
    # 额外信息
    print("\n" + "-"*70)
    print("【额外信息】")
    if solver_time != "N/A":
        print(f"  ⏱️  求解器用时: {solver_time:.2f} 秒 (s)")
        if solver_time >= 60:
            minutes = int(solver_time // 60)
            seconds = solver_time % 60
            print(f"      = {minutes} 分 {seconds:.1f} 秒")
    
    # 计算效率指标
    if epochs_required != "N/A" and epoch_duration != "N/A":
        avg_epoch_time = collective_finish_time / epochs_required if epochs_required > 0 else 0
        print(f"  📊 平均每 Epoch 时间: {avg_epoch_time:.6f} 秒 (s)")
    
    print("\n" + "="*70)
    
    # 返回数据用于进一步处理
    return {
        "epoch_duration": epoch_duration,
        "expected_epoch_duration": expected_epoch_duration,
        "epochs_required": epochs_required,
        "collective_finish_time": collective_finish_time,
        "algo_bandwidth": algo_bandwidth,
        "solver_time": solver_time
    }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python print_schedule_summary.py <schedule.json>")
        print("\n示例:")
        print("  python print_schedule_summary.py teccl/examples/schedules/ndv2_schedule.json")
        sys.exit(1)
    
    json_file = sys.argv[1]
    print_schedule_summary(json_file)


if __name__ == "__main__":
    main()
