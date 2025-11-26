#!/usr/bin/env python3
"""
测试脚本：验证 _print_result_summary 方法的输出
"""

# 模拟 schedule_data
schedule_data = {
    "1-Epoch_Duration": 0.00125,
    "2-Expected_Epoch_Duration": 0.00125,
    "3-Epochs_Required": 35,
    "4-Collective_Finish_Time": 0.043750000000000004,
    "5-Algo_Bandwidth": 22.857142857142854,
    "Solver_Time": 52.85
}

# 复制 _print_result_summary 的实现
def print_result_summary(schedule_data):
    """打印调度结果的关键指标摘要（带单位）"""
    epoch_duration = schedule_data.get("1-Epoch_Duration", "N/A")
    expected_epoch_duration = schedule_data.get("2-Expected_Epoch_Duration", "N/A")
    epochs_required = schedule_data.get("3-Epochs_Required", "N/A")
    collective_finish_time = schedule_data.get("4-Collective_Finish_Time", "N/A")
    algo_bandwidth = schedule_data.get("5-Algo_Bandwidth", "N/A")
    solver_time = schedule_data.get("Solver_Time", "N/A")
    
    print("\n" + "="*70)
    print("  TE-CCL 调度结果摘要")
    print("="*70)
    print("\n【主要性能指标】")
    
    if epoch_duration != "N/A":
        print(f"  1️⃣  Epoch 时长: {epoch_duration:.6f} 秒 (s)")
    else:
        print(f"  1️⃣  Epoch 时长: {epoch_duration}")
    
    if expected_epoch_duration != "N/A":
        print(f"  2️⃣  预期 Epoch 时长: {expected_epoch_duration:.6f} 秒 (s)")
    else:
        print(f"  2️⃣  预期 Epoch 时长: {expected_epoch_duration}")
    
    print(f"  3️⃣  所需 Epoch 数: {epochs_required} 个")
    
    if collective_finish_time != "N/A":
        print(f"  4️⃣  集合通信完成时间: {collective_finish_time:.6f} 秒 (s)")
        print(f"      = {collective_finish_time * 1000:.3f} 毫秒 (ms)")
    else:
        print(f"  4️⃣  集合通信完成时间: {collective_finish_time}")
    
    if algo_bandwidth != "N/A":
        print(f"  5️⃣  算法带宽: {algo_bandwidth:.2f} GB/s")
    else:
        print(f"  5️⃣  算法带宽: {algo_bandwidth}")
    
    if solver_time != "N/A":
        print(f"\n  ⏱️  求解器用时: {solver_time:.2f} 秒 (s)")
        if solver_time >= 60:
            minutes = int(solver_time // 60)
            seconds = solver_time % 60
            print(f"      = {minutes} 分 {seconds:.1f} 秒")
    
    print("="*70 + "\n")

# 测试
print("模拟 teccl solve 命令运行结束时的输出：")
print("Schedule written to teccl/examples/schedules/ndv2_schedule.json")
print_result_summary(schedule_data)
