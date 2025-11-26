import json
from collections import defaultdict

# 加载修复后的调度文件
with open('teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json', 'r') as f:
    data = json.load(f)

flows = data['7-Flows']

print("="*70)
print("分析修复后的 Mesh AlltoAll 调度")
print("="*70)

# 基本统计
print(f"\n【基本信息】")
print(f"  总数据量: {data['0-Total_Data_GB']} GB")
print(f"  Epoch 时长: {data['1-Epoch_Duration']} s")
print(f"  Epoch 数量: {data['3-Epochs_Required']}")
print(f"  完成时间: {data['4-Collective_Finish_Time']} s")
print(f"  算法带宽: {data['5-Algo_Bandwidth']:.2f} GB/s")
print(f"  总流数量: {len(flows)}")

# 重建 chunk→destination 映射
num_nodes = 16
chunks_per_gpu = 16
device_chunk_map = {d: d for d in range(num_nodes)}

chunk_to_device = {}
for s in range(num_nodes):
    for t in range(num_nodes):
        if s == t:
            continue
        for c in range(chunks_per_gpu // num_nodes):
            chunk_id = device_chunk_map[t] + c * num_nodes
            chunk_to_device[(s, chunk_id)] = t

# 解析流，构建路径
chunk_paths = defaultdict(list)
for flow in flows:
    parts = flow.split()
    chunk = int(parts[1])
    source = int(parts[3])
    link = parts[6]
    src_node, dst_node = map(int, link.split('->'))
    epoch = int(parts[-1])
    
    chunk_paths[(source, chunk)].append({
        'from': src_node,
        'to': dst_node,
        'epoch': epoch
    })

# 检查是否还有"短路"连接（跨行的错误邻居）
print(f"\n【检查拓扑连接】")
edges_used = set()
for (source, chunk), hops in chunk_paths.items():
    for hop in hops:
        edge = (hop['from'], hop['to'])
        edges_used.add(edge)

# 检查是否有跨行的边（错误连接）
side_length = 4
invalid_edges = []
for i, j in edges_used:
    i_row, i_col = i // side_length, i % side_length
    j_row, j_col = j // side_length, j % side_length
    
    # 检查是否是有效邻居
    is_valid = False
    if i_row == j_row and abs(i_col - j_col) == 1:  # 同行相邻
        is_valid = True
    elif i_col == j_col and abs(i_row - j_row) == 1:  # 同列相邻
        is_valid = True
    
    if not is_valid:
        invalid_edges.append((i, j))

if invalid_edges:
    print(f"  ❌ 发现 {len(invalid_edges)} 条无效边（跨行连接）:")
    for i, j in invalid_edges[:5]:
        i_row, i_col = i // side_length, i % side_length
        j_row, j_col = j // side_length, j % side_length
        print(f"    {i} ({i_row},{i_col}) -> {j} ({j_row},{j_col})")
else:
    print(f"  ✅ 所有边都是有效的邻居连接（无跨行短路）")

# 计算 Manhattan 距离
def manhattan_distance(src, dst):
    src_r, src_c = src // side_length, src % side_length
    dst_r, dst_c = dst // side_length, dst % side_length
    return abs(src_r - dst_r) + abs(src_c - dst_c)

# 路径长度分析
print(f"\n【路径长度分析】")
shorter_than_optimal = []
equal_to_optimal = []
longer_than_optimal = []

for (source, chunk), hops in chunk_paths.items():
    if (source, chunk) not in chunk_to_device:
        continue
    
    destination = chunk_to_device[(source, chunk)]
    actual_hops = len(hops)
    optimal_hops = manhattan_distance(source, destination)
    
    if actual_hops < optimal_hops:
        shorter_than_optimal.append((source, destination, chunk, actual_hops, optimal_hops))
    elif actual_hops == optimal_hops:
        equal_to_optimal.append((source, destination, chunk, actual_hops, optimal_hops))
    else:
        longer_than_optimal.append((source, destination, chunk, actual_hops, optimal_hops))

print(f"  - 短于 Manhattan 距离: {len(shorter_than_optimal)} 条")
print(f"  - 等于 Manhattan 距离: {len(equal_to_optimal)} 条")
print(f"  - 长于 Manhattan 距离: {len(longer_than_optimal)} 条")

# 总跳数对比
total_actual_hops = sum(len(hops) for hops in chunk_paths.values())
total_optimal_hops = sum(
    manhattan_distance(src, chunk_to_device[(src, chunk)])
    for src, chunk in chunk_paths.keys()
    if (src, chunk) in chunk_to_device
)

print(f"\n【总跳数对比】")
print(f"  - 实际总跳数: {total_actual_hops}")
print(f"  - 理论总跳数 (Manhattan): {total_optimal_hops}")
print(f"  - 差异: {total_actual_hops - total_optimal_hops} 跳")

if total_actual_hops < total_optimal_hops:
    print(f"\n【结论】")
    print(f"  ❌ 问题仍然存在：实际跳数 < 理论最优")
    print(f"  可能原因：拓扑修复未生效或还有其他问题")
elif total_actual_hops == total_optimal_hops:
    print(f"\n【结论】")
    print(f"  ✅✅✅ 完美！实际调度达到了理论最优")
    print(f"  所有路径都使用了最短路径，没有浪费任何跳数")
    print(f"  拓扑 BUG 已成功修复！")
else:
    efficiency = (total_optimal_hops / total_actual_hops) * 100
    print(f"\n【结论】")
    print(f"  ⚠️ 实际跳数 > 理论最优 ({efficiency:.1f}% 效率)")
    print(f"  这是正常的，因为需要考虑链路容量和并发约束")
    
    if longer_than_optimal:
        extra_hops_dist = defaultdict(int)
        for _, _, _, actual, optimal in longer_than_optimal:
            extra = actual - optimal
            extra_hops_dist[extra] += 1
        
        print(f"\n  【额外跳数分布】")
        for extra in sorted(extra_hops_dist.keys()):
            print(f"    +{extra} 跳: {extra_hops_dist[extra]} 条路径")

# 检查是否有流分割
print(f"\n【流分割检查】")
epoch_links = defaultdict(list)
for flow in flows:
    parts = flow.split()
    link = parts[6]
    epoch = int(parts[-1])
    volume = float(parts[9])
    epoch_links[(epoch, link)].append(volume)

duplicates = [(k, v) for k, v in epoch_links.items() if len(v) > 1]
if duplicates:
    print(f"  ❌ 发现 {len(duplicates)} 个 epoch-link 有重复流（可能流分割）")
    for (epoch, link), volumes in duplicates[:3]:
        print(f"    Epoch {epoch}, Link {link}: {volumes}")
else:
    print(f"  ✅ 没有流分割（所有 epoch-link 组合唯一）")

print("="*70)
