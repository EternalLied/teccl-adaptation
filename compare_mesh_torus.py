"""
对比 Mesh vs Torus 拓扑在 AlltoAll 场景下的性能
"""
import json
import subprocess
import sys
from pathlib import Path

def run_solve(input_file):
    """运行求解并返回结果"""
    print(f"\n运行: {input_file}")
    result = subprocess.run(
        [sys.executable, "-m", "teccl", "solve", "--input_args", input_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ 求解失败:")
        print(result.stderr)
        return None
    
    print(result.stdout)
    return result.returncode == 0

def analyze_schedule(schedule_file):
    """分析调度文件"""
    if not Path(schedule_file).exists():
        print(f"❌ 调度文件不存在: {schedule_file}")
        return None
    
    with open(schedule_file, 'r') as f:
        data = json.load(f)
    
    flows = data.get('7-Flows', [])
    
    # 计算总跳数
    from collections import defaultdict
    chunk_paths = defaultdict(list)
    
    for flow in flows:
        parts = flow.split()
        chunk = int(parts[1])
        source = int(parts[3])
        chunk_paths[(source, chunk)].append(flow)
    
    total_hops = sum(len(hops) for hops in chunk_paths.values())
    
    return {
        'total_data_gb': data.get('0-Total_Data_GB'),
        'epoch_duration': data.get('1-Epoch_Duration'),
        'epochs_required': data.get('3-Epochs_Required'),
        'finish_time': data.get('4-Collective_Finish_Time'),
        'algo_bandwidth': data.get('5-Algo_Bandwidth'),
        'total_flows': len(flows),
        'total_hops': total_hops,
        'num_paths': len(chunk_paths)
    }

def main():
    print("="*70)
    print("Mesh vs Torus AlltoAll 性能对比")
    print("="*70)
    
    # 运行 Mesh
    print("\n【1/2】运行 Mesh AlltoAll...")
    mesh_success = run_solve("teccl/examples/sample_inputs/mesh.json")
    
    # 运行 Torus
    print("\n【2/2】运行 Torus AlltoAll...")
    torus_success = run_solve("teccl/examples/sample_inputs/torus_alltoall.json")
    
    if not mesh_success or not torus_success:
        print("\n❌ 至少有一个求解失败")
        return
    
    # 分析结果
    print("\n" + "="*70)
    print("结果对比分析")
    print("="*70)
    
    mesh_stats = analyze_schedule("teccl/examples/schedules/Mesh_16nodes_ALLTOALL_1.0GB_16chunks.json")
    torus_stats = analyze_schedule("teccl/examples/schedules/Torus_16nodes_ALLTOALL_1.0GB_16chunks.json")
    
    if not mesh_stats or not torus_stats:
        print("❌ 无法读取调度文件")
        return
    
    print(f"\n{'指标':<30} | {'Mesh':>15} | {'Torus':>15} | {'改善'}")
    print("-"*70)
    
    # 比较各项指标
    metrics = [
        ('总数据量 (GB)', 'total_data_gb', ''),
        ('Epoch 时长 (s)', 'epoch_duration', ''),
        ('Epoch 数量', 'epochs_required', ''),
        ('完成时间 (s)', 'finish_time', 's'),
        ('算法带宽 (GB/s)', 'algo_bandwidth', 'GB/s'),
        ('总流数量', 'total_flows', ''),
        ('总跳数', 'total_hops', '跳'),
        ('路径数量', 'num_paths', ''),
    ]
    
    for label, key, unit in metrics:
        mesh_val = mesh_stats.get(key)
        torus_val = torus_stats.get(key)
        
        if mesh_val is None or torus_val is None:
            continue
        
        # 计算改善
        if key in ['finish_time', 'epochs_required', 'total_hops']:
            # 越小越好
            if mesh_val > 0:
                improvement = (1 - torus_val / mesh_val) * 100
                improvement_str = f"{improvement:+.1f}%"
            else:
                improvement_str = "N/A"
        elif key in ['algo_bandwidth']:
            # 越大越好
            if mesh_val > 0:
                improvement = (torus_val / mesh_val - 1) * 100
                improvement_str = f"{improvement:+.1f}%"
            else:
                improvement_str = "N/A"
        else:
            improvement_str = "-"
        
        if isinstance(mesh_val, float):
            print(f"{label:<30} | {mesh_val:>15.4f} | {torus_val:>15.4f} | {improvement_str}")
        else:
            print(f"{label:<30} | {mesh_val:>15} | {torus_val:>15} | {improvement_str}")
    
    print("\n" + "="*70)
    print("结论")
    print("="*70)
    
    hop_improvement = (1 - torus_stats['total_hops'] / mesh_stats['total_hops']) * 100
    time_improvement = (1 - torus_stats['finish_time'] / mesh_stats['finish_time']) * 100
    bw_improvement = (torus_stats['algo_bandwidth'] / mesh_stats['algo_bandwidth'] - 1) * 100
    
    print(f"\nTorus 相比 Mesh 的优势:")
    print(f"  ✅ 总跳数减少: {hop_improvement:.1f}%")
    print(f"  ✅ 完成时间减少: {time_improvement:.1f}%")
    print(f"  ✅ 算法带宽提升: {bw_improvement:.1f}%")
    print(f"\n原因: Torus 的环绕连接提供了更短的路径，减少了平均跳数")
    print(f"     理论最优跳数: Mesh=640, Torus=512 (20% 减少)")

if __name__ == "__main__":
    main()
