## 目标
帮助 AI 代理快速在 TE-CCL 代码库中进行有意义的改动：理解架构边界、常用运行/调试命令、代码约定以及修改/扩展时要注意的地方。

## 快速启动（开发者常用命令）
- 创建 Conda 环境并安装 Gurobi（需要有效许可证），然后在该环境下安装包：

```powershell
# 在 conda 环境中 (示例)
conda create -n teccl python=3.9 -y; conda activate teccl
# 安装 Gurobi（参考 README 中的具体步骤并激活许可证），随后：
pip install -e .
```

- 运行单个示例：

```powershell
teccl solve --input_args teccl/examples/sample_inputs/ndv2_input.json
```

## 项目“宏观”结构与设计意图
- 入口：`setup.py` 的 console_script 注册 `teccl = teccl.__main__:main`，实际 CLI handler 在 `teccl/cli/solve.py` 中解析 JSON 输入并构造 `UserInputParams`。
- 调度器/控制流：`teccl/scheduler.py` 中的 `TECCLSolver` 负责：选择拓扑、构造 solver（`teccl/solvers/*`），进行可行性搜索（当 `num_epochs == -1`）并写出最终 schedule JSON。
- 输入约定：用户输入 JSON 分为三部分：`TopologyParams`, `GurobiParams`, `InstanceParams`（见 `teccl/input_data.py`）。AI 要修改运行逻辑时务必遵循这些字段和枚举（`Collective`, `ObjectiveType`, `EpochType`, `SolutionMethod`）。
- 拓扑与解法分离：每种拓扑实现为 `teccl/topologies/*.py`（例如 `DGX1`, `DGX2`, `NDv2`, `AMD`, `Mesh`），拓扑负责 `capacity`、`alpha`、`switch_indices`、`epoch_duration` 等；求解器实现于 `teccl/solvers/*`（如 `allgather.py`, `alltoall.py`, `allgather_astar.py`）。

## 项目约定与常见模式（对 AI 很重要）
- 拓扑实例通过 `TopologyParams.name` 选择：值必须和 `teccl/topologies/*.py` 中类名所期望的字符串一致（例如: "DGX1", "NDv2"）。
- Solver 构造方式：`TECCLSolver.get_solver` 根据 `InstanceParams.collective` 和 `objective_type` 返回合适的 Formulation（MILP 或 A*）；AlltoAll 会调整 `num_chunks`：
  - 注意：`AlltoAllFormulation` 在构造时把 `num_chunks` 乘以 `(len(topology.capacity) - len(topology.switch_indices))`。
- 变量命名与约束：solver 代码（例如 `teccl/solvers/allgather.py`）大量使用多维数组 + Gurobi 变量；修改时保留现有变量/约束命名可减少回归风险。
- Epoch 逻辑：当 `instance.num_epochs == -1` 时，`TECCLSolver.feasible_solution_search` 会尝试估算合适的 epoch 数以及 epoch duration；不要绕过该流程，除非清楚后果。

## 常见编辑场景与示例（可直接复用的参考点）
- 添加新拓扑：在 `teccl/topologies/` 新建文件，实现 `construct_topology()` 和 `set_switch_indicies()` 并确保构造 `capacity` 和 `alpha` 矩阵。参考 `teccl/topologies/topology.py` 的抽象基类。
- 支持新 collective：在 `teccl/solvers/` 新增 Formulation，确保实现 `encode_problem()`, `get_schedule()` 和必要的变量初始化，注册到 `TECCLSolver.get_solver`。
- 调试/日志：在输入 JSON 中把 `InstanceParams.debug` 设为 `true` 并设置 `debug_output_file`，或在 `GurobiParams` 中设置 `log_file`。另外，运行时会在 `Logs/` 下创建日志目录。

## 运行与资源注意事项
- 本项目依赖 Gurobi；大拓扑需要大量内存（示例中 4-chassis 需要 ~256GB 内存和长时间求解）。在 CI/快速迭代中请使用小样例或减小 `num_epochs`/`num_chunks`。
- examples 目录包含生成、运行和分析脚本：`teccl/examples/json_gen.py`, `run_experiments.sh`, `generate_tables.py`。用于批量实验和复现实验数据。

## 编辑/PR 建议（避免常见错误）
- 不要任意调整 Gurobi 参数默认值，改动需在 `input` JSON 中通过 `GurobiParams` 配置并在 README 中记录。
- 修改拓扑的 `capacity` 或 `alpha` 时要同时验证 `get_epoch_duration_fast_link()` 与 `get_epoch_duration_slow_link()` 的结果。
- 当改动 solver 的约束或目标，会显著影响求解时间；在提交 PR 前用小规模样本（`teccl/examples/sample_inputs/`）做 smoke test。

---
如果有任何不清楚的点或你想让我把某个部分展开（例如：把 `allgather.py` 的关键约束解释成短注释，或为新拓扑生成模板文件），告诉我你要深挖的文件/任务，我会迭代更新这份指南。
