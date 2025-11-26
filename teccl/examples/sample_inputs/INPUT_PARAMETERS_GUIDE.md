# TE-CCL 输入参数完整指南

本文档详细说明所有输入 JSON 参数的含义、单位和取值范围。

## TopologyParams（拓扑参数）

| 参数 | 类型 | 单位 | 默认值 | 说明 |
|------|------|------|--------|------|
| `name` | string | - | "DGX1" | 拓扑名称，必须匹配 `teccl/topologies/*.py` 中的类名<br>可选值: "DGX1", "DGX2", "NDv2", "AMD", "Mesh" |
| `chassis` | int | 个 | 1 | 机箱数量，影响拓扑规模 |
| `chunk_size` | float | **GB** | 1.0 | 数据块大小<br>示例: 0.0625 = 64MB, 1.0 = 1GB |
| `alpha` | tuple | **秒 (s)** | (0, 0) | 链路延迟: (链路 alpha, 交换机 alpha)<br>示例: (0.35e-6, 0) = (0.35微秒, 0) |
| `side_length` | int | - | 4 | 仅用于 Mesh/Torus 拓扑：网格边长<br>总节点数 = side_length² |

### 示例
```json
{
  "TopologyParams": {
    "name": "NDv2",
    "chassis": 2,
    "chunk_size": 0.0625,  // 64 MB
    "alpha": [0.0, 0.0]     // 秒
  }
}
```

---

## GurobiParams（Gurobi 求解器参数）

| 参数 | 类型 | 单位 | 默认值 | 说明 |
|------|------|------|--------|------|
| `time_limit` | float | **小时 (hrs)** | 2.0 | 求解时间限制 |
| `feasibility_tol` | float | - | 1e-4 | 可行性容差 |
| `intfeas_tol` | float | - | 1e-4 | 整数可行性容差 |
| `optimality_tol` | float | - | 1e-4 | 最优性容差 |
| `output_flag` | int | - | 1 | 输出标志: 0=关闭, 1=开启 |
| `log_file` | string | - | "" | 日志文件路径（空字符串表示不记录） |
| `log_to_console` | int | - | 0 | 控制台日志: 0=关闭, 1=开启 |
| `mip_gap` | float | - | 1e-4 | MIP 最优性间隙 |
| `mip_focus` | int | - | 0 | MIP 焦点: 0=平衡, 1=可行性, 2=最优性, 3=界 |
| `crossover` | int | - | -1 | 交叉算法: -1=自动 |
| `method` | int | - | -1 | 求解方法: -1=自动 |
| `heuristics` | float | - | 0.05 | 启发式强度: 0.0~1.0 |
| `presolve` | int | - | -1 | 预求解: -1=自动, 0=关闭, 1=保守, 2=激进 |
| `solution_limit` | int | **个** | 2000000 | 解数量限制 |

### 示例
```json
{
  "GurobiParams": {
    "time_limit": 2,        // 2 小时
    "output_flag": 0,
    "mip_gap": 0.0001,
    "mip_focus": 1
  }
}
```

---

## InstanceParams（实例参数）

| 参数 | 类型 | 单位 | 默认值 | 说明 |
|------|------|------|--------|------|
| `collective` | int | - | 1 | 集合通信类型<br>1 = AllGather<br>2 = AlltoAll |
| `num_chunks` | int | **个** | 1 | 每个节点需要传输的数据块数量 |
| `epoch_type` | int | - | 1 | Epoch 时长计算方式<br>1 = FASTEST_LINK（最快链路）<br>2 = SLOWEST_LINK（最慢链路）<br>3 = USER_INPUT（用户指定） |
| `epoch_duration` | float | **秒 (s)** | -1 | Epoch 时长（-1 表示自动计算） |
| `epoch_multiplier` | int | - | 1 | Epoch 时长倍数 |
| `num_epochs` | int | **个** | -1 | Epoch 数量（-1 表示自动估算） |
| `epsilon` | float | - | 0.1 | 目标函数中的 epsilon 值 |
| `alpha_threshold` | float | - | 0.1 | Alpha 阈值：alpha/epoch_duration 比值低于此值时 alpha 视为 0 |
| `alpha_epoch_duration_ratio_max` | int | - | 200 | Alpha/epoch_duration 最大比值，超过则增加 epoch_duration |
| `switch_copy` | bool | - | true | 交换机是否可以复制数据块到多个出口 |
| `switch_to_gpu_link_on` | bool | - | false | Switch→GPU 链路是否计入传输时间<br>false = 瞬时传输<br>true = 完整计时 |
| `debug` | bool | - | false | 是否输出调试信息 |
| `debug_output_file` | string | - | "" | 调试日志文件路径 |
| `objective_type` | int | - | 3 | 优化目标函数<br>1 = BINARY_USED_EPOCHS<br>2 = TOTAL_DEMAND<br>3 = PAPER（论文标准）<br>4 = ASTAR |
| `solution_method` | int | - | 1 | 求解方法<br>1 = ONE_SHOT（一次性）<br>2 = ITERATIVE（迭代二分搜索） |
| `schedule_output_file` | string | - | "" | 调度输出文件路径（空字符串使用默认命名） |
| `symmetry` | bool | - | false | 是否对对称节点施加对称约束 |

### 示例
```json
{
  "InstanceParams": {
    "collective": 1,              // AllGather
    "num_chunks": 1,              // 1 个数据块
    "epoch_type": 1,              // 最快链路
    "epoch_duration": -1,         // 自动计算 (秒)
    "num_epochs": -1,             // 自动估算 (个)
    "alpha_threshold": 0.1,
    "switch_copy": true,
    "switch_to_gpu_link_on": false,
    "debug": false,
    "objective_type": 3,          // PAPER
    "solution_method": 2,         // ITERATIVE
    "schedule_output_file": "teccl/examples/schedules/ndv2_schedule.json"
  }
}
```

---

## 完整示例（带单位说明）

```json
{
  "TopologyParams": {
    "name": "NDv2",
    "chassis": 2,                 // 2 个机箱
    "chunk_size": 0.0625          // 64 MB (0.0625 GB)
  },
  "GurobiParams": {
    "time_limit": 2,              // 2 小时
    "feasibility_tol": 0.0001,
    "intfeas_tol": 0.0001,
    "optimality_tol": 0.0001,
    "output_flag": 0,
    "log_file": "",
    "log_to_console": 0,
    "mip_gap": 0.0001,
    "mip_focus": 1,
    "crossover": -1,
    "method": -1,
    "heuristics": 0.3
  },
  "InstanceParams": {
    "collective": 1,              // AllGather
    "num_chunks": 1,              // 1 个数据块
    "epoch_type": 1,              // FASTEST_LINK
    "epoch_duration": -1,         // 自动计算 (秒)
    "num_epochs": -1,             // 自动估算 (个)
    "alpha_threshold": 0.1,
    "switch_copy": true,
    "switch_to_gpu_link_on": false,
    "debug": false,
    "debug_output_file": "",
    "objective_type": 3,          // PAPER
    "solution_method": 2,         // ITERATIVE
    "schedule_output_file": "teccl/examples/schedules/ndv2_schedule.json"
  }
}
```

---

## 常见数据块大小转换

| 描述 | chunk_size (GB) | 字节数 |
|------|-----------------|--------|
| 1 KB | 0.000000953674 | 1,024 |
| 4 KB | 0.000003814697 | 4,096 |
| 16 KB | 0.000015258789 | 16,384 |
| 64 KB | 0.000061035156 | 65,536 |
| 256 KB | 0.000244140625 | 262,144 |
| 1 MB | 0.000976562500 | 1,048,576 |
| 4 MB | 0.003906250000 | 4,194,304 |
| 16 MB | 0.015625000000 | 16,777,216 |
| 64 MB | 0.062500000000 | 67,108,864 |
| 256 MB | 0.250000000000 | 268,435,456 |
| 1 GB | 1.000000000000 | 1,073,741,824 |

---

## 时间单位转换

| 描述 | alpha 值 (秒) |
|------|---------------|
| 0.35 微秒 | 0.35e-6 或 0.00000035 |
| 2.6 微秒 | 2.6e-6 或 0.0000026 |
| 1 毫秒 | 1e-3 或 0.001 |
| 1 秒 | 1.0 |

---

## 参考链接

- Gurobi 参数文档: https://www.gurobi.com/documentation/10.0/refman/parameters.html
- TE-CCL 论文: https://doi.org/10.1145/3651890.3672249
- 代码参数定义: `teccl/input_data.py`
