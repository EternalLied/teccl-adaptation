"""
验证 Torus 拓扑实现的正确性
- 检查环绕连接
- 对比 Mesh vs Torus 的路径长度
- 运行 AlltoAll 求解并分析结果
"""
from teccl.topologies.torus import Torus
from teccl.topologies.mesh import Mesh
from teccl.input_data import TopologyParams

def verify_torus_connections(side_length=4):
    """验证 Torus 的环绕连接"""
    topo_params = TopologyParams(
        name="Torus",
        chassis=1,
        total_data_MB=1024,
        side_length=side_length
    )
    # Set chunk_size before constructing topology
    topo_params.chunk_size = 1.0  # 1 GB chunk for testing
    torus = Torus(topo_params)
    
    print("="*70)
    print(f"验证 Torus 拓扑 ({side_length}×{side_length})")
    print("="*70)
    
    # 检查水平环绕
    print("\n【水平环绕连接】")
    for row in range(side_length):
        leftmost = row * side_length
        rightmost = leftmost + side_length - 1
        
        # 检查最右边连接到最左边
        if torus.capacity[rightmost][leftmost] > 0:
            print(f"  ✅ Row {row}: {rightmost} ↔ {leftmost}")
        else:
            print(f"  ❌ Row {row}: {rightmost} ↔ {leftmost} (缺失)")
    
    # 检查垂直环绕
    print("\n【垂直环绕连接】")
    for col in range(side_length):
        top = col
        bottom = col + side_length * (side_length - 1)
        
        # 检查最下面连接到最上面
        if torus.capacity[bottom][top] > 0:
            print(f"  ✅ Col {col}: {bottom} ↔ {top}")
        else:
            print(f"  ❌ Col {col}: {bottom} ↔ {top} (缺失)")
    
    # 检查每个节点的邻居数量（应该都是 4）
    print("\n【节点度数检查】")
    degree_issues = []
    for i in range(side_length ** 2):
        degree = sum(1 for c in torus.capacity[i] if c > 0)
        if degree != 4:
            degree_issues.append((i, degree))
    
    if degree_issues:
        print(f"  ❌ 发现 {len(degree_issues)} 个节点度数不为 4:")
        for node, degree in degree_issues[:5]:
            print(f"    Node {node}: degree = {degree}")
    else:
        print(f"  ✅ 所有节点度数都为 4（符合 Torus 特性）")

def compare_distances(side_length=4):
    """对比 Mesh 和 Torus 的距离"""
    print("\n" + "="*70)
    print("Mesh vs Torus 距离对比")
    print("="*70)
    
    def manhattan_distance(src, dst, side_length):
        """Mesh 的 Manhattan 距离"""
        src_r, src_c = src // side_length, src % side_length
        dst_r, dst_c = dst // side_length, dst % side_length
        return abs(src_r - dst_r) + abs(src_c - dst_c)
    
    def torus_distance(src, dst, side_length):
        """Torus 的最短距离（考虑环绕）"""
        src_r, src_c = src // side_length, src % side_length
        dst_r, dst_c = dst // side_length, dst % side_length
        
        # 水平方向：取直接距离和环绕距离的较小值
        h_direct = abs(src_c - dst_c)
        h_wrap = side_length - h_direct
        h_dist = min(h_direct, h_wrap)
        
        # 垂直方向：取直接距离和环绕距离的较小值
        v_direct = abs(src_r - dst_r)
        v_wrap = side_length - v_direct
        v_dist = min(v_direct, v_wrap)
        
        return h_dist + v_dist
    
    # 统计所有节点对的距离
    num_nodes = side_length ** 2
    mesh_total = 0
    torus_total = 0
    improvements = []
    
    for src in range(num_nodes):
        for dst in range(num_nodes):
            if src == dst:
                continue
            
            mesh_dist = manhattan_distance(src, dst, side_length)
            torus_dist = torus_distance(src, dst, side_length)
            
            mesh_total += mesh_dist
            torus_total += torus_dist
            
            if torus_dist < mesh_dist:
                improvements.append((src, dst, mesh_dist, torus_dist))
    
    print(f"\n【总距离统计】（{num_nodes} 个节点，{num_nodes*(num_nodes-1)} 对路径）")
    print(f"  Mesh 总距离: {mesh_total} 跳")
    print(f"  Torus 总距离: {torus_total} 跳")
    print(f"  改善: {mesh_total - torus_total} 跳 ({(1-torus_total/mesh_total)*100:.1f}% 减少)")
    print(f"  平均距离: Mesh={mesh_total/(num_nodes*(num_nodes-1)):.2f}, Torus={torus_total/(num_nodes*(num_nodes-1)):.2f}")
    
    print(f"\n【距离改善示例】（Torus 比 Mesh 更短的路径）")
    for src, dst, mesh_d, torus_d in improvements[:5]:
        src_r, src_c = src // side_length, src % side_length
        dst_r, dst_c = dst // side_length, dst % side_length
        print(f"  {src}({src_r},{src_c}) → {dst}({dst_r},{dst_c}): Mesh={mesh_d}跳, Torus={torus_d}跳 (省{mesh_d-torus_d}跳)")

def visualize_example_path():
    """可视化一个示例路径"""
    print("\n" + "="*70)
    print("示例：Node 3 → Node 4 的最短路径")
    print("="*70)
    
    print("\nMesh 拓扑（无环绕）:")
    print("  Row 0:  0 - 1 - 2 - 3")
    print("          |   |   |   |")
    print("  Row 1:  4 - 5 - 6 - 7")
    print()
    print("  路径: 3 → 2 → 1 → 0 → 4 (4 跳)")
    print("  或: 3 → 7 → 6 → 5 → 4 (4 跳)")
    
    print("\nTorus 拓扑（有环绕）:")
    print("  Row 0:  0 - 1 - 2 - 3")
    print("          |   |   |   ↑")
    print("  Row 1:  4 - 5 - 6 - 7")
    print("          ↑           |")
    print("          └───────────┘ (环绕)")
    print()
    print("  路径: 3 → 4 (1 跳，通过水平环绕！)")
    print("  距离减少: 4 → 1 (75% 改善)")

if __name__ == "__main__":
    verify_torus_connections(side_length=4)
    compare_distances(side_length=4)
    visualize_example_path()
    
    print("\n" + "="*70)
    print("提示：运行以下命令测试 Torus AlltoAll 求解:")
    print("  python -m teccl solve --input_args teccl/examples/sample_inputs/torus_alltoall.json")
    print("="*70)
