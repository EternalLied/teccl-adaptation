"""
分析为什么第三个 epoch (epoch 2) 的 alpha 补偿为 0
"""

import json

print("="*70)
print("第三个 Epoch (epoch 2) Alpha 补偿为 0 的原因分析")
print("="*70)

# 加载调度结果
with open("teccl/examples/schedules/Mesh_4nodes_ALLTOALL_1GB_4chunks.json", "r") as f:
    schedule = json.load(f)

print("\n【基本信息】")
print(f"  Epoch 时长: {schedule['1-Epoch_Duration']} 秒 = {schedule['1-Epoch_Duration']*1e6} μs")
print(f"  Alpha 阈值: {schedule['Alpha_Threshold']}")
print(f"  链路 Alpha: 0.5 μs (所有链路)")
print(f"  阈值判断: alpha/epoch_duration = 0.5μs / 5000μs = 0.0001 ≤ 0.1 ✓ (被忽略)")

print("\n【补偿策略】")
print(f"  策略: {schedule['Compensation_Strategy']}")
print("  说明: 对每个 (source, dest, chunk) 路径，在每个 epoch 累积该路径")
print("        当前 epoch 的所有被忽略 alpha；然后取该 epoch 所有路径的最大值。")

print("\n【各 Epoch 的补偿值】")
for i, comp in enumerate(schedule['Epoch_Compensation_us']):
    print(f"  Epoch {i}: {comp} μs")

print("\n" + "="*70)
print("Epoch 2 的流量分析")
print("="*70)

# 提取 epoch 2 的流量
flows_epoch2 = [f for f in schedule['7-Flows'] if 'epoch 2' in f]
print(f"\n【Epoch 2 的流量列表】({len(flows_epoch2)} 条)")
for i, flow in enumerate(flows_epoch2, 1):
    print(f"  {i}. {flow}")

# 分析每条路径
print("\n【路径级别的 Alpha 累积分析】")
print("\n从 '8-Chunk paths' 中提取在 epoch 2 完成或经过 epoch 2 的路径：")

paths_with_epoch2 = {}
for demand_key, path_list in schedule['8-Chunk paths'].items():
    for path in path_list:
        epochs_in_path = [hop[0] for hop in path]
        if 2 in epochs_in_path:
            paths_with_epoch2[demand_key] = path

print(f"\n共有 {len(paths_with_epoch2)} 条路径涉及 epoch 2:")

for demand_key, path in paths_with_epoch2.items():
    print(f"\n  • {demand_key}")
    epoch2_hops = [hop for hop in path if hop[0] == 2]
    
    if epoch2_hops:
        print(f"    Epoch 2 的跳数: {len(epoch2_hops)}")
        for hop in epoch2_hops:
            epoch, hop_desc = hop
            print(f"      - {hop_desc}")
        
        # 计算该路径在 epoch 2 的累积 alpha
        alpha_sum = len(epoch2_hops) * 0.5  # 每条链路 0.5 μs
        print(f"    ✓ Epoch 2 累积 alpha: {len(epoch2_hops)} hops × 0.5 μs = {alpha_sum} μs")
    else:
        print(f"    (该路径在 epoch 2 之前已完成)")

print("\n" + "="*70)
print("关键发现：为什么 Epoch 2 补偿为 0？")
print("="*70)

print("\n问题的根源在于【路径起点的判断】：")
print("""
  当前补偿策略 (path_epoch_max) 的逻辑：
  
  1. 对于 required_flows 中的每个 flow (s, i, j, c, volume, k)：
     - s: source (数据的原始来源节点)
     - i: 当前跳的发送端
     - j: 当前跳的接收端
     - c: chunk ID
     - k: epoch
  
  2. 判断 j 是否为"最终接收节点"（final_receivers）：
     - final_receivers = {所有非 switch 的接收端 j}
     - 对于 2×2 mesh: final_receivers = {0, 1, 2, 3}（所有节点）
  
  3. 如果 j 在 final_receivers 中：
     - 只将该 alpha 计入路径 (s, j, c) 的 epoch k
     - **认为这是路径的最后一跳**
  
  4. 否则（j 不在 final_receivers，即 j 是 switch）：
     - 将该 alpha 计入所有可能的 (s, d, c) 路径
     - 认为这是中间跳
""")

print("\n【Epoch 2 的实际情况】")
print("\n观察 Epoch 2 的 5 条流量：")
epoch2_flows_parsed = []
for flow in flows_epoch2:
    # 解析流量字符串
    # 例如: "Chunk 3 from 0 traveled over 2->3 with volume 1.0 in epoch 2"
    parts = flow.split()
    chunk_id = int(parts[1])
    source = int(parts[3])
    link = parts[6]
    sender, receiver = map(int, link.split('->'))
    epoch2_flows_parsed.append({
        'chunk': chunk_id,
        'source': source,
        'link': (sender, receiver),
        'desc': flow
    })

print("\nEpoch 2 的流量详情：")
for i, f in enumerate(epoch2_flows_parsed, 1):
    s = f['source']
    i_node, j_node = f['link']
    c = f['chunk']
    print(f"\n  {i}. Chunk {c} from {s}: {i_node} → {j_node}")
    print(f"     • j={j_node} 在 final_receivers? 是 (所有节点都是 final_receiver)")
    print(f"     • 代码判断: 这是到节点 {j_node} 的【最后一跳】")
    print(f"     • Alpha 计入路径: (source={s}, dest={j_node}, chunk={c})")
    print(f"     • 但是！这条路径在【之前的 epoch】中已经有了起始跳！")

print("\n" + "="*70)
print("【核心问题】")
print("="*70)

print("""
  path_epoch_max 策略按照 (s, d, c) 来累积每个 epoch 的 alpha。
  
  对于多跳路径，例如：
    "Demand at 0 for chunk 0 from 3 met by epoch 2"
    - Epoch 1: 3->1 (第一跳)
    - Epoch 2: 1->0 (第二跳)
  
  代码的处理：
    • Epoch 1 的 flow (3, 3, 1, 0, 1.0, 1):
      - j=1 在 final_receivers，认为是到节点 1 的最后一跳
      - Alpha 计入: path_epoch_alpha[(3, 1, 0)][1] += 0.5
      - **但实际上，chunk 0 的最终目的地是节点 0，不是节点 1！**
    
    • Epoch 2 的 flow (3, 1, 0, 0, 1.0, 2):
      - j=0 在 final_receivers，认为是到节点 0 的最后一跳
      - Alpha 计入: path_epoch_alpha[(3, 0, 0)][2] += 0.5
      - **这才是正确的路径标识！**
  
  结果：
    - path_epoch_alpha[(3, 1, 0)][1] = 0.5  (错误的路径！)
    - path_epoch_alpha[(3, 0, 0)][2] = 0.5  (正确，但只有最后一跳)
    
  问题：
    第一跳的 alpha 被计入了错误的路径 (3→1)，
    而不是实际的完整路径 (3→0)！
""")

print("\n【为什么 Epoch 2 补偿为 0？】")
print("""
  观察 Epoch 2 的所有流量：它们都是多跳路径的【最后一跳】。
  
  根据当前的补偿逻辑：
    • 每条流只把自己这一跳的 alpha (0.5 μs) 计入对应的路径
    • 不会累积之前 epoch 的 alpha（因为之前的跳被归到了"错误的目的地"）
  
  而 Epoch 0 和 Epoch 1 的补偿各为 0.5 μs，是因为：
    • 它们包含了【直连路径】（1 跳完成的传输）
    • 例如 Epoch 0: "Chunk 0 from 2 traveled over 2->0" (直达！)
    • 这些直连路径的第一跳就是最后一跳，所以 alpha 被正确计入
  
  但 Epoch 2 的所有流量都是：
    ❌ 多跳路径的第二跳（前面的跳已经被"错误归类"了）
    ❌ 没有任何直连的 1-hop 路径
  
  所以，Epoch 2 的每条路径只计入了【自己这一跳】的 alpha，
  而忽略了【之前 epoch 的跳】的 alpha。
  
  取该 epoch 所有路径的最大值 = max(0.5, 0.5, 0.5, ...) = 0.5 μs？
  
  等等！为什么结果是 0 而不是 0.5？
""")

print("\n" + "="*70)
print("【更深层的问题：为什么是 0 而不是 0.5？】")
print("="*70)

print("""
  让我重新检查代码逻辑...
  
  在 alltoall.py 的补偿计算中：
  
  ```python
  # 推断最终接收节点集合
  final_receivers = {t[2] for t in required_flows if t[2] not in self.topology.switch_indices}
  
  for flow in required_flows:
      s, i, j, c, volume, k = flow
      if i == j or self.topology.capacity[i][j] <= 0:
          continue  # 跳过自环和无容量链路
      
      link_alpha = self.topology.alpha[i][j]
      if link_alpha <= 0 or (link_alpha / self.epoch_duration) > alpha_threshold:
          continue  # 跳过不符合阈值的链路
      
      # 如果 j 是最终接收，则只记入该目的
      potential_destinations = [j] if j in final_receivers else list(final_receivers)
      for d in potential_destinations:
          path_epoch_alpha[(s, d, c)][k] += link_alpha
  ```
  
  关键！让我们看 Epoch 2 的一条具体流量：
    Flow: (3, 1, 0, 0, 1.0, 2)  # Chunk 0 from 3: 1→0 in epoch 2
    
    • i=1, j=0
    • j=0 在 final_receivers? 是
    • potential_destinations = [0]
    • 计入: path_epoch_alpha[(3, 0, 0)][2] += 0.5
  
  但是！这条路径 (3, 0, 0) 在 Epoch 1 有没有记录？
    - 检查 Epoch 1 的流量: (3, 3, 1, 0, 1.0, 1)  # 3→1
    - i=3, j=1
    - j=1 在 final_receivers? 是
    - potential_destinations = [1]
    - 计入: path_epoch_alpha[(3, 1, 0)][1] += 0.5  ← 错误！
  
  所以：
    • path_epoch_alpha[(3, 0, 0)] 只有 epoch 2 的记录
    • path_epoch_alpha[(3, 1, 0)] 有 epoch 1 的记录（但这是错误的路径！）
    
  那为什么 Epoch 2 补偿是 0 而不是 0.5？
  
  啊！我明白了！问题在于【Path_Count】：
    schedule["Path_Count"] = 15
    
  这 15 条路径都在 Epoch 0 或 Epoch 1 完成了！
  Epoch 2 的流量虽然存在，但它们被当作是【已完成路径的后续跳】，
  而不是新的独立路径！
  
  让我验证...
""")

print("\n【验证：检查 per_epoch_path_alpha 的内容】")
print("""
  根据代码逻辑，per_epoch_path_alpha[2] 应该包含在 epoch 2 有 alpha 累积的路径。
  
  但如果 per_epoch_path_alpha[2] 是空的，那么：
    epoch_max_compensations[2] = 0.0
  
  为什么会是空的？
  
  可能的原因：
    1. Epoch 2 的所有流量都被【跳过】了（capacity 检查、阈值检查等）
    2. Epoch 2 的流量虽然处理了，但没有被归到任何路径
    3. 代码中有 bug 导致 epoch 2 的记录被覆盖或丢失
""")

print("\n让我手动模拟 Epoch 2 的一条流量处理过程：")
print("""
  Flow: "Chunk 3 from 0 traveled over 2->3 with volume 1.0 in epoch 2"
  解析: (s=0, i=2, j=3, c=3, volume=1.0, k=2)
  
  代码检查：
    1. i == j? 2 == 3? 否 ✓
    2. capacity[2][3] > 0? 是 (邻居节点) ✓
    3. link_alpha = 0.5e-6 秒 = 0.5 μs
    4. link_alpha > 0? 是 ✓
    5. link_alpha / epoch_duration = 0.5μs / 5000μs = 0.0001
    6. 0.0001 > 0.1? 否 ✓ (满足阈值，应该被计入)
    7. j=3 in final_receivers? 是 ✓
    8. potential_destinations = [3]
    9. 计入: path_epoch_alpha[(0, 3, 3)][2] += 0.5
  
  理论上，这条记录应该存在！
  
  那为什么 Epoch 2 的补偿是 0？
""")

print("\n" + "="*70)
print("【真正的原因】")
print("="*70)

print("""
  我需要重新审视代码...
  
  啊！我发现了！
  
  在 alltoall.py 的 get_flow_schedule 函数中：
  
  ```python
  # 推断最终接收节点集合：所有非 switch 的 j。
  final_receivers = {t[2] for t in required_flows if t[2] not in self.topology.switch_indices}
  ```
  
  这里 final_receivers 收集的是 required_flows 中所有的接收端 j。
  对于 AlltoAll，每个节点都会接收数据，所以 final_receivers = {0, 1, 2, 3}。
  
  然后：
  ```python
  for flow in required_flows:
      s, i, j, c, volume, k = flow
      if i == j or self.topology.capacity[i][j] <= 0:
          continue
      ...
      potential_destinations = [j] if j in final_receivers else list(final_receivers)
      for d in potential_destinations:
          path_epoch_alpha[(s, d, c)][k] += link_alpha
  ```
  
  关键问题：
    • 由于所有节点都在 final_receivers 中
    • 每条 flow 只会计入 (s, j, c) 这一个路径
    • 多跳路径的【中间节点】被当作了"最终目的地"！
  
  例如，路径 3→1→0 (chunk 0):
    • Epoch 1: flow (3, 3, 1, 0, 1.0, 1)
      - 计入 path_epoch_alpha[(3, 1, 0)][1] += 0.5  ← 错误！
    • Epoch 2: flow (3, 1, 0, 0, 1.0, 2)
      - 计入 path_epoch_alpha[(3, 0, 0)][2] += 0.5  ← 这才对！
  
  但是！Chunk 0 的真实目的地是节点 0，不是节点 1！
  所以 path_epoch_alpha[(3, 1, 0)] 是一个【虚假的路径】！
  
  真实的路径应该是 (3, 0, 0)，它的完整 alpha 累积应该是：
    • Epoch 1: 0.5 (第一跳 3→1)
    • Epoch 2: 0.5 (第二跳 1→0)
    • 总计: 1.0 μs
  
  但由于代码把第一跳归到了 (3, 1, 0)，第二跳归到了 (3, 0, 0)，
  导致两跳被分到了不同的"路径"，无法正确累积！
""")

print("\n但这还是没有解释为什么 Epoch 2 的补偿是 0 而不是 0.5...")
print("\n让我检查一下 per_epoch_path_alpha[2] 的实际内容...")

print("""
  从 schedule JSON 中，我们可以看到：
    "Epoch_Compensation_us": [0.5, 0.5, 0.0]
  
  这意味着：
    • per_epoch_path_alpha[0] 有路径，max = 0.5
    • per_epoch_path_alpha[1] 有路径，max = 0.5
    • per_epoch_path_alpha[2] 要么是空的，要么所有路径的值都是 0
  
  根据我们的分析，per_epoch_path_alpha[2] 应该包含 5 条路径，
  每条路径的 alpha 应该是 0.5。
  
  那为什么是 0？
  
  唯一的可能性：代码中有一个 bug，导致 epoch 2 的流量被跳过了！
  
  让我检查是否有条件把 epoch 2 的流量过滤掉了...
""")

print("\n等等！我注意到一个细节：")
print("""
  在 get_flow_schedule 中，required_flows 是从 per_chunk_flows 提取的：
  
  ```python
  required_flows = []
  Kmax = self.find_demand_satisfied_k()
  for k in range(Kmax):
      if k in per_chunk_flows.keys():
          required_flows += per_chunk_flows[k]
  ```
  
  注意：range(Kmax)，而不是 range(Kmax + 1)！
  
  如果 Kmax = 2（即 find_demand_satisfied_k() 返回 2），
  那么 range(2) = [0, 1]，不包括 epoch 2！
  
  这就是问题所在！
""")

print("\n" + "="*70)
print("【终极答案】")
print("="*70)

print(f"""
  schedule["3-Epochs_Required"] = {schedule["3-Epochs_Required"]}
  
  但是，在 get_flow_schedule 函数中：
  
  ```python
  Kmax = self.find_demand_satisfied_k()  # 返回 2
  for k in range(Kmax):  # range(2) = [0, 1]
      if k in per_chunk_flows.keys():
          required_flows += per_chunk_flows[k]
  ```
  
  问题！这里只循环到 Kmax-1，即只包含 epoch 0 和 epoch 1！
  Epoch 2 的流量根本没有被加入 required_flows！
  
  所以，在计算 alpha 补偿时：
    • required_flows 只包含 epoch 0 和 epoch 1 的流量
    • path_epoch_alpha 只累积了 epoch 0 和 epoch 1 的 alpha
    • per_epoch_path_alpha[2] 是空的！
    • epoch_max_compensations[2] = 0.0（因为该 epoch 没有路径）
  
  这是一个 BUG！
  
  正确的代码应该是：
    for k in range(Kmax + 1):  # 包含 Kmax
        ...
  
  或者：
    for k in range(self.find_demand_satisfied_k() + 1):
        ...
""")

print("\n【总结】")
print("""
  第三个 epoch (epoch 2) 的补偿为 0 的原因：
  
  ❌ BUG: get_flow_schedule 中提取 required_flows 时，
         使用了 range(Kmax) 而不是 range(Kmax + 1)，
         导致最后一个 epoch 的流量被遗漏！
  
  影响：
    • Epoch 2 的流量没有被纳入 alpha 补偿计算
    • 导致 Epoch_Compensation_us[2] = 0
    • 低估了总的 Schedule_Based_Compensation
  
  修复方法：
    将 range(Kmax) 改为 range(Kmax + 1)
    或者改为 range(self.find_demand_satisfied_k() + 1)
""")

print("\n" + "="*70)
