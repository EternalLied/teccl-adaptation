# AlltoAll 流量分割功能说明

## 概述

新增了 `allow_flow_splitting` 参数，用于控制 AlltoAll 求解器是否允许流量分割。

## 参数说明

### `allow_flow_splitting` (bool, 默认: false)

- **位置**: `InstanceParams` 中
- **默认值**: `false`
- **作用**: 控制 AlltoAll 求解器使用 LP（线性规划）还是 MILP（混合整数线性规划）

### 两种模式对比

| 特性 | MILP (allow_flow_splitting=false) | LP (allow_flow_splitting=true) |
|------|-----------------------------------|--------------------------------|
| 变量类型 | GRB.INTEGER (整数) | GRB.CONTINUOUS (连续) |
| 流量分割 | ❌ 不允许 | ✅ 允许 |
| 求解速度 | 较慢 | 较快 |
| 解的质量 | 可能次优（时间限制内） | 更容易达到最优 |
| 实际应用 | 更符合实际（整数 chunk） | 可能需要后处理 |
| 求解器名称 | `AllToAll_MILP` | `AllToAll_LP` |

## 使用方法

### 1. 在 JSON 配置文件中设置

```json
{
    "InstanceParams": {
        "collective": 2,
        "allow_flow_splitting": true,
        ...
    }
}
```

### 2. 示例配置

#### MILP 配置 (mesh.json)
```json
{
    "InstanceParams": {
        "allow_flow_splitting": false
    }
}
```

运行输出:
```
WARNING:root:Not_Optimal_AllToAll_MILP_Status-10_Mesh_4-nodes_4-chunks_25-epochs_0.005-epoch_duration
```

#### LP 配置 (mesh_lp.json)
```json
{
    "InstanceParams": {
        "allow_flow_splitting": true
    }
}
```

运行输出:
```
WARNING:root:Not_Optimal_AllToAll_LP_Status-10_Mesh_4-nodes_4-chunks_25-epochs_0.005-epoch_duration
```

## 技术细节

### 变量类型变化

当 `allow_flow_splitting=true` 时，以下变量从 `GRB.INTEGER` 改为 `GRB.CONTINUOUS`:

1. **flow[s][i][j][k]**: 从源 s 经过链路 (i,j) 在 epoch k 的流量
2. **buffer[s][i][k]**: 源 s 的数据在节点 i 的缓冲区（epoch k）
3. **consumed_at_k[s][i][k]**: 节点 i 在 epoch k 消耗的来自源 s 的数据
4. **total_demand_sat[s][i][k]**: 到 epoch k 为止满足的总需求量

### 求解器名称

- `solver_name` 会根据参数自动设置为 `"AllToAll_LP"` 或 `"AllToAll_MILP"`
- 日志文件名和警告信息中会相应显示 LP 或 MILP

## 性能建议

### 何时使用 MILP (allow_flow_splitting=false)

- 需要实际可执行的调度（整数 chunk）
- 小规模拓扑（节点数 ≤ 16）
- 有充足的求解时间

### 何时使用 LP (allow_flow_splitting=true)

- 大规模拓扑（节点数 > 16）
- 需要快速获得近似最优解
- 进行算法研究和性能上界估计
- 后续会对结果进行取整处理

## 示例

### 快速测试

```bash
# MILP 模式
teccl solve --input_args teccl/examples/sample_inputs/mesh.json

# LP 模式
teccl solve --input_args teccl/examples/sample_inputs/mesh_lp.json
```

### 自动化测试

运行提供的测试脚本:
```bash
python test_flow_splitting.py
```

该脚本会自动运行两种模式并比较求解时间和结果质量。

## 注意事项

1. **LP 结果的后处理**: 当使用 LP 模式时，流量变量可能是小数，实际部署前需要进行取整
2. **求解时间**: LP 通常比 MILP 快 10-100 倍，特别是在大规模拓扑中
3. **最优性**: LP 更容易找到全局最优解，而 MILP 可能受限于时间限制
4. **兼容性**: 该参数只影响 AlltoAll 求解器，AllGather 不受影响

## 相关文件

- **参数定义**: `teccl/input_data.py` (InstanceParams.allow_flow_splitting)
- **求解器实现**: `teccl/solvers/alltoall.py`
- **示例配置**: `teccl/examples/sample_inputs/mesh_lp.json`
- **测试脚本**: `test_flow_splitting.py`
