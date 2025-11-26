# TE-CCL 输入 JSON 参数完整说明

本文档详细说明 TE-CCL 输入 JSON 文件的所有参数含义、取值范围和使用建议。

## 文件结构

输入 JSON 文件包含三个主要部分：
```json
{
  "TopologyParams": { ... },    // 拓扑配置
  "GurobiParams": { ... },      // Gurobi 求解器参数
  "InstanceParams": { ... }     // 问题实例参数
}
```

---

## 一、TopologyParams（拓扑参数）

定义网络拓扑结构和物理特性。

### 1.1 通用参数

#### `name` (string, 必需)
**拓扑类型名称**
- 可选值：
  - `"DGX1"`: NVIDIA DGX-1（8 GPU, NVLink 1.0）
  - `"DGX2"`: NVIDIA DGX-2（16 GPU, NVSwitch）
  - `"NDv2"`: Azure NDv2（多机箱 InfiniBand 互连）
  - `"AMD"`: AMD MI300 系列
  - `"Mesh"`: 通用 2D Mesh 拓扑
- 示例：`"name": "NDv2"`

#### `chassis` (int, 必需)
**机箱数量**
- 取值：≥ 1
- 含义：拓扑包含的独立机箱（服务器节点）数量
- 示例：`"chassis": 2` （双机箱配置）

#### `total_data_MB` (float, 必需)
**总数据量（MB）**
- 取值：> 0
- 含义：集合通信操作的总数据量，单位 MB
- 自动计算：程序会根据总数据量、节点数和 num_chunks 自动计算每块大小（chunk_size）
- 公式：`chunk_size (GB) = total_data_MB / 1024 / (节点总数 * num_chunks)`
- 示例：
  - `"total_data_MB": 1024` → 1 GB
  - `"total_data_MB": 256` → 256 MB
  - `"total_data_MB": 102400` → 100 GB

#### `chunk_size` (float, 自动计算)
**单块数据大小（GB）**
- **无需手动设置**，由程序根据 `total_data_MB` 自动计算
- 在拓扑构造时自动填充此字段
- 默认值：0.0

#### `alpha` (array[2], 可选)
**链路传播延迟参数（秒）**
- 格式：`[link_alpha, switch_alpha]`
- 含义：
  - `link_alpha`: 直连链路的传播延迟
  - `switch_alpha`: 交换机转发延迟
- 默认：`[0.0, 0.0]`（忽略延迟）
- 示例：
  - `"alpha": [0.0, 0.0]` → 零延迟理想模型
  - `"alpha": [7e-7, 1.3e-6]` → 700 ns 链路 + 1.3 μs 交换机

### 1.2 Mesh 拓扑专用参数

#### `side_length` (int, Mesh 必需)
**Mesh 网格边长**
- 取值：≥ 2
- 含义：正方形 Mesh 拓扑的边长（节点总数 = side_length²）
- 示例：
  - `"side_length": 4` → 4×4 = 16 节点
  - `"side_length": 6` → 6×6 = 36 节点
- **注意**：当前仅支持正方形 Mesh，不支持矩形（如 3×4）

### 1.3 NDv2 专用参数

#### `option` (int, NDv2 可选)
**配置选项**
- 取值：通常为 1（具体取值见拓扑实现）
- 含义：NDv2 拓扑的特定配置变体
- 示例：`"option": 1`

---

## 二、GurobiParams（Gurobi 求解器参数）

控制 Gurobi 优化器的行为和性能。

### 2.1 时间与收敛控制

#### `time_limit` (float)
**最大求解时间（小时）**
- 默认：2
- 含义：求解器最多运行的小时数，超时返回当前最优解
- 调优建议：
  - 快速实验：0.05（3 分钟）
  - 正常测试：1–2 小时
  - 长时间精确求解：8–24 小时
- 示例：`"time_limit": 2`

#### `mip_gap` (float)
**MIP 相对最优间隙**
- 默认：1e-4（0.01%）
- 含义：允许的相对最优间隙 = (上界 - 下界) / |下界|
- 调优建议：
  - 快速探索：1e-2（1%）或 1e-3（0.1%）
  - 精确基准：1e-5（0.001%）或更小
  - 平衡：1e-4（默认）
- 示例：`"mip_gap": 0.0001`

### 2.2 数值精度参数

#### `feasibility_tol` (float)
**线性约束可行性容忍度**
- 默认：1e-6
- 当前常用：1e-4
- 含义：约束 `lhs ≤ rhs` 允许的绝对误差
- 调优：数值不稳定时可放宽到 1e-4；需高精度时收紧到 1e-8
- 示例：`"feasibility_tol": 0.0001`

#### `intfeas_tol` (float)
**整数可行性容忍度**
- 默认：1e-5
- 当前常用：1e-4
- 含义：变量与最近整数的距离容忍度
- 示例：`"intfeas_tol": 0.0001`

#### `optimality_tol` (float)
**最优性容忍度**
- 默认：1e-6
- 当前常用：1e-4
- 含义：对偶间隙判定最优的容忍度
- 示例：`"optimality_tol": 0.0001`

### 2.3 求解策略参数

#### `mip_focus` (int)
**MIP 求解侧重点**
- 可选值：
  - `0`: 平衡（默认）
  - `1`: 侧重寻找可行解
  - `2`: 侧重改善下界（证明最优）
  - `3`: 侧重收紧 gap
- 推荐：`1`（初期难找到可行解时）
- 示例：`"mip_focus": 1`

#### `heuristics` (float)
**启发式搜索强度**
- 取值：0.0–1.0
- 默认：0.05
- 当前常用：0.3
- 含义：用于寻找整数可行解的启发式算法努力程度
- 调优：
  - 快速找解：0.5–0.7
  - 节省时间：0.05–0.2
- 示例：`"heuristics": 0.3`

#### `method` (int)
**线性松弛求解方法**
- 可选值：
  - `-1`: 自动选择（推荐）
  - `0`: 单纯形（原始）
  - `1`: 单纯形（对偶）
  - `2`: 屏障（内点法）
  - `3`: 并发
- 推荐：`-1`（自动）
- 示例：`"method": -1`

#### `crossover` (int)
**内点法后交叉策略**
- 可选值：
  - `-1`: 自动（推荐）
  - `0`: 禁用
  - `1`: 原始交叉
  - `2`: 对偶交叉
- 示例：`"crossover": -1`

#### `presolve` (int)
**预处理强度**
- 可选值：
  - `-1`: 自动（默认）
  - `0`: 关闭
  - `1`: 保守
  - `2`: 激进
- 示例：`"presolve": -1`

#### `solution_limit` (int)
**解数量限制**
- 默认：2000000
- 含义：找到指定数量的可行解后停止
- 示例：`"solution_limit": 2000000`

### 2.4 日志输出参数

#### `output_flag` (int)
**控制台输出开关**
- 可选值：
  - `0`: 静默模式（无输出）
  - `1`: 正常输出
- 推荐：调试时用 1，批量运行用 0
- 示例：`"output_flag": 0`

#### `log_file` (string)
**日志文件路径**
- 默认：`""`（不写入文件）
- 含义：Gurobi 日志写入的文件路径
- 示例：`"log_file": "logs/solve.log"`

#### `log_to_console` (int)
**日志输出到控制台**
- 可选值：
  - `0`: 不输出到控制台
  - `1`: 输出到控制台
- 示例：`"log_to_console": 0`

---

## 三、InstanceParams（问题实例参数）

定义具体的集合通信问题和求解策略。

### 3.1 集合通信参数

#### `collective` (int, 必需)
**集合通信算子类型**
- 可选值：
  - `1`: AllGather（全聚合）
  - `2`: AlltoAll（全对全交换）
- 含义：
  - **AllGather**: 每个节点有一份数据，最终所有节点拥有全部数据
  - **AlltoAll**: 每个节点有 N 份不同数据，发送给其他 N-1 个节点
- 示例：`"collective": 1`

#### `num_chunks` (int, 必需)
**数据分块数量**
- 取值：≥ 1
- 含义：每个节点的数据分成多少块进行传输
- 影响：
  - `1`: 不分块，模型简单但灵活性低
  - `>1`: 增加调度灵活性和并行度，但模型规模增大
- 推荐：
  - 初始测试：1
  - 性能优化：2–4
  - 大规模实验：谨慎使用（会显著增加求解时间）
- **注意**：AlltoAll 中会自动放大 `num_chunks *= 节点数`
- 示例：`"num_chunks": 1`

### 3.2 时间离散化参数（Epoch）

#### `epoch_type` (int)
**Epoch 时长计算方式**
- 可选值：
  - `1`: FASTEST_LINK（基于最快链路）
  - `2`: SLOWEST_LINK（基于最慢链路）
- 含义：
  - 最快链路：更细粒度，epoch 数更多，调度更精确
  - 最慢链路：更粗粒度，epoch 数更少，求解更快
- 推荐：通常用 `1`（精细调度）
- 示例：`"epoch_type": 1`

#### `epoch_duration` (float)
**手动指定 Epoch 时长（秒）**
- 默认：`-1`（自动计算）
- 含义：每个时间片的长度
- 使用场景：
  - `-1`: 让程序根据 `epoch_type` 自动计算（推荐）
  - `> 0`: 手动指定（用于特殊实验）
- 示例：`"epoch_duration": -1`

#### `epoch_multiplier` (float)
**Epoch 时长倍数放大因子**
- 默认：1
- 含义：将自动计算的 epoch 时长乘以此倍数
- 作用：通过放大 epoch 时长减少 epoch 总数，加速求解
- 示例：
  - `1`: 不放大
  - `2`: epoch 时长翻倍，epoch 数减半
- 示例：`"epoch_multiplier": 1`

#### `num_epochs` (int)
**最大 Epoch 数量**
- 默认：`-1`（自动搜索）
- 含义：时间线包含的 epoch 总数
- 使用场景：
  - `-1`: 通过可行性搜索自动确定（推荐）
  - `> 0`: 固定值（用于探索或对比实验）
- 调优：如遇不可行，增大此值或增大 `epoch_multiplier`
- 示例：`"num_epochs": -1` 或 `"num_epochs": 50`

#### `alpha_threshold` (float)
**传播延迟阈值**
- 默认：0.1
- 含义：当 `alpha / epoch_duration < alpha_threshold` 时，忽略该链路的传播延迟
- 作用：避免微小延迟产生额外的 epoch 开销，简化模型
- 示例：`"alpha_threshold": 0.1`

### 3.3 路由与交换机参数

#### `switch_copy` (bool)
**允许交换机复制数据**
- 可选值：
  - `false`: 禁止（交换机仅转发，单播）
  - `true`: 允许（交换机可复制到多目的，多播）
- 影响：
  - `false`: 更严格的路由约束，可能导致更长时间
  - `true`: 更灵活，可能减少传输时间
- 推荐：根据实际硬件能力设置
- 示例：`"switch_copy": false`

#### `switch_to_gpu_link_on` (bool)
**启用交换机到 GPU 链路**
- 可选值：
  - `true`: 启用交换机→GPU 方向的链路容量
  - `false`: 禁用（某些简化测试场景）
- **注意**：Mesh 拓扑无交换机，此参数无效
- 示例：`"switch_to_gpu_link_on": true`

### 3.4 调试参数

#### `debug` (bool)
**调试模式开关**
- 可选值：
  - `true`: 启用详细日志和中间输出
  - `false`: 仅输出关键信息
- 推荐：排查问题时启用，正常运行时关闭
- 示例：`"debug": false`

#### `debug_output_file` (string)
**调试日志输出文件**
- 默认：`""`（不写入独立文件）
- 含义：Python logging 模块的日志文件路径
- 示例：`"debug_output_file": "debug_run.log"`

### 3.5 优化策略参数

#### `objective_type` (int)
**优化目标函数类型**
- 可选值：
  - `1`: BINARY_USED_EPOCHS（最小化使用的 epoch 数）
  - `2`: TOTAL_DEMAND（所有需求满足时给奖励）
  - `3`: PAPER（推荐，每个需求满足时立即奖励）
  - `4`: ASTAR（A* 启发式搜索）
- 推荐：`3`（PAPER 方法，收敛性和质量较好）
- 示例：`"objective_type": 3`

#### `solution_method` (int)
**求解方法**
- 可选值：
  - `1`: ONE_SHOT（一次性求解）
  - `2`: ITERATIVE（迭代二分搜索）
- 含义：
  - ONE_SHOT: 直接在给定 `num_epochs` 下求解，速度快
  - ITERATIVE: 通过二分搜索逐步缩小 epoch 范围，更稳健
- 推荐：
  - 探索阶段：`1`（快速）
  - 精确结果：`2`（稳健）
- 示例：`"solution_method": 2`

### 3.6 输出参数

#### `schedule_output_folder` (string)
**调度结果输出文件夹路径**
- 默认：`"teccl/examples/schedules"`
- 含义：最终调度方案 JSON 文件的输出目录
- 文件名格式：自动生成为 `拓扑_节点数_算子_数据量MB_块数chunks_时间戳.json`
- 行为：
  - 留默认：输出到 `teccl/examples/schedules`
  - 设为空字符串：输出到当前工作目录
  - 指定其他路径：输出到该目录（目录不存在会自动创建）
- 推荐：使用相对路径，跨平台兼容
- 示例：
  - 默认 → `teccl/examples/schedules/NDv2_16nodes_ALLGATHER_1024MB_1chunks_1732512345.json`
  - `""` → `./NDv2_16nodes_ALLGATHER_1024MB_1chunks_1732512345.json`
  - `"results"` → `results/NDv2_16nodes_ALLGATHER_1024MB_1chunks_1732512345.json`

---

## 四、常用配置模板

### 4.1 快速验证配置（AllGather, 小数据）
```json
{
  "TopologyParams": {
    "name": "NDv2",
    "chassis": 2,
    "total_data_MB": 256
  },
  "GurobiParams": {
    "time_limit": 0.1,
    "mip_gap": 1e-2,
    "output_flag": 1
  },
  "InstanceParams": {
    "collective": 1,
    "num_chunks": 1,
    "epoch_type": 1,
    "epoch_duration": -1,
    "num_epochs": -1,
    "objective_type": 3,
    "solution_method": 1,
    "schedule_output_folder": ""
  }
}
```

### 4.2 精确基准测试配置（AllGather, 大数据）
```json
{
  "TopologyParams": {
    "name": "NDv2",
    "chassis": 2,
    "total_data_MB": 1024
  },
  "GurobiParams": {
    "time_limit": 2,
    "feasibility_tol": 1e-6,
    "intfeas_tol": 1e-5,
    "optimality_tol": 1e-6,
    "mip_gap": 1e-4,
    "mip_focus": 1,
    "heuristics": 0.3
  },
  "InstanceParams": {
    "collective": 1,
    "num_chunks": 1,
    "epoch_type": 1,
    "epoch_duration": -1,
    "num_epochs": -1,
    "alpha_threshold": 0.1,
    "switch_copy": false,
    "objective_type": 3,
    "solution_method": 2,
    "schedule_output_folder": "teccl/examples/schedules"
  }
}
```

### 4.3 AlltoAll 测试配置
```json
{
  "TopologyParams": {
    "name": "NDv2",
    "chassis": 2,
    "total_data_MB": 1024
  },
  "GurobiParams": {
    "time_limit": 2,
    "mip_gap": 1e-3,
    "mip_focus": 1
  },
  "InstanceParams": {
    "collective": 2,
    "num_chunks": 1,
    "epoch_type": 1,
    "num_epochs": -1,
    "objective_type": 3,
    "solution_method": 2,
    "schedule_output_folder": ""
  }
}
```

### 4.4 Mesh 拓扑配置
```json
{
  "TopologyParams": {
    "name": "Mesh",
    "chassis": 1,
    "total_data_MB": 1024,
    "side_length": 4,
    "alpha": [0.0, 0.0]
  },
  "GurobiParams": {
    "time_limit": 2,
    "output_flag": 1
  },
  "InstanceParams": {
    "collective": 1,
    "num_chunks": 1,
    "epoch_type": 1,
    "num_epochs": 50,
    "objective_type": 3,
    "solution_method": 2,
    "schedule_output_file": ""
  }
}
```

---

## 五、调优指南

### 5.1 遇到不可行（Status=3）时

**可能原因**：
- `num_epochs` 太小
- `epoch_duration` 太短
- 约束过于严格（如 `switch_copy=false` 且拓扑受限）

**解决方法**：
1. 增大 `num_epochs`（如从 50 → 100）
2. 增大 `epoch_multiplier`（如从 1 → 2）
3. 尝试 `switch_copy=true`（如果硬件支持）
4. 减小 `num_chunks`（如从 4 → 1）
5. 检查 `total_data_MB` 是否过大

### 5.2 求解时间过长时

**优化方向**：
1. 放宽 `mip_gap`（1e-4 → 1e-3 或 1e-2）
2. 减小 `num_chunks`
3. 增大 `epoch_multiplier`（减少 epoch 数）
4. 使用 `solution_method=1`（ONE_SHOT）
5. 减小 `heuristics`（0.3 → 0.1）
6. 减小 `num_epochs`（如果已指定）

### 5.3 需要更精确结果时

**加强精度**：
1. 收紧 `mip_gap`（1e-4 → 1e-5）
2. 降低数值容忍度（feasibility_tol 等设为 1e-6）
3. 增加 `time_limit`（2 → 8 或 24 小时）
4. 使用 `solution_method=2`（ITERATIVE）
5. 设置 `mip_focus=3`（侧重 gap 收敛）

---

## 六、常见问题

### Q1: 为什么没有 `chunk_size` 参数？
A: 现已改为使用 `total_data_MB`，程序会自动根据节点数和 `num_chunks` 计算 `chunk_size`。

### Q2: AlltoAll 的 `num_chunks` 为什么会自动放大？
A: AlltoAll 内部会将 `num_chunks` 乘以节点数，以增加每对节点之间的调度粒度。实际使用的块数 = 输入值 × 节点总数。

### Q3: Mesh 拓扑支持矩形网格吗（如 3×4）？
A: 当前不支持，仅支持正方形网格（`side_length` 的平方）。

### Q4: `switch_to_gpu_link_on` 在 Mesh 中有用吗？
A: 无用。Mesh 拓扑没有交换机，此参数仅对 DGX2/NDv2 等有交换机的拓扑生效。

### Q5: 输出文件名格式是什么？
A: 文件名完全自动生成，格式为：`拓扑_节点数_算子_数据量MB_块数chunks_时间戳.json`  
例如：
```
NDv2_16nodes_ALLGATHER_1024MB_1chunks_1732512345.json
DGX2_16nodes_ALLTOALL_2048MB_2chunks_1732512456.json
Mesh_36nodes_ALLGATHER_512MB_1chunks_1732512567.json
```
只需指定输出文件夹（`schedule_output_folder`），文件名会包含所有关键参数信息。

---

## 七、参考资源

- **Gurobi 官方文档**: https://www.gurobi.com/documentation/
- **项目 README**: `README.md`
- **示例文件目录**: `teccl/examples/sample_inputs/`
- **拓扑实现**: `teccl/topologies/`
- **求解器实现**: `teccl/solvers/`

---

**文档版本**: 1.0  
**更新日期**: 2025-11-25  
**维护者**: TE-CCL 项目组
