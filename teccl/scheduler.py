import copy
import json
import logging
import math
import pathlib
from time import time
from typing import Dict, Tuple, Union

from gurobipy import GRB
from teccl.input_data import *
from teccl.solvers.allgather import AllGatherFormulation
from teccl.solvers.allgather_astar import AStarFormulation
from teccl.solvers.alltoall import AlltoAllFormulation
from teccl.solvers.base_formulation import BaseFormulation
from teccl.topologies.dgx1 import DGX1
from teccl.topologies.dgx2 import DGX2
from teccl.topologies.ndv2 import NDv2
from teccl.topologies.amd import AMD
from teccl.topologies.mesh import Mesh
from teccl.topologies.torus import Torus
from teccl.topologies.topology import Topology


class TECCLSolver(object):
    def __init__(self, user_input: UserInputParams):
        self.user_input = user_input
        # Calculate chunk_size from total_data_MB
        # Set a temporary chunk_size to construct topology first
        user_input.topology.chunk_size = 1.0  # Temporary value
        temp_topology = self.get_topology(user_input.topology)
        num_nodes = temp_topology.node_per_chassis * temp_topology.chassis
        
        # Calculate actual chunk_size: total_data_MB (in MB) / 1024 (to GB) / (num_nodes * num_chunks)
        total_data_GB = user_input.topology.total_data_MB / 1024.0
        chunk_size = total_data_GB / (num_nodes * user_input.instance.num_chunks)
        
        # Store calculated chunk_size in topology params
        user_input.topology.chunk_size = chunk_size
        
        # Now construct the actual topology and solver with correct chunk_size
        self.topology_obj = self.get_topology(user_input.topology)
        self.solver = self.get_solver(copy.deepcopy(user_input), self.topology_obj)

    
    def get_topology(self, topology_params: TopologyParams) -> Topology:
        if topology_params.name == "DGX1":
            return DGX1(topology_params)
        elif topology_params.name == "DGX2":
            return DGX2(topology_params)
        elif topology_params.name == "NDv2":
            return NDv2(topology_params)
        elif topology_params.name == "AMD":
            return AMD(topology_params)
        elif topology_params.name == "Mesh":
            return Mesh(topology_params)
        elif topology_params.name == "Torus":
            return Torus(topology_params)
        else:
            raise NotImplementedError(
                f"Input topology {topology_params.name} not implemented")


    def get_solver(self, user_input: UserInputParams, topology: Topology) -> BaseFormulation:
        if user_input.instance.collective == Collective.ALLGATHER:
            if user_input.instance.objective_type == ObjectiveType.ASTAR:
                return AStarFormulation(user_input, topology)
            return AllGatherFormulation(user_input, topology)
        elif user_input.instance.collective == Collective.ALLTOALL:
            # For AlltoAll, num_chunks represents chunks per GPU, so multiply by number of GPUs
            # Cache the original num_chunks on first call to prevent exponential growth
            if not hasattr(self, '_original_num_chunks'):
                self._original_num_chunks = user_input.instance.num_chunks
            
            adjusted_user_input = copy.deepcopy(user_input)
            gpus = len(topology.capacity) - len(topology.switch_indices)
            # Always use the cached original value, not the potentially modified one
            adjusted_user_input.instance.num_chunks = self._original_num_chunks * gpus
            return AlltoAllFormulation(adjusted_user_input, topology)
        else:
            raise NotImplementedError(
                f"Input collective {user_input.instance.collective} not implemented")

    def feasible_solution_search(self, user_input: UserInputParams, topology_obj: Topology, final_epoch_duration: float) -> Union[Tuple[float, int, Dict], ValueError]:
        """
            Finds a feasible time in which the collective can finish using large epochs with fewer of them.
            Returns: (feasible_time, num_epochs, timing_details)
        """
        # Initialize timing breakdown
        feasibility_timing = {
            "solver_creation": 0.0,
            "encoding_solving": 0.0,
            "demand_check": 0.0,
            "iterations": 0
        }
        
        if user_input.instance.collective == Collective.ALLTOALL:
            num_epochs = math.ceil(topology_obj.get_max_hop_distance() * 20)
            factor = 100
        else:
            num_epochs = math.ceil(topology_obj.get_max_hop_distance() * 3)
            factor = 1
        # 3 is a good factor to not have too many epochs, but also to take into account the alpha
        max_time_chunk = topology_obj.get_largest_time_chunk()

        collective_time_estimate = num_epochs * max_time_chunk * \
            user_input.instance.num_chunks * len(topology_obj.capacity) / 2

        # binary search on the time estimate
        lower_bound = 0

        upper_bound = collective_time_estimate * factor
        attempts = 0
        feasible_time = upper_bound

        while lower_bound <= upper_bound:
            mid = (upper_bound + lower_bound) / 2
            new_user_input = copy.deepcopy(user_input)
            new_user_input.gurobi = copy.deepcopy(user_input.gurobi)
            new_user_input.instance = copy.deepcopy(user_input.instance)
            # find some feasible solution
            new_user_input.gurobi.solution_limit = 1
            new_user_input.instance.num_epochs = num_epochs
            new_user_input.instance.epoch_duration = mid / num_epochs
            if new_user_input.instance.epoch_duration <= final_epoch_duration and feasible_time != collective_time_estimate * factor:
                break
            # user_input.instance.debug = True
            
            feasibility_timing["iterations"] += 1
            
            start_solver_creation = time()
            solver_inst = self.get_solver(new_user_input, topology_obj)
            feasibility_timing["solver_creation"] += time() - start_solver_creation
            
            start_encode = time()
            result = solver_inst.encode_problem()
            feasibility_timing["encoding_solving"] += time() - start_encode
            
            if result != GRB.INFEASIBLE:
                start_demand = time()
                epochs_taken = solver_inst.find_demand_satisfied_k() + 1
                feasibility_timing["demand_check"] += time() - start_demand
                
                time_taken = epochs_taken * solver_inst.epoch_duration
                upper_bound = time_taken
                feasible_time = min(feasible_time, time_taken)
            else:
                lower_bound = mid
            attempts += 1
            if attempts > 10:
                # Avoids trying too many times and spending time in the initial search.
                break
        if feasible_time != collective_time_estimate * factor:
            return feasible_time, num_epochs, feasibility_timing
        raise ValueError(
            "Unable to find a solution in the initial feasible search algorithm (try with factor > 1)")


    def get_schedules(self, initial_solver: BaseFormulation, user_input: UserInputParams, topology_obj: Topology) -> Dict:
        """
            Finds the optimal schedule for the collective either directly or iteratively.
            In the direct method, the solver is instantiated to find the optimal solution in the given number of epochs.
            In the iterative method, the solution is found using binary search and in each iteration the solver is instantiated
                to find some feasible solution.
        """
        epoch_result_schedule_solver = {}
        if user_input.instance.solution_method == SolutionMethod.ONE_SHOT:
            # One shot
            result = initial_solver.encode_problem()
            schedule, schedule_json = initial_solver.get_schedule()
            
            if schedule:
                epochs_taken = initial_solver.find_demand_satisfied_k() + 1
                epoch_result_schedule_solver[epochs_taken] = {"result": result,
                                                            "schedule": (schedule, schedule_json),
                                                            "solver": initial_solver}
        else:
            # Iterative
            user_input.gurobi.solution_limit = 1
            lower_bound = 0
            upper_bound = user_input.instance.num_epochs
            tried_epochs = set()
            
            while lower_bound <= upper_bound:
                mid = math.ceil((upper_bound + lower_bound) / 2)
                if mid in tried_epochs:
                    break
                tried_epochs.add(mid)
                
                new_user_input = copy.deepcopy(user_input)
                new_user_input.instance.num_epochs = mid
                
                solver_inst = self.get_solver(new_user_input, topology_obj)
                solver = solver_inst
                
                result = solver_inst.encode_problem(use_one_less_epoch=True)
                schedule, schedule_json = solver_inst.get_schedule()
                
                if schedule:
                    epochs_taken = solver_inst.find_demand_satisfied_k() + 1
                    logging.debug(f"Found a feasible schedule in {epochs_taken} epochs")
                    upper_bound = epochs_taken
                    epoch_result_schedule_solver[epochs_taken] = {"result": result,
                                                                "schedule": (schedule, schedule_json),
                                                                "solver": solver_inst}
                else:
                    lower_bound = mid
        return epoch_result_schedule_solver
    
    def _print_result_summary(self, schedule_data: Dict) -> None:
        """
            打印调度结果的关键指标摘要（带单位）
        """
        total_data_gb = schedule_data.get("0-Total_Data_GB", "N/A")
        epoch_duration = schedule_data.get("1-Epoch_Duration", "N/A")
        expected_epoch_duration = schedule_data.get("2-Expected_Epoch_Duration", "N/A")
        epochs_required = schedule_data.get("3-Epochs_Required", "N/A")
        collective_finish_time = schedule_data.get("4-Collective_Finish_Time", "N/A")
        algo_bandwidth = schedule_data.get("5-Algo_Bandwidth", "N/A")
        # 简化：不再输出用时分解，仅保留总求解时间（如存在）
        solver_time = schedule_data.get("Solver_Time", "N/A")
        
        # Alpha compensation metrics
        alpha_threshold = schedule_data.get("Alpha_Threshold", "N/A")
        schedule_based_compensation = schedule_data.get("Schedule_Based_Compensation_us", "N/A")
        used_ignored_links = schedule_data.get("Used_Ignored_Alpha_Links_Count", "N/A")
        static_ignored_links = schedule_data.get("Static_Ignored_Alpha_Links_Count", "N/A")
        collective_finish_time_scheduled = schedule_data.get("4b-Collective_Finish_Time_ScheduleBased", "N/A")
        algo_bandwidth_scheduled = schedule_data.get("5b-Algo_Bandwidth_ScheduleBased", "N/A")
        
        print("\n" + "="*70)
        print("  TE-CCL 调度结果摘要")
        print("="*70)
        print("\n【主要性能指标】")
        if total_data_gb != "N/A":
            print(f"  0️⃣  总数据量: {total_data_gb:.4f} GB")
        else:
            print(f"  0️⃣  总数据量: {total_data_gb}")
        
        if epoch_duration != "N/A":
            print(f"  1️⃣  Epoch 时长: {epoch_duration:.6f} 秒 (s)")
        else:
            print(f"  1️⃣  Epoch 时长: {epoch_duration}")
        
        if expected_epoch_duration != "N/A":
            print(f"  2️⃣  预期 Epoch 时长: {expected_epoch_duration:.6f} 秒 (s)")
        else:
            print(f"  2️⃣  预期 Epoch 时长: {expected_epoch_duration}")
        
        print(f"  3️⃣  所需 Epoch 数: {epochs_required} 个")
        
        if collective_finish_time != "N/A":
            print(f"  🔵 集合通信完成时间 (原始): {collective_finish_time:.6f} 秒 (s)")
            print(f"      = {collective_finish_time * 1000:.3f} 毫秒 (ms)")
        else:
            print(f"  🔵 集合通信完成时间 (原始): {collective_finish_time}")
        
        if collective_finish_time_scheduled != "N/A":
            print(f"  🟢 集合通信完成时间 (补偿后): {collective_finish_time_scheduled:.6f} 秒 (s)")
            print(f"      = {collective_finish_time_scheduled * 1000:.3f} 毫秒 (ms)")
        
        if algo_bandwidth != "N/A":
            print(f"  🔵 算法带宽 (原始): {algo_bandwidth:.2f} GB/s")
        else:
            print(f"  🔵 算法带宽 (原始): {algo_bandwidth}")
        
        if algo_bandwidth_scheduled != "N/A":
            print(f"  🟢 算法带宽 (补偿后): {algo_bandwidth_scheduled:.2f} GB/s")
        
        # Alpha compensation details
        if schedule_based_compensation != "N/A":
            print("\n【Alpha 延迟补偿详情】")
            if alpha_threshold != "N/A":
                print(f"  🔧 阈值: {alpha_threshold} (α/epoch_duration ≤ {alpha_threshold} 时忽略)")
            if static_ignored_links != "N/A" and used_ignored_links != "N/A":
                usage_rate = (used_ignored_links / static_ignored_links * 100) if static_ignored_links > 0 else 0
                print(f"  📊 被忽略链路: {used_ignored_links}/{static_ignored_links} ({usage_rate:.1f}%)")
            if schedule_based_compensation != "N/A":
                print(f"  ⏱️  补偿延迟: {schedule_based_compensation:.2f} μs ({schedule_based_compensation / 1000:.3f} ms)")
                if collective_finish_time != "N/A" and collective_finish_time > 0:
                    compensation_seconds = schedule_based_compensation / 1e6
                    impact_percent = (compensation_seconds / collective_finish_time) * 100
                    if algo_bandwidth != "N/A" and algo_bandwidth_scheduled != "N/A":
                        bandwidth_change = ((algo_bandwidth - algo_bandwidth_scheduled) / algo_bandwidth) * 100
                        print(f"  📉 性能影响: 时间+{impact_percent:.2f}%, 带宽-{bandwidth_change:.2f}%")
        
        if solver_time != "N/A":
            print(f"\n【求解器总用时】")
            print(f"  ⏱️  总用时: {solver_time:.2f} 秒 (s)")
            if solver_time >= 60:
                minutes = int(solver_time // 60)
                seconds = solver_time % 60
                print(f"      = {minutes} 分 {seconds:.1f} 秒")
        
        print("="*70 + "\n")
    
    def solve(self):
        """
            Main function that first finds a feasible collective finish time to estimate the number of epochs required
             if user did not provide it. It then finds the optimal solution and outputs the schedule to the file.
        """
        logs_dir = pathlib.Path("Logs")
        logs_dir.mkdir(exist_ok=True)
        user_input = self.user_input
        solver = self.solver
        if user_input.instance.debug:
            logging.basicConfig(format='%(asctime)s %(message)s',
                                datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG, filename=user_input.instance.debug_output_file)

        # Start timing: only core solving (feasibility search + encoding + solving + post-processing)
        # 简化：仅记录整体求解时间，不做阶段分解
        start_total = time()
        if user_input.instance.num_epochs == -1:
            feasible_time, _, _ = self.feasible_solution_search(
                user_input, self.topology_obj, solver.epoch_duration)
            user_input.instance.num_epochs = math.ceil(
                feasible_time / solver.epoch_duration)
            solver.set_num_epochs(user_input.instance.num_epochs)
        epoch_result_schedule_solver = self.get_schedules(
            solver, user_input, self.topology_obj)
        solver_time = time() - start_total

        if epoch_result_schedule_solver:
            # Always build a descriptive filename with topology, nodes, collective, data and chunks
            best_epochs = min(epoch_result_schedule_solver.keys())
            solver = epoch_result_schedule_solver[best_epochs]["solver"]
            collective_name = user_input.instance.collective.name  # e.g., "ALLGATHER" or "ALLTOALL"
            total_data_MB = user_input.topology.total_data_MB
            num_chunks = user_input.instance.num_chunks
            num_nodes = solver.num_nodes  # Get total number of nodes
            
            # Adaptive data size in filename: choose GB/MB/KB based on magnitude of total_data_MB
            def _fmt_size_mb(mb: float):
                if mb >= 1024.0:
                    val = mb / 1024.0
                    # Use integer if no fractional part, otherwise keep decimals
                    val = int(val) if val == int(val) else round(val, 4)
                    unit = 'GB'
                elif mb < 1.0:
                    val = mb * 1024.0
                    val = int(val) if val == int(val) else round(val, 4)
                    unit = 'KB'
                else:
                    val = int(mb) if mb == int(mb) else round(mb, 4)
                    unit = 'MB'
                return val, unit
            data_val, data_unit = _fmt_size_mb(total_data_MB)
            # Generate filename: Topology_NumNodes_Collective_Data[GB|MB|KB]_NumChunks.json
            filename = f'{user_input.topology.name}_{num_nodes}nodes_{collective_name}_{data_val}{data_unit}_{num_chunks}chunks.json'
            
            # Determine output directory
            if user_input.instance.schedule_output_folder:
                output_dir = pathlib.Path(user_input.instance.schedule_output_folder)
            else:
                output_dir = pathlib.Path('.')  # Current directory
            
            output_file = str(output_dir / filename)
            # Store solver time and breakdown (core solving only, excluding file I/O)
            epoch_result_schedule_solver[best_epochs]["schedule"][1]["Solver_Time"] = solver_time
            pathlib.Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w+') as f:
                json_obj = json.dumps(
                    epoch_result_schedule_solver[best_epochs]["schedule"][1], indent=2, sort_keys=True)
                f.write(json_obj)
            print(f'Schedule written to {output_file}')
            
            # 打印结果摘要
            self._print_result_summary(epoch_result_schedule_solver[best_epochs]["schedule"][1])

        else:
            logging.error("No schedule found with the given parameters")


