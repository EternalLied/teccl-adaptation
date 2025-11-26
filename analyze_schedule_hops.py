import json
from collections import defaultdict

# 加载调度文件
with open('teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json', 'r') as f:
    data = json.load(f)

flows = data['7-Flows']
epochs_required = data['3-Epochs_Required']

print("="*70)
print("实际调度 vs 理论最优分析")
print("="*70)

# 解析流
parsed_flows = []
for flow in flows:
    # "Chunk X from Y traveled over A->B in epoch K"
    parts = flow.split()
    chunk = int(parts[1])
    source = int(parts[3])
    link = parts[6]  # "A->B"
    src_node, dst_node = map(int, link.split('->'))
    epoch = int(parts[-1])
    parsed_flows.append({
        'chunk': chunk,
        'source': source,
        'link': (src_node, dst_node),
        'epoch': epoch,
        'flow': flow
    })

print(f"\n【基本信息】")
print(f"  - 实际流数量: {len(flows)}")
print(f"  - 理论最优跳数: 640")
print(f"  - 差距: {640 - len(flows)} 跳 ({(640 - len(flows)) / 640 * 100:.1f}%)")
print(f"  - 所需 Epoch 数: {epochs_required}")

# 统计每个 (source, chunk) 的路径长度
path_lengths = defaultdict(list)
for pf in parsed_flows:
    key = (pf['source'], pf['chunk'])
    path_lengths[key].append(pf['link'])

print(f"\n【路径统计】")
print(f"  - 总路径数: {len(path_lengths)} (应该是 240: 16×15)")
actual_hops = sum(len(links) for links in path_lengths.values())
print(f"  - 实际总跳数: {actual_hops}")
print(f"  - 平均路径长度: {actual_hops / len(path_lengths):.2f} 跳")
print(f"  - 理论平均路径长度: {640 / 240:.2f} 跳")

# 分析路径长度分布
hop_distribution = defaultdict(int)
for links in path_lengths.values():
    hop_distribution[len(links)] += 1

print(f"\n【实际跳数分布】")
for hops in sorted(hop_distribution.keys()):
    count = hop_distribution[hops]
    percentage = (count / len(path_lengths)) * 100
    print(f"  {hops} 跳: {count:3d} 路径 ({percentage:5.2f}%)")

# 对比理论最优分布
print(f"\n【理论最优跳数分布（Manhattan 距离）】")
print(f"  1 跳:  48 路径 (20.00%)")
print(f"  2 跳:  68 路径 (28.33%)")
print(f"  3 跳:  64 路径 (26.67%)")
print(f"  4 跳:  40 路径 (16.67%)")
print(f"  5 跳:  16 路径 ( 6.67%)")
print(f"  6 跳:   4 路径 ( 1.67%)")

# 分析每个 epoch 的流量
epoch_flows = defaultdict(int)
for pf in parsed_flows:
    epoch_flows[pf['epoch']] += 1

print(f"\n【每个 Epoch 的流量分布】")
for epoch in sorted(epoch_flows.keys()):
    count = epoch_flows[epoch]
    print(f"  Epoch {epoch:2d}: {count:3d} 流")

# 检查是否有路径比理论最优更短
print(f"\n【路径效率分析】")

# 计算理论 Manhattan 距离
def manhattan_distance(src, dst):
    src_r, src_c = src // 4, src % 4
    dst_r, dst_c = dst // 4, dst % 4
    return abs(src_r - dst_r) + abs(src_c - dst_c)

# 为每个 (source, chunk) 找到目标节点
# chunk id 对应目标节点（根据之前的分析）
better_paths = 0
equal_paths = 0
worse_paths = 0

for (source, chunk), links in path_lengths.items():
    actual_hops = len(links)
    # 目标节点是 chunk id（根据 AlltoAll 的 demand 生成逻辑）
    destination = chunk
    optimal_hops = manhattan_distance(source, destination)
    
    if actual_hops < optimal_hops:
        better_paths += 1
    elif actual_hops == optimal_hops:
        equal_paths += 1
    else:
        worse_paths += 1
        if worse_paths <= 5:  # 只显示前5个
            print(f"  Node {source} → Node {destination} (chunk {chunk}): "
                  f"实际 {actual_hops} 跳 > 最优 {optimal_hops} 跳")

print(f"\n【路径质量总结】")
print(f"  - 优于理论最优: {better_paths} 路径 ({better_paths/240*100:.1f}%)")
print(f"  - 等于理论最优: {equal_paths} 路径 ({equal_paths/240*100:.1f}%)")
print(f"  - 差于理论最优: {worse_paths} 路径 ({worse_paths/240*100:.1f}%)")

print("="*70)
