# Torus 拓扑实现文档

## 文件清单

### 1. 核心实现
- **`teccl/topologies/torus.py`**: Torus 拓扑类实现
  - 实现了水平和垂直方向的环绕连接
  - 每个节点都有 4 个邻居（上下左右，带环绕）
  - 链路速度: 50 GB/s，传播延迟: 0.5 μs

### 2. 输入配置文件
- **`teccl/examples/sample_inputs/torus_alltoall.json`**: Torus AlltoAll 配置
- **`teccl/examples/sample_inputs/torus_allgather.json`**: Torus AllGather 配置
  - 4×4 网格，16 个节点
  - 1 GB 数据，16 chunks
  - 时间限制: 300s

### 3. 验证和测试脚本
- **`verify_torus.py`**: 验证 Torus 拓扑连接正确性
  - 检查水平/垂直环绕连接
  - 检查节点度数（应该全部为 4）
  - 对比 Mesh vs Torus 的距离优势

- **`compare_mesh_torus.py`**: 性能对比脚本
  - 同时运行 Mesh 和 Torus 的 AlltoAll 求解
  - 对比完成时间、带宽、跳数等指标
  - 生成详细的对比报告

## Mesh vs Torus 的关键区别

### Mesh（网格）
- **无环绕连接**
- 边界节点只有 2-3 个邻居
- 平均距离: 2.67 跳
- 总跳数（AlltoAll）: 640

### Torus（环面）
- **有环绕连接**（水平+垂直）
- 所有节点都有 4 个邻居
- 平均距离: 2.13 跳（**20% 改善**）
- 总跳数（AlltoAll）: 512（**20% 减少**）

### 原始 Bug
原始的 `mesh.py` 代码错误地实现了**部分 Torus 特性**：
- 只有水平环绕（行边界跨越）
- 没有垂直环绕
- 创建了 6 对错误连接: (3,4), (7,8), (11,12) 及其反向

## 快速开始

### 1. 验证 Torus 拓扑
```bash
python verify_torus.py
```

### 2. 运行 Torus AlltoAll
```bash
python -m teccl solve --input_args teccl/examples/sample_inputs/torus_alltoall.json
```

### 3. 对比 Mesh vs Torus
```bash
python compare_mesh_torus.py
```

## 预期结果

Torus 应该在以下方面优于 Mesh：
- ✅ 完成时间减少 ~20%
- ✅ 算法带宽提升 ~25%
- ✅ 总跳数减少 20% (512 vs 640)
- ✅ 所有路径达到理论最优（Torus 距离）

## 注意事项

1. **chunk_size 初始化**: 需要在构造拓扑前设置 `topology_params.chunk_size`
2. **对称性**: Torus 是完全对称的，所有节点地位相同
3. **可扩展性**: 适用于任意 `side_length × side_length` 的网格
4. **实际应用**: Torus 在超算互联网络中很常见（如 IBM Blue Gene）

## 后续工作

- [ ] 添加 3D Torus 支持（立方体环绕）
- [ ] 优化大规模 Torus 的求解性能
- [ ] 添加更多拓扑变体（如 k-ary n-cube）
