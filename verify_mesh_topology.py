import json
from collections import defaultdict

print("="*70)
print("验证 Mesh 拓扑的邻居关系")
print("="*70)

# 4×4 Mesh 的理论邻居关系
side_length = 4

def get_theoretical_neighbors(node, side_length):
    """根据网格拓扑计算理论上的邻居"""
    row = node // side_length
    col = node % side_length
    neighbors = []
    
    # 上
    if row > 0:
        neighbors.append(node - side_length)
    # 下
    if row < side_length - 1:
        neighbors.append(node + side_length)
    # 左
    if col > 0:
        neighbors.append(node - 1)
    # 右
    if col < side_length - 1:
        neighbors.append(node + 1)
    
    return sorted(neighbors)

def get_code_neighbors(node, side_length):
    """根据当前代码逻辑计算邻居"""
    neighbors = []
    for j in range(side_length ** 2):
        if j == node - 1 or j == node + 1 or j == node - side_length or j == node + side_length:
            neighbors.append(j)
    return sorted(neighbors)

print(f"\n【节点邻居对比】")
print(f"{'Node':>4} | {'理论邻居':<20} | {'代码邻居':<20} | {'匹配?'}")
print(f"-" * 70)

mismatches = []
for node in range(16):
    theoretical = get_theoretical_neighbors(node, side_length)
    code = get_code_neighbors(node, side_length)
    match = "✅" if theoretical == code else "❌"
    
    print(f"{node:4d} | {str(theoretical):<20} | {str(code):<20} | {match}")
    
    if theoretical != code:
        mismatches.append({
            'node': node,
            'theoretical': theoretical,
            'code': code,
            'extra': set(code) - set(theoretical),
            'missing': set(theoretical) - set(code)
        })

if mismatches:
    print(f"\n【邻居不匹配详情】")
    for m in mismatches:
        node = m['node']
        row = node // side_length
        col = node % side_length
        print(f"\n  Node {node} (row={row}, col={col}):")
        print(f"    理论邻居: {m['theoretical']}")
        print(f"    代码邻居: {m['code']}")
        if m['extra']:
            print(f"    ❌ 多余的: {m['extra']} (不应该是邻居)")
        if m['missing']:
            print(f"    ❌ 缺失的: {m['missing']} (应该是邻居但没有)")

print(f"\n【结论】")
if mismatches:
    print(f"  ❌ 发现 {len(mismatches)} 个节点的邻居关系不正确")
    print(f"  问题原因: mesh.py 中的邻居判断没有考虑行边界")
    print(f"  影响: 某些不相邻的节点被错误地连接，导致'短路'")
    print(f"\n  这解释了为什么实际跳数小于 Manhattan 距离：")
    print(f"  错误的拓扑连接创造了不应存在的'捷径'！")
else:
    print(f"  ✅ 所有节点的邻居关系都正确")

print("="*70)
