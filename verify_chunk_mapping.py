import json
from collections import defaultdict

# 加载调度文件
with open('teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json', 'r') as f:
    data = json.load(f)

flows = data['7-Flows']

print("="*70)
print("正确理解 AlltoAll chunk→destination 映射")
print("="*70)

# 根据 base_formulation.py 中的逻辑重建 device_chunk_map
num_nodes = 16
chunks_per_gpu = 16
gpus = num_nodes  # 没有交换机
device_chunk_map = {}
i = 0
for d in range(num_nodes):
    device_chunk_map[d] = i
    i += 1

print(f"\n【Device→Chunk 映射】")
print(f"device_chunk_map: {device_chunk_map}")

# 反向映射：从 chunk ID 找到目标节点
chunk_to_device = {}
for s in range(num_nodes):
    for t in range(num_nodes):
        if s == t:
            continue
        for c in range(chunks_per_gpu // gpus):
            chunk_id = device_chunk_map[t] + c * gpus
            # 从源节点 s 发送的 chunk_id 的目标是节点 t
            chunk_to_device[(s, chunk_id)] = t

print(f"\n【Chunk→Destination 示例】")
print(f"从节点 0 发送的 chunks:")
for chunk_id in range(chunks_per_gpu):
    if (0, chunk_id) in chunk_to_device:
        dest = chunk_to_device[(0, chunk_id)]
        print(f"  Chunk {chunk_id} → Node {dest}")

# 计算 Manhattan 距离
def manhattan_distance(src, dst):
    src_r, src_c = src // 4, src % 4
    dst_r, dst_c = dst // 4, dst % 4
    return abs(src_r - dst_r) + abs(src_c - dst_c)

# 解析流，构建每个 chunk 的完整路径
chunk_paths = defaultdict(list)
for flow in flows:
    # "Chunk X from Y traveled over A->B in epoch K"
    parts = flow.split()
    chunk = int(parts[1])
    source = int(parts[3])
    link = parts[6]  # "A->B"
    src_node, dst_node = map(int, link.split('->'))
    epoch = int(parts[-1])
    
    chunk_paths[(source, chunk)].append({
        'from': src_node,
        'to': dst_node,
        'epoch': epoch
    })

print(f"\n【路径分析（使用正确的 chunk→destination 映射）】")
print(f"总路径数: {len(chunk_paths)}")

# 分析每条路径
shorter_than_optimal = []
equal_to_optimal = []
longer_than_optimal = []

for (source, chunk), hops in chunk_paths.items():
    actual_hops = len(hops)
    
    # 使用正确的映射找到目标节点
    if (source, chunk) in chunk_to_device:
        destination = chunk_to_device[(source, chunk)]
    else:
        # 这不应该发生
        print(f"  警告：找不到 (source={source}, chunk={chunk}) 的目标节点")
        continue
    
    optimal_hops = manhattan_distance(source, destination)
    
    if actual_hops < optimal_hops:
        shorter_than_optimal.append((source, destination, chunk, actual_hops, optimal_hops))
    elif actual_hops == optimal_hops:
        equal_to_optimal.append((source, destination, chunk, actual_hops, optimal_hops))
    else:
        longer_than_optimal.append((source, destination, chunk, actual_hops, optimal_hops))

print(f"\n【路径比较结果】")
print(f"  - 短于 Manhattan 距离: {len(shorter_than_optimal)} 条")
print(f"  - 等于 Manhattan 距离: {len(equal_to_optimal)} 条")
print(f"  - 长于 Manhattan 距离: {len(longer_than_optimal)} 条")

# 如果还有短于最优的，说明我的理解还是有问题
if shorter_than_optimal:
    print(f"\n【异常：仍然有短于 Manhattan 距离的路径】")
    print(f"前 5 个案例：")
    
    for i, (src, dst, chunk, actual, optimal) in enumerate(shorter_than_optimal[:5]):
        print(f"\n  案例 {i+1}: Node {src} → Node {dst} (Chunk {chunk})")
        print(f"    - 实际跳数: {actual}")
        print(f"    - Manhattan 距离: {optimal}")
        print(f"    - 差异: {actual - optimal}")
        
        # 显示坐标
        src_r, src_c = src // 4, src % 4
        dst_r, dst_c = dst // 4, dst % 4
        print(f"    - 源坐标: ({src_r}, {src_c})")
        print(f"    - 目标坐标: ({dst_r}, {dst_c})")
        print(f"    - Manhattan 计算: |{src_r}-{dst_r}| + |{src_c}-{dst_c}| = {optimal}")
        
        # 显示实际路径
        path_hops = chunk_paths[(src, chunk)]
        print(f"    - 实际路径: ", end="")
        print(" → ".join([str(path_hops[0]['from'])] + [str(h['to']) for h in path_hops]))

# 重新计算总跳数
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
    print(f"  ❌ 仍然存在问题：实际跳数小于 Manhattan 距离总和")
    print(f"  需要进一步调查 chunk→destination 映射逻辑")
elif total_actual_hops == total_optimal_hops:
    print(f"\n【结论】")
    print(f"  ✅ 实际调度达到了理论最优（所有路径都使用最短路径）")
    print(f"  这意味着 MILP 求解器找到了最优解！")
else:
    print(f"\n【结论】")
    print(f"  ⚠️ 实际跳数多于理论最优")
    print(f"  这是正常的，因为要考虑链路容量限制和并发约束")
    efficiency = (total_optimal_hops / total_actual_hops) * 100
    print(f"  路径效率: {efficiency:.1f}%")
    
    # 分析长于最优的路径
    if longer_than_optimal:
        print(f"\n  【长于最优的路径详情】")
        extra_hops = defaultdict(int)
        for _, _, _, actual, optimal in longer_than_optimal:
            extra = actual - optimal
            extra_hops[extra] += 1
        
        print(f"  额外跳数分布:")
        for extra in sorted(extra_hops.keys()):
            print(f"    +{extra} 跳: {extra_hops[extra]} 条路径")

print("="*70)
