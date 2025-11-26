import json
import numpy as np
from collections import defaultdict

# Load mesh.json configuration
with open('teccl/examples/sample_inputs/mesh.json', 'r') as f:
    config = json.load(f)

# Extract parameters
total_data_MB = config['TopologyParams']['total_data_MB']
side_length = config['TopologyParams']['side_length']
user_num_chunks = config['InstanceParams']['num_chunks']

# Calculate derived values
devices = side_length ** 2  # 4x4 = 16 nodes
gpus = devices  # Mesh has no switches
total_data_GB = total_data_MB / 1024.0

# Simulate the num_chunks adjustment (from scheduler.py get_solver)
adjusted_num_chunks = user_num_chunks * gpus  # 1 * 16 = 16

# Calculate chunk_size (from scheduler.py __init__)
chunk_size = total_data_GB / (devices * user_num_chunks)

print("="*70)
print("AlltoAll Configuration Analysis")
print("="*70)
print(f"\n【输入参数】")
print(f"  - total_data_MB: {total_data_MB} MB")
print(f"  - total_data_GB: {total_data_GB} GB")
print(f"  - side_length: {side_length} (mesh topology)")
print(f"  - devices (nodes): {devices}")
print(f"  - user_num_chunks: {user_num_chunks}")
print(f"  - GPUs (non-switch nodes): {gpus}")

print(f"\n【Scheduler 计算】")
print(f"  - chunk_size = {total_data_GB} / ({devices} * {user_num_chunks}) = {chunk_size} GB")
print(f"  - adjusted_num_chunks = {user_num_chunks} * {gpus} = {adjusted_num_chunks}")

print(f"\n【Demand 生成逻辑】")
print(f"  - chunks_per_gpu: {adjusted_num_chunks}")
print(f"  - device_chunk_map: {{0:0, 1:1, ..., 15:15}}")

# Simulate demand generation
demand = np.zeros((devices, devices, adjusted_num_chunks), dtype=np.int32)
device_chunk_map = defaultdict(int)
idx = 0
for d in range(devices):
    device_chunk_map[d] = idx
    idx += 1

chunk_assignments = []
for s in range(devices):
    for t in range(devices):
        if s == t:
            continue
        for c in range(adjusted_num_chunks // gpus):
            chunk_id = device_chunk_map[t] + c * gpus
            demand[s][t][chunk_id] = 1
            chunk_assignments.append((s, t, chunk_id))

print(f"\n【每个节点的发送模式】")
print(f"  - chunks_per_gpu // gpus = {adjusted_num_chunks} // {gpus} = {adjusted_num_chunks // gpus}")
print(f"  - 即：每个节点向其他每个节点发送 {adjusted_num_chunks // gpus} 个 chunk")

# Analyze for node 0
node_0_sends = [(t, c) for s, t, c in chunk_assignments if s == 0]
print(f"\n【节点 0 的发送详情】")
print(f"  - 总共发送到 {len(set(t for t, c in node_0_sends))} 个目标节点")
print(f"  - 发送的 chunk 数量: {len(node_0_sends)}")
print(f"  - 前 5 个发送: {node_0_sends[:5]}")

# Calculate data size per chunk
data_per_chunk = chunk_size  # Each chunk is chunk_size GB
total_data_sent_by_one_node = len(node_0_sends) * data_per_chunk

print(f"\n【数据量计算】")
print(f"  - 每个 chunk 的大小: {data_per_chunk} GB = {data_per_chunk * 1024} MB")
print(f"  - 节点 0 总共发送数据: {len(node_0_sends)} chunks × {data_per_chunk} GB = {total_data_sent_by_one_node} GB")
print(f"  - 节点 0 总共接收数据: {len([1 for s, t, c in chunk_assignments if t == 0])} chunks × {data_per_chunk} GB")

print(f"\n【验证你的理解】")
print(f"  问：每个节点有 15 个 1/16 GB 的数据块要发送到其他 15 个节点？")
print(f"  答：{'✅ 正确' if (len(node_0_sends) == 15 and abs(data_per_chunk - 1/16) < 1e-6) else '❌ 不正确'}")
print(f"      - 实际：每个节点向其他 {len(set(t for t, c in node_0_sends))} 个节点")
print(f"      - 每个目标节点发送 {adjusted_num_chunks // gpus} 个 chunk")
print(f"      - 每个 chunk 大小: {data_per_chunk} GB = 1/{int(1/data_per_chunk)} GB")
print(f"      - 总发送: {len(node_0_sends)} 个 chunk")

print(f"\n【总网络流量】")
total_chunks = len(chunk_assignments)
total_network_data = total_chunks * data_per_chunk
print(f"  - 总 chunk 传输次数: {total_chunks}")
print(f"  - 总网络数据传输量: {total_network_data} GB")
print(f"  - 每个节点接收的数据: {total_data_sent_by_one_node} GB")

print("="*70)
