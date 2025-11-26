import numpy as np
from collections import defaultdict

# 4x4 Mesh 拓扑参数
side_length = 4
nodes = side_length ** 2  # 16 nodes
gpus = nodes  # No switches in mesh

print("="*70)
print("4×4 Mesh AlltoAll 理论跳数计算")
print("="*70)

# 构建节点坐标 (row, col)
node_coords = {}
for node_id in range(nodes):
    row = node_id // side_length
    col = node_id % side_length
    node_coords[node_id] = (row, col)

print(f"\n【拓扑信息】")
print(f"  - 节点数: {nodes}")
print(f"  - 拓扑: {side_length}×{side_length} Mesh")
print(f"  - 每个节点坐标:")
for node_id, (r, c) in node_coords.items():
    print(f"    Node {node_id:2d}: ({r}, {c})")

# 计算 Manhattan 距离（最短路径跳数）
def manhattan_distance(src, dst):
    """计算两个节点之间的 Manhattan 距离（最短跳数）"""
    src_r, src_c = node_coords[src]
    dst_r, dst_c = node_coords[dst]
    return abs(src_r - dst_r) + abs(src_c - dst_c)

print(f"\n【AlltoAll 通信模式】")
print(f"  - 每个节点向其他 {nodes - 1} 个节点各发送 1 个 chunk")
print(f"  - 总 chunk 传输: {nodes} × {nodes - 1} = {nodes * (nodes - 1)}")

# 计算所有传输的跳数
hop_distribution = defaultdict(int)
total_hops = 0
total_transmissions = 0

print(f"\n【详细跳数分析】")
for src in range(nodes):
    src_total_hops = 0
    for dst in range(nodes):
        if src == dst:
            continue
        hops = manhattan_distance(src, dst)
        hop_distribution[hops] += 1
        src_total_hops += hops
        total_hops += hops
        total_transmissions += 1
    
    if src < 4:  # 只显示前4个节点的详细信息
        print(f"  Node {src}: 总跳数 = {src_total_hops}, 平均跳数 = {src_total_hops / (nodes - 1):.2f}")

print(f"\n【跳数分布】")
for hops in sorted(hop_distribution.keys()):
    count = hop_distribution[hops]
    percentage = (count / total_transmissions) * 100
    print(f"  {hops} 跳: {count:3d} 次传输 ({percentage:5.2f}%)")

print(f"\n【总体统计】")
print(f"  - 总传输次数: {total_transmissions}")
print(f"  - 总跳数: {total_hops}")
print(f"  - 平均跳数: {total_hops / total_transmissions:.2f}")
print(f"  - 最小跳数: {min(hop_distribution.keys())}")
print(f"  - 最大跳数: {max(hop_distribution.keys())}")

# 验证对称性
print(f"\n【对称性验证】")
per_node_hops = []
for src in range(nodes):
    src_hops = sum(manhattan_distance(src, dst) for dst in range(nodes) if dst != src)
    per_node_hops.append(src_hops)

print(f"  - 每个节点总跳数相同: {len(set(per_node_hops)) == 1}")
if len(set(per_node_hops)) == 1:
    print(f"  - 每个节点总跳数: {per_node_hops[0]}")
else:
    print(f"  - 每个节点总跳数范围: {min(per_node_hops)} - {max(per_node_hops)}")

# 理论下界（如果所有链路都能完美利用）
print(f"\n【理论下界分析】")
total_links = 0
for i in range(nodes):
    r, c = node_coords[i]
    # 计算邻居数量
    neighbors = 0
    if r > 0: neighbors += 1  # 上
    if r < side_length - 1: neighbors += 1  # 下
    if c > 0: neighbors += 1  # 左
    if c < side_length - 1: neighbors += 1  # 右
    total_links += neighbors

# 每条边被计数两次（双向）
total_edges = total_links // 2
print(f"  - Mesh 中的边数: {total_edges}")
print(f"  - 总数据传输量: {total_transmissions} chunks")
print(f"  - 总跳数: {total_hops} hops")
print(f"  - 平均每条边承载: {total_hops / total_edges:.2f} chunks")

print("="*70)
