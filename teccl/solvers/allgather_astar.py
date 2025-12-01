from collections import defaultdict
import logging
import math
import time
from itertools import product
from typing import Dict, List, Set, Tuple
import copy

import gurobipy as gp
import numpy as np
from gurobipy import GRB
from teccl.input_data import *
from teccl.solvers.allgather import AllGatherFormulation
from teccl.topologies.topology import Topology

class AStarFormulation(AllGatherFormulation):
    def __init__(self, user_input: UserInputParams, topology: Topology, num_rounds=0):
        super().__init__(user_input, topology)
        self.model = gp.Model('AllGather_AStar')
        self.solver_name = "AStarSolver"
        self.buffer_look_ahead_count = 1
        self.all_models = []
        self.epsilon = 0.1
        self.beta = self.epsilon / 50

        self.compute_floyd_warshall()
        if num_rounds > 0:
            self.num_rounds = num_rounds
        else:

            beta_num_back = 0
            for i, j in product(self.nodes, self.nodes):
                if self.topology.capacity[i][j]:
                    epoch_capacity = self.topology.capacity[i][j] * self.epoch_duration
                    beta_num_back = max(beta_num_back, max(
                        0, int(1 / epoch_capacity) - 1))
            alpha_num_back = 0
            alpha = self.topology.alpha
            if len(alpha):
                max_alpha = max(
                    [max([x for x in self.topology.alpha[i]]) for i in range(len(alpha))])
                if (max_alpha / self.epoch_duration) > self.user_input.instance.alpha_threshold:
                    alpha_num_back = math.ceil(max_alpha / self.epoch_duration)
                self.buffer_look_ahead_count = alpha_num_back + 1
            # In each round at least one chunk can be delivered on any link
            minimum_epochs_per_round = alpha_num_back + beta_num_back
            self.numEpochsPerRound_ = max(15, minimum_epochs_per_round)
            # assert self.numEpochsPerRound_ < 15, "Number of epochs per round in A* is more than 20"
            self.num_rounds = int(
                self.num_epochs / self.numEpochsPerRound_) + 1
            self.num_epochs = self.numEpochsPerRound_
            self.epochs_ = list(range(self.num_epochs))
            self.total_epochs = self.num_epochs - 1

    def initialize_variables(self):
        # f (s, i, j, c, k) : flow going from source to destination on link (i,j) \in E at epoch K.
        # B (s, i, c, k) : buffer contents,
        # total_demand_sat (s, d) --> total demand sent from node s to node d.

        varType = GRB.INTEGER

        self.flow = np.zeros((self.num_nodes, self.num_nodes,
                            self.num_nodes, self.num_chunks, self.num_epochs)).tolist()

        for i, j, in product(self.nodes, self.nodes):
            if self.topology.capacity[i][j] <= 0:
                continue
            for s, c, k in product(self.nodes, self.chunks, self.epochs_):
                self.flow[s][i][j][c][k] = self.model.addVar(
                    0, 1, vtype=varType, name='flow_%d_%d_%d_%d_%d' % (s, i, j, c, k))

        self.buffer = np.zeros((self.num_nodes, self.num_nodes,
                            self.num_chunks, self.num_epochs)).tolist()
        self.total_demand_sat = np.zeros(
            (self.num_nodes, self.num_nodes, self.num_chunks, self.num_epochs)).tolist()

        for s, i, c, k in product(self.nodes, self.nodes, self.chunks, self.epochs_):
            self.buffer[s][i][c][k] = self.model.addVar(
                0, 1, vtype=varType, name='buffer_%d_%d_%d_%d' % (s, i, c, k))
            if self.demand[s][i][c]:
                self.total_demand_sat[s][i][c][k] = self.model.addVar(
                    0, 1, vtype=varType, name='total_demand_%d_%d_%d_%d' % (s, i, c, k))
                
        self.buffer_ahead = np.zeros((self.num_nodes, self.num_nodes,
                                       self.num_chunks, self.buffer_look_ahead_count)).tolist()
        # future_epoch 0 is the next epoch after the epochs in the round
        # future_epoch 0 = self.numEpochs
        # future_epoch 1 = self.numEpochs + 1
        for s, i, c, future_epoch in product(self.nodes, self.nodes, self.chunks, range(self.buffer_look_ahead_count)):
            self.buffer_ahead[s][i][c][future_epoch] = self.model.addVar(
                0, 1, vtype=GRB.INTEGER, name='buffer_ahead_%d_%d_%d_%d' % (s, i, c, future_epoch))

    def refresh_model(self):
        self.all_models.append(self.model)
        self.model = gp.Model('AllGather_AStar')
        self.aux_t_ = []
        self.aux_sat_ = []

    def add_buffer_look_ahead_constraints_helper(self, i, s, c, future_epoch):
        buffer_constr = gp.LinExpr(0.0)
        if i not in self.topology.switch_indices:
            if future_epoch == 0:
                buffer_constr.add(self.buffer[s][i][c][self.num_epochs - 1])
            else:
                buffer_constr.add(self.buffer_ahead[
                                  s][i][c][future_epoch - 1])
        for j in range(self.num_nodes):
            if self.topology.capacity[j][i] > 0:
                link_alpha = self.topology.alpha[j][i]
                epoch_capacity = self.topology.capacity[j][i] * self.epoch_duration
                beta_num_back = max(0, int(1 / epoch_capacity) - 1)
                if (link_alpha / self.epoch_duration) > self.user_input.instance.alpha_threshold:
                    num_back = math.ceil(link_alpha / self.epoch_duration)
                    if (self.num_epochs - 1 + future_epoch - num_back - beta_num_back) >= 0 and (self.num_epochs - num_back - 1 - beta_num_back + future_epoch) < self.num_epochs:
                        buffer_constr.add(
                            self.flow[s][j][i][c][self.num_epochs - num_back - beta_num_back - 1 + future_epoch])
                else:
                    if future_epoch == 0:
                        buffer_constr.add(
                            self.flow[s][j][i][c][self.num_epochs - 1 - beta_num_back])
                    else:
                        # no flows in the look ahead with alpha=0
                        pass
        self.model.addConstr(buffer_constr == self.buffer_ahead[
                              s][i][c][future_epoch], name="buffer_look_ahead_s_%d_i_%d_c_%d_k_%d" % (s, i, c, future_epoch))

    def add_buffer_look_ahead_constraints(self):
        for i, s, c, future_epoch in product(self.nodes, self.nodes, self.chunks, range(self.buffer_look_ahead_count)):
            self.add_buffer_look_ahead_constraints_helper(
                i, s, c, future_epoch)

    def check_demand(self, previous_buffers):
        found = False
        for s, d, c in product(self.nodes, self.nodes, self.chunks):
            if self.demand[s][d][c] == 1:
                # If the chunk (s,c) reached/will reach destination d in the previous round then remove the corresponding demand
                if previous_buffers[s][d][c][self.buffer_look_ahead_count - 1] != 1:
                    return True
        return found

    def update_demand(self, previous_buffers):
        count = 0
        for s, d, c in product(self.nodes, self.nodes, self.chunks):
            if self.demand[s][d][c] == 1:
                # If the chunk (s,c) reached/will reach destination d in the previous round then remove the corresponding demand
                # This could be sub-optimal as in the next round the chunk may be received through another path before the chunk
                # from the current round reaches. However, with our constraint of adding to the buffer, Gurobi is forced to use
                # the path from the current round. (B <=1 and adding current round will make it 1 already)
                if previous_buffers[s][d][c][self.buffer_look_ahead_count - 1] == 1:
                    self.demand[s][d][c] = 0
                else:
                    count += 1
        return count

    def get_previous_buffer(self):
        previous_buffers = np.zeros((self.num_nodes, self.num_nodes,
                                     self.num_chunks, self.buffer_look_ahead_count)).tolist()
        for v in self.model.getVars():
            if ('buffer_ahead' in v.varName) and v.x > 0.0:
                ids = list(map(lambda x: int(x), v.varName.split("_")[2:]))
                previous_buffers[ids[0]][ids[1]][ids[2]][ids[3]] = v.x
        return previous_buffers
    
    def find_max_k(self):
        max_k = 0
        for v in self.model.getVars():
            if 'flow_' in v.varName and v.x > 0.0:
                if 'future' in v.varName:
                    continue
                components = v.varName.split('_')
                _, _, _, _, _, k = components
                if int(k) > max_k:
                    max_k = int(k)
        return max_k

    def count_used_epochs(self, round: int, previous_buffers):
        max_k = 0
        for s, d, c in product(self.nodes, self.nodes, self.chunks):
            if self.demand[s][d][c] == 1:
                found = False
                for k in range(self.buffer_look_ahead_count):
                    if previous_buffers[s][d][c][k] == 1:
                        found = True
                        max_k = max(max_k, k)
                        break
                assert found, "Error in A* as demand is not met"
        if max_k == 0:
            # Demand was met at some point in the final round
            self.total_epochs = (round - 1) * \
                self.num_epochs + self.find_max_k() + 1
        else:
            self.total_epochs = round * self.num_epochs + max_k

    def dfs_remove_unnecessary_flows(self, astar: bool) -> Tuple[List[Tuple[int, int, int, int, int]], Dict]:
        """
            This function removes the unnecessary flows from the list of flows.
            Traces the path of the chunk from the destination to the source accumulating the flows required to satisfy the demand.
            All the flows that are not required are removed.
        """
        from collections import defaultdict
        flows, demand_met_epoch, buffers, _ = self.get_flows_buffer_demand()

        # In an A* round, we can't say whether a flow is required or not until the end of all the rounds as
        #  the node receiving the chunk may be an intermediate node in the path to the destination in the later rounds.
        flows.sort(key=lambda x: x[4])
        flows_str_info = {}
        total_nodes = self.topology.node_per_chassis * self.topology.chassis
        flows_str_info["0-Total_Data_GB"] = total_nodes * self.topology.chunk_size * self.num_chunks
        flows_str_info["Collective_Type"] = self.user_input.instance.collective.name  # "ALLGATHER"
        flows_str_info["Num_Chunks"] = self.num_chunks
        flows_str_info["1-Epoch_Duration"] = self.epoch_duration
        flows_str_info["2-Expected_Epoch_Duration"] = self.expected_epoch_duration
        flows_str_info["3-Epochs_Required"] = self.total_epochs
        flows_str_info["4-Collective_Finish_Time"] = flows_str_info["1-Epoch_Duration"] * flows_str_info["3-Epochs_Required"]
        flows_str_info["5-Algo_Bandwidth"] = self.topology.node_per_chassis * self.topology.chunk_size * self.topology.chassis * self.num_chunks / flows_str_info["4-Collective_Finish_Time"]
        # Alpha post-processing compensation (ignored small alphas)
        alpha_threshold = self.user_input.instance.alpha_threshold
        # Static all-links scan (legacy):
        ignored_alphas_static = []
        for i in range(len(self.topology.alpha)):
            for j in range(len(self.topology.alpha[i])):
                link_alpha = self.topology.alpha[i][j]
                if link_alpha > 0 and (link_alpha / self.epoch_duration) <= alpha_threshold:
                    ignored_alphas_static.append(link_alpha)
        total_ignored_alpha_static = sum(ignored_alphas_static)
        max_ignored_alpha_static = max(ignored_alphas_static) if ignored_alphas_static else 0
        
        # Path-level per-epoch max schedule-based compensation (path_epoch_max):
        #  A* 模式下尚未构造精确的 (s,d,c) 完整路径，这里用近似：将最终到达 GPU (非 switch) 的最后一跳视作目的 d，
        #  并聚合该源 s 与 chunk c 在到达 d 之前所有相关 hop 被忽略 alpha。
        #  然后对每个 epoch 取所有路径的最大值，避免不同目的合并导致的高估。此近似可后续替换为完整路径回溯。
        path_epoch_alpha = defaultdict(lambda: defaultdict(float))  # (s,d,c) -> epoch -> ignored_alpha_sum
        # 标记最终目的节点: 最后一跳的接收节点且不是交换机
        final_hops = [(s,i,j,c,k) for s,i,j,c,k in flows if j not in self.topology.switch_indices]
        for s,i,j,c,k in flows:
            if self.topology.capacity[i][j] <= 0:
                continue
            link_alpha = self.topology.alpha[i][j]
            if link_alpha <= 0 or (link_alpha / self.epoch_duration) > alpha_threshold:
                continue
            # 找到与该 (s,c) 相关的最终目的集合
            destinations = [jh for ss,ii,jh,cc,kk in final_hops if ss==s and cc==c and kk>=k]
            if not destinations:
                continue
            # 将该 hop 贡献给所有尚未完成的目的的路径（保守，不会低估单条路径 alpha）
            for d in destinations:
                path_epoch_alpha[(s,d,c)][k] += link_alpha
        per_epoch_path_alpha = defaultdict(dict)
        for path_key, epoch_map in path_epoch_alpha.items():
            for ek, val in epoch_map.items():
                per_epoch_path_alpha[ek][path_key] = val
        # Ensure we report a compensation value for every epoch up to the number of epochs required.
        epochs_required = self.find_demand_satisfied_k() + 1
        epoch_max_compensations = []
        for k in range(epochs_required):
            if k in per_epoch_path_alpha and per_epoch_path_alpha[k]:
                epoch_max_compensations.append(max(per_epoch_path_alpha[k].values()))
            else:
                epoch_max_compensations.append(0.0)
        total_schedule_based_compensation = sum(epoch_max_compensations)
        
        used_ignored_links = set()
        for s, i, j, c, k in flows:
            link_alpha = self.topology.alpha[i][j]
            if link_alpha > 0 and (link_alpha / self.epoch_duration) <= alpha_threshold:
                used_ignored_links.add((i, j))
        
        flows_str_info["Alpha_Threshold"] = alpha_threshold
        flows_str_info["Static_Ignored_Alpha_Links_Count"] = len(ignored_alphas_static)
        flows_str_info["Used_Ignored_Alpha_Links_Count"] = len(used_ignored_links)
        flows_str_info["Compensation_Strategy"] = "path_epoch_max"
        flows_str_info["Path_Count"] = len(path_epoch_alpha)
        flows_str_info["Epoch_Compensation_us"] = [v * 1e6 for v in epoch_max_compensations]
        flows_str_info["Schedule_Based_Compensation_us"] = total_schedule_based_compensation * 1e6  # Convert to microseconds
        
        # Chunk-epoch grouped compensation (Option C):
        flows_str_info["4b-Collective_Finish_Time_ScheduleBased"] = flows_str_info["4-Collective_Finish_Time"] + total_schedule_based_compensation
        if flows_str_info["4b-Collective_Finish_Time_ScheduleBased"] > 0:
            flows_str_info["5b-Algo_Bandwidth_ScheduleBased"] = self.topology.node_per_chassis * self.topology.chunk_size * self.topology.chassis * self.num_chunks / flows_str_info["4b-Collective_Finish_Time_ScheduleBased"]
        else:
            flows_str_info["5b-Algo_Bandwidth_ScheduleBased"] = flows_str_info["5-Algo_Bandwidth"]
        flows_str_info['7-Flows'] = [
            f"Chunk {c} from {s} traveled over {i}->{j} in epoch {k}" for s, i, j, c, k in flows]
        return flows, flows_str_info


    def astar_objective_clique(self):
        def initialize_flow(i, j, look_ahead_index, bound):
            # No self edges and no same source and destination
            self.flows_[i][j][look_ahead_index] = self.model.addVar(
                0, bound, vtype=GRB.CONTINUOUS, name='future_flow_%d_%d_%d' % (i, j, look_ahead_index))

        self.flows_ = np.zeros(
            (self.num_nodes, self.num_nodes, self.buffer_look_ahead_count)).tolist()

        all_pair_shortest = self.floyd_warshall
        objective = gp.LinExpr(0.0)
        mulitplier = 10
        sum_end = self.num_nodes * 2 + self.num_chunks + self.num_epochs

        for n, d, c, k in product(self.nodes, self.nodes, self.chunks, self.epochs_):
            my_contribution = 1 + ((n + d + c + k) / sum_end)
            objective.add(self.total_demand_sat[
                n][d][c][k], -mulitplier * round(my_contribution * (self.epsilon / (k + 1)), 5))
            # for i in self.nodes:
            #     if self.topology[i][d] <= 0:
            #         continue
            #     objective.add(self.flow[s][i][d][c][k], 10 * self.gamma_)

        for d in self.nodes:
            total_demand = 0
            for source_id in self.nodes:
                for chunk_id in self.chunks:
                    total_demand += self.demand[source_id][d][chunk_id]
            if total_demand == 0:
                continue
            for look_ahead_index in range(self.buffer_look_ahead_count):
                sum_across_all_nodes = gp.LinExpr(0.0)
                for s in self.nodes:
                    # if n == d:
                    #     continue
                    sum_buffers = gp.LinExpr(0.0)
                    for c in self.chunks:
                        for n in self.nodes:
                            if d == n or self.demand[n][d][c] == 0:
                                # total_demand assumes there is no self demand
                                continue
                            sum_buffers.add(self.buffer_ahead[
                                            n][s][c][look_ahead_index])
                    initialize_flow(s, d, look_ahead_index, total_demand)
                    if s == d:
                        objective.add(
                            self.flows_[s][d][look_ahead_index], -mulitplier * round((pow((look_ahead_index + 1), -1) * pow(self.beta, 0)), 5))
                    else:
                        objective.add(
                            self.flows_[s][d][look_ahead_index], -mulitplier * round((pow((look_ahead_index + 1), -1) * self.beta / (1 + all_pair_shortest[s][d])), 5))
                    self.model.addConstr(
                        self.flows_[s][d][look_ahead_index] <= sum_buffers, name="Future_Flow_Less_Buffer_s_%d_d_%d_look_ahead_%d" % (s, d, look_ahead_index))
                    sum_across_all_nodes.add(
                        self.flows_[s][d][look_ahead_index])
                self.model.addConstr(sum_across_all_nodes == total_demand,
                                      name="sum_across_all_nodes_d_%d_look_ahead_%d" % (d, look_ahead_index))
        return objective

    def get_per_chunk_flows(self):
        return self.sends_

    def store_flows(self, round):
        for v in self.model.getVars():
            if 'flow_' in v.varName and v.x > 0.0:
                if 'future' in v.varName:
                    continue
                components = v.varName.split('_')
                _, s_t, i, j, c, k = components
                self.sends_[int(k) + (round * self.numEpochsPerRound_)
                            ].append((int(s_t), int(c), int(i), int(j)))
    
    def source_constraints(self):
        # Source constraints are constraints that
        # encode how much the source is allowed to send.
        for s, j, c in product(self.nodes, self.nodes, self.chunks):
            if self.topology.capacity[s][j] <= 0:
                continue
            src_cnstr = gp.LinExpr(0.0)
            dem = max(self.demand[s, :, c])
            for k in self.epochs_:
                src_cnstr.add(self.flow[s][s][j][c][k])
            self.model.addConstr(
                src_cnstr <= dem, name="source_s_%d_j_%d_c_%d" % (s, j, c))

    def encode_problem(self, output_folder="", filename="", basename="", debug=False, warmstart="", gurobi_args={}, use_one_less_epoch=False):
        previous_buffers = None
        self.sends_ = defaultdict(list)
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        logging.debug(
            f"A* starting with {self.num_rounds} rounds and {self.num_epochs} per round")
        setup_start = time.time()
        for round in range(self.num_rounds):
            if round > 0:
                previous_buffers = self.get_previous_buffer()
                found_demand = self.check_demand(previous_buffers)
                if not found_demand:
                    self.count_used_epochs(round, previous_buffers)
                    logging.debug(f"A* finished the demand requirement for {self.num_epochs} epochs per "
                                  f"round in {round} rounds with {self.total_epochs} epochs")
                    if filename != "":
                        logging.debug(setup_start, setup_end, solve_start, solve_end, self,
                                            output_folder, filename + "_AStarSolver_", basename)
                    return 1
                else:
                    # Demand could not be satisfied in the last round so we need another round
                    count = self.update_demand(previous_buffers)
                    logging.debug(
                        f"Demand {count} at the start of round {round}")
            setup_start = time.time()
            self.refresh_model()
            self.initialize_variables()
            self.source_constraints()
            self.destination_constraints(astar_multiple_rounds=True)
            self.node_constraints(previous_buffers)
            self.capacity_constraints()
            self.add_buffer_look_ahead_constraints()
            self.model.setObjective(self.astar_objective_clique())
            setup_end = time.time()

            self.model.Params.OutputFlag = 1
            self.model.setParam(
                "LogFile", f'Logs/AStar_nodes-{self.num_nodes}_chunks-{self.num_chunks}_epochs-{self.num_epochs}_round-{round}.log')
            self.model.Params.LogToConsole = 0
            if debug:
                self.model.write(
                    f'Logs/AStar_nodes-{self.num_nodes}_chunks-{self.num_chunks}_epochs-{self.num_epochs}_round-{round}.lp')
                self.model.Params.OutputFlag = 1
                self.model.setParam(
                    "LogFile", f'Logs/AStar_nodes-{self.num_nodes}_chunks-{self.num_chunks}_epochs-{self.num_epochs}_round-{round}.log')
                self.model.Params.LogToConsole = 0
                logging.basicConfig(level=logging.DEBUG)

            solve_start = time.time()
            self.model.optimize()
            solve_end = time.time()

            if self.model.Status != GRB.OPTIMAL:
                if self.model.Status != GRB.TIME_LIMIT or (self.model.SolCount <= 0):
                    if filename != "":
                        logging.warning(
                            output_folder, filename + "_astar_", basename + f'round_{round}')
                    logging.warning(
                        f"Infeasible_{self.solver_name}_Status-{self.model.Status}_Round-{round}_Chunks-{self.num_chunks}_Epochs-{self.num_epochs}_EpochDuration-{self.epoch_duration}")
                    return -1
                else:
                    logging.debug(f'Solution count {self.model.SolCount}')
                    optimal_value = self.model.ObjBound
                    current_solution = self.model.ObjVal
                    diff = current_solution - optimal_value
                    diff = (diff * 100) / -optimal_value
                    logging.debug(f'A* finished round {round} with {diff} gap')

            logging.debug(f"A* model finished running!------------ epochs_per_round:{self.num_epochs}"
                          f" round: {round} solver_time: {solve_end-solve_start}")

            if filename != "":
                logging.debug(setup_start, setup_end, solve_start, solve_end, self,
                                    output_folder, filename + "_AStarSolver_", basename + f'round_{round}')

            if debug:
                self.model.write(
                    f'Logs/AStar_nodes-{self.num_nodes}_chunks-{self.num_chunks}_epochs-{self.num_epochs}_round-{round}.sol')

        self.store_flows(round)
        previous_buffers = self.get_previous_buffer()
        found_demand = self.check_demand(previous_buffers)
        if not found_demand:
            self.count_used_epochs(round + 1, previous_buffers)
            logging.debug(f"A* finished the demand requirement for {self.num_epochs} epochs per "
                          f"round in {round + 1} rounds with {self.total_epochs} epochs")
            if filename != "":
                logging.debug(setup_start, setup_end, solve_start, solve_end, self,
                                    output_folder, filename + "_AStarSolver_", basename)
            return 1
        return -1
    
    def get_schedule(self) -> Tuple[List[Tuple[int, int, int, int, int]], Dict]:
        if self.model.SolCount > 0:
            if not self.required_flows:
                self.required_flows, self.flows_str_info = self.dfs_remove_unnecessary_flows(
                    astar=True)
            return self.required_flows, self.flows_str_info
        else:
            return [], {}