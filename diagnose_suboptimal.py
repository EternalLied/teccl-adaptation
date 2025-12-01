"""
诊断 TECCL 为什么没有找到 2-epoch 最优解
"""

import json

print("="*70)
print("TECCL 次优解的根本原因分析")
print("="*70)

# 加载实际调度
with open("teccl/examples/schedules/Mesh_4nodes_ALLTOALL_1GB_4chunks.json", "r") as f:
    schedule = json.load(f)

print("\n【问题陈述】")
print("  理论最优: 2 epochs, 100 GB/s")
print("  TECCL 结果: 3 epochs, 66.67 GB/s")
print("  效率损失: 33.3%")

print("\n【根本原因分析】")
print("\n1️⃣  【多跳路由的引入】")
print("  TECCL 的调度使用了多跳路径，而理论最优只需直连。")
print("\n  示例: Chunk 2 从 Node 0 到 Node 2")
print("    理论最优: 0 → 2 (直连, 1 hop)")
print("    TECCL 实际: 0 → 1 → 3 → 2 (3 hops!)")

# 统计路径长度
print("\n  【路径长度统计】")
paths = schedule["8-Chunk paths"]
path_lengths = {}
for demand_key, path_list in paths.items():
    hops = len(path_list[0])
    path_lengths[demand_key] = hops

one_hop = sum(1 for h in path_lengths.values() if h == 1)
two_hop = sum(1 for h in path_lengths.values() if h == 2)
three_hop = sum(1 for h in path_lengths.values() if h == 3)

print(f"    1-hop (直连): {one_hop}/12 = {one_hop/12*100:.1f}%")
print(f"    2-hop (中转): {two_hop}/12 = {two_hop/12*100:.1f}%")
print(f"    3-hop (长路): {three_hop}/12 = {three_hop/12*100:.1f}%")

print("\n2️⃣  【目标函数的问题】")
print("  当前目标函数 (ObjectiveType.PAPER):")
print("    objective = -100 * Σ(demand_sat[s][d][k] / (k+1))")
print("              + 0.02 * Σ(flow[s][i][d][k])")
print("\n  问题:")
print("    ✗ 主要优化 'demand_sat'（需求满足时间）")
print("    ✗ flow 项系数太小 (0.02 vs 100)，几乎无影响")
print("    ✗ 不惩罚多跳路由")
print("    ✗ 不激励链路并行利用")

print("\n3️⃣  【MILP 求解器状态】")
print(f"    Status-10: TIME_LIMIT (时间限制 {0.2}s)")
print(f"    Status-3: INFEASIBLE (在 2-epoch 配置下)")
print("\n  Gurobi 在时间限制内找到可行解但非最优:")
print("    • 可能陷入局部最优")
print("    • 求解树探索不充分")
print("    • 预求解没有识别出结构")

print("\n4️⃣  【num_chunks 调整的影响】")
print("    输入: num_chunks = 1")
print("    调整后: chunks_per_gpu = 1 * 4 (GPUs) = 4")
print("    结果: 每个 (s,d) 对只有 1 个 chunk")
print("\n  这限制了灵活性:")
print("    • 不能将一个需求分成多个 chunk")
print("    • 必须找到完整的 1-chunk 路径")
print("    • 减少了调度的自由度")

print("\n" + "="*70)
print("解决方案建议")
print("="*70)

print("\n【方案 1: 修改目标函数（根本解决）】")
print("  改进方向:")
print("    1. 增加路径长度惩罚:")
print("       objective -= α * Σ(hop_count[s][d][k])")
print("    2. 增加 epoch 利用率激励:")
print("       objective -= β * (epochs_used)")
print("    3. 平衡各项系数（避免 0.02 vs 100 的悬殊）")

print("\n【方案 2: 调整求解器参数】")
print("  修改 mesh.json:")
print("    • time_limit: 0.2 → 5.0 (给更多时间)")
print("    • MIPGap: 添加 0.01 (容忍 1% 的间隙)")
print("    • MIPFocus: 设置为 1 (侧重可行解)")
print("    • Heuristics: 增加到 0.5 (更多启发式)")

print("\n【方案 3: 增加 num_chunks】")
print("  修改 mesh.json:")
print("    • num_chunks: 1 → 4")
print("  效果:")
print("    • chunks_per_gpu = 4 * 4 = 16")
print("    • 每个 (s,d) 对有 4 个 chunk")
print("    • 可以在不同 epoch 发送不同 chunk")
print("    • 增加调度灵活性")

print("\n【方案 4: 尝试不同的 objective_type】")
print("  测试:")
print("    • objective_type: 3 → 1 (BINARY_USED_EPOCHS)")
print("  这会直接优化 epoch 数量")

print("\n" + "="*70)
print("快速测试方案")
print("="*70)

print("\n方案 2+4 组合（最简单）:")
print("""
  修改 mesh.json:
  {
    "GurobiParams": {
      "time_limit": 5.0,
      "mip_gap": 0.01
    },
    "InstanceParams": {
      "objective_type": 1,  // BINARY_USED_EPOCHS
      "num_epochs": 50
    }
  }
  
  然后运行:
  teccl solve --input_args teccl/examples/sample_inputs/mesh.json
""")

print("="*70)
