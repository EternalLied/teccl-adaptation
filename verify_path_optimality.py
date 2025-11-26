import json
from collections import defaultdict

# 加载调度文件
with open('teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json', 'r') as f:
    data = json.load(f)

flows = data['7-Flows']

print("="*70)
print("重新验证：实际跳数 vs 理论最短路径")
print("="*70)

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

# 计算 Manhattan 距离（理论最短路径）
def manhattan_distance(src, dst):
    src_r, src_c = src // 4, src % 4
    dst_r, dst_c = dst // 4, dst % 4
    return abs(src_r - dst_r) + abs(src_c - dst_c)

print(f"\n【详细路径分析】")
print(f"总路径数: {len(chunk_paths)}")

# 分析每条路径
shorter_than_optimal = []
equal_to_optimal = []
longer_than_optimal = []

for (source, chunk), hops in chunk_paths.items():
    actual_hops = len(hops)
    # chunk id 就是目标节点
    destination = chunk
    optimal_hops = manhattan_distance(source, destination)
    
    if actual_hops < optimal_hops:
        shorter_than_optimal.append((source, destination, actual_hops, optimal_hops))
    elif actual_hops == optimal_hops:
        equal_to_optimal.append((source, destination, actual_hops, optimal_hops))
    else:
        longer_than_optimal.append((source, destination, actual_hops, optimal_hops))

print(f"\n【路径比较结果】")
print(f"  - 短于 Manhattan 距离: {len(shorter_than_optimal)} 条")
print(f"  - 等于 Manhattan 距离: {len(equal_to_optimal)} 条")
print(f"  - 长于 Manhattan 距离: {len(longer_than_optimal)} 条")

# 这不应该发生！让我们检查那些"短于最优"的路径
if shorter_than_optimal:
    print(f"\n【异常：短于 Manhattan 距离的路径】")
    print(f"这不应该发生，因为 Manhattan 距离是 Mesh 上的最短路径！")
    print(f"\n让我检查前 5 个案例：")
    
    for i, (src, dst, actual, optimal) in enumerate(shorter_than_optimal[:5]):
        print(f"\n  案例 {i+1}: Node {src} → Node {dst}")
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
        path_hops = chunk_paths[(src, dst)]
        print(f"    - 实际路径: ", end="")
        print(" → ".join([str(path_hops[0]['from'])] + [str(h['to']) for h in path_hops]))

# 重新计算总跳数
total_actual_hops = sum(len(hops) for hops in chunk_paths.values())
total_optimal_hops = sum(manhattan_distance(src, chunk) for src, chunk in chunk_paths.keys())

print(f"\n【总跳数对比】")
print(f"  - 实际总跳数: {total_actual_hops}")
print(f"  - 理论总跳数 (Manhattan): {total_optimal_hops}")
print(f"  - 差异: {total_actual_hops - total_optimal_hops} 跳")

if total_actual_hops < total_optimal_hops:
    print(f"\n【结论】")
    print(f"  ❌ 发现错误：实际跳数小于 Manhattan 距离总和")
    print(f"  可能原因：")
    print(f"    1. Manhattan 距离计算有误")
    print(f"    2. chunk→destination 的映射假设有误")
    print(f"    3. 路径解析有误")
    print(f"\n  让我验证 chunk→destination 的映射...")
elif total_actual_hops == total_optimal_hops:
    print(f"\n【结论】")
    print(f"  ✅ 实际调度达到了理论最优（所有路径都使用最短路径）")
else:
    print(f"\n【结论】")
    print(f"  ⚠️ 实际跳数多于理论最优")
    print(f"  这是正常的，因为要考虑链路容量限制和并发约束")
    efficiency = (total_optimal_hops / total_actual_hops) * 100
    print(f"  路径效率: {efficiency:.1f}%")

print("="*70)
