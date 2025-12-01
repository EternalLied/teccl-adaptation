"""检查 Gurobi 状态码含义"""

# Gurobi 状态码
status_codes = {
    1: "LOADED",
    2: "OPTIMAL",
    3: "INFEASIBLE",
    4: "INF_OR_UNBD",
    5: "UNBOUNDED",
    6: "CUTOFF",
    7: "ITERATION_LIMIT",
    8: "NODE_LIMIT",
    9: "TIME_LIMIT",
    10: "SOLUTION_LIMIT",
    11: "INTERRUPTED",
    12: "NUMERIC",
    13: "SUBOPTIMAL",
    14: "INPROGRESS",
    15: "USER_OBJ_LIMIT"
}

print("Gurobi Status Codes:")
print("=" * 50)
for code, name in status_codes.items():
    print(f"Status {code}: {name}")

print("\n" + "=" * 50)
print("当前问题 Status-10 = SOLUTION_LIMIT")
print("含义：求解器找到了指定数量的解后停止")
print("触发条件：GurobiParams 中设置了 SolutionLimit 参数")
print("=" * 50)
