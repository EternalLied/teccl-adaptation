"""
分析 2×2 Mesh AlltoAll 的理论最优调度
"""

print("="*70)
print("2×2 Mesh AlltoAll 理论最优分析")
print("="*70)

# 拓扑结构
print("\n【拓扑结构】")
print("  节点布局:")
print("    0 - 1")
print("    |   |")
print("    2 - 3")
print("\n  链路: 0-1, 1-0, 0-2, 2-0, 1-3, 3-1, 2-3, 3-2")
print("  每条链路带宽: 50 GB/s")
print("  Epoch 时长: 0.005s")
print("  每 epoch 每链路容量: 50 * 0.005 = 0.25 GB")

# AlltoAll 需求
print("\n【AlltoAll 需求】")
print("  总数据: 1 GB")
print("  每个节点向其他 3 个节点各发送: 1/4 = 0.25 GB")
print("\n  需求矩阵:")
for src in range(4):
    demands = []
    for dst in range(4):
        if src == dst:
            demands.append("  -  ")
        else:
            demands.append("0.25")
    print(f"    Node {src} → [{', '.join(demands)}]")

# 理论最优调度（2 epochs）
print("\n【理论最优调度 - 2 Epochs】")
print("\nEpoch 0:")
print("  Node 0 → Node 1: 0.25 GB (直连)")
print("  Node 1 → Node 0: 0.25 GB (直连)")
print("  Node 2 → Node 3: 0.25 GB (直连)")
print("  Node 3 → Node 2: 0.25 GB (直连)")
print("  总传输: 1.0 GB")
print("  利用率: 4/8 = 50% (4条链路被使用)")

print("\nEpoch 1:")
print("  Node 0 → Node 2: 0.25 GB (直连)")
print("  Node 2 → Node 0: 0.25 GB (直连)")
print("  Node 1 → Node 3: 0.25 GB (直连)")
print("  Node 3 → Node 1: 0.25 GB (直连)")
print("  总传输: 1.0 GB")
print("  利用率: 4/8 = 50%")

print("\n【性能指标】")
print(f"  总时间: 2 × 0.005 = 0.01 秒 (10 ms)")
print(f"  算法带宽: 1.0 / 0.01 = 100 GB/s")
print(f"  链路利用率: 50% (每个 epoch 只用一半链路)")

# TECCL 实际调度（3 epochs）
print("\n" + "="*70)
print("TECCL 实际调度 - 3 Epochs")
print("="*70)
print(f"  总时间: 3 × 0.005 = 0.015 秒 (15 ms)")
print(f"  算法带宽: 1.0 / 0.015 = 66.67 GB/s")
print(f"  效率: 66.67 / 100 = 66.7%")

print("\n【可能的原因】")
print("  1. MILP 求解器未找到全局最优解（Status-10 = TIME_LIMIT）")
print("  2. 目标函数不鼓励并行传输（可能优化不同的指标）")
print("  3. 约束条件可能过于保守（例如 buffer 限制）")
print("  4. 求解时间限制太短（0.2秒）")
print("  5. 初始可行解搜索没有从最优方向开始")

print("\n" + "="*70)
