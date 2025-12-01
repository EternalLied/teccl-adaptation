# TE-CCL 数据量配置最佳实践

## ⚠️ 数据量限制说明

由于模型的数值精度限制，**极小的数据量（如 < 10KB）可能导致求解失败**。

### 失败示例
```json
"total_data": "1KB"  // ❌ 导致 epoch_duration 太小 (~4.8 纳秒)
                     // 结果: Status-3 INFEASIBLE
```

### 推荐的数据量范围

| 数据量范围      | 适用场景                    | 状态 |
|---------------|----------------------------|------|
| **< 10KB**    | 不推荐（数值精度问题）        | ❌    |
| **10KB-100KB** | 测试小规模问题              | ⚠️    |
| **100KB-10MB** | 典型测试场景                | ✅    |
| **10MB-1GB**   | 实际应用场景                | ✅    |
| **> 1GB**      | 大规模集群通信              | ✅    |

## 推荐配置示例

### 快速测试（256KB）
```json
{
    "TopologyParams": {
        "total_data": "256KB"
    },
    "InstanceParams": {
        "num_epochs": 30
    }
}
```

### 标准测试（1MB-4MB）
```json
{
    "TopologyParams": {
        "total_data": "1MB"  // 或 "4MB"
    },
    "InstanceParams": {
        "num_epochs": 50
    }
}
```

### 实际应用（256MB-1GB）
```json
{
    "TopologyParams": {
        "total_data": "1GB"  // 或 "256MB"
    },
    "InstanceParams": {
        "num_epochs": -1  // 自动推断
    }
}
```

## 故障排除

### 问题：Status-3 INFEASIBLE

**症状：**
```
WARNING: Not_Optimal_AllGather_MILP_Status-3
ERROR: No schedule found with the given parameters
```

**可能原因：**
1. ❌ 数据量太小（< 10KB）
2. ❌ num_epochs 太少
3. ❌ epoch_multiplier 设置不当
4. ❌ 拓扑与数据量不匹配

**解决方案：**
1. ✅ 增加 total_data 到 >= 100KB
2. ✅ 增加 num_epochs 或设为 -1（自动推断）
3. ✅ 调整 epoch_multiplier（建议 1-8）
4. ✅ 启用 debug 模式查看详细日志

### 问题：求解时间过长

**解决方案：**
1. 减少 num_epochs
2. 增加 time_limit
3. 增加 mip_gap（如 0.05）
4. 减少 num_chunks
5. 使用 solution_method: 1 (ONE_SHOT) 而非 2 (ITERATIVE)

## 调试技巧

启用调试模式：
```json
{
    "InstanceParams": {
        "debug": true,
        "debug_output_file": "Logs/debug.log"
    },
    "GurobiParams": {
        "output_flag": 1,
        "log_to_console": 1,
        "log_file": "Logs/gurobi.log"
    }
}
```

## 为什么极小数据量会失败？

当数据量非常小时：
1. **chunk_size 极小**：1KB / (4 nodes × 1 chunk) = 0.00024 GB
2. **epoch_duration 极小**：~4.8 纳秒
3. **浮点精度问题**：Gurobi 容差设置（1e-4）大于实际值
4. **约束冲突**：alpha 延迟（微秒级）远大于 epoch_duration

### 数值示例
```
1KB 数据量:
  chunk_size = 0.00024 GB
  link_speed = 50 GB/s
  epoch_duration = 0.00024 / 50 = 4.8e-6 秒 = 4.8 μs
  
如果链路 alpha = 0.5 μs:
  alpha / epoch_duration = 0.5 / 4.8 ≈ 0.104
  这接近或超过 alpha_threshold (0.1)
  导致约束建模困难
```

## 建议

对于学习和测试：
- 使用 **1MB-4MB** 数据量
- 使用 **ONE_SHOT** 模式（更快）
- 设置合理的 **time_limit**（0.2-0.5 小时）

对于实际评估：
- 使用 **256MB-1GB** 数据量
- 使用 **ITERATIVE** 模式（更优）
- 根据问题规模调整 **num_epochs**
