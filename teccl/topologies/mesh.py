from teccl.input_data import TopologyParams
from teccl.topologies.topology import Topology


class Mesh(Topology):
    def __init__(self, topo_input: TopologyParams):
        super().__init__(topo_input)

    def construct_topology(self, topo_input: TopologyParams):
        self.node_per_chassis = self.side_length ** 2

        speed = 50 / self.chunk_size  # 修改为 50 GB/s
        # Each node is only connected to its neighbors (with proper boundary checks)
        self.capacity = []
        for i in range(self.node_per_chassis):
            i_row = i // self.side_length
            i_col = i % self.side_length
            row = []
            for j in range(self.node_per_chassis):
                j_row = j // self.side_length
                j_col = j % self.side_length
                # Check if j is a valid neighbor: same row (left/right) or same col (up/down)
                is_neighbor = False
                if i_row == j_row and abs(i_col - j_col) == 1:  # Same row, adjacent column
                    is_neighbor = True
                elif i_col == j_col and abs(i_row - j_row) == 1:  # Same column, adjacent row
                    is_neighbor = True
                
                if is_neighbor:
                    row.append(speed)
                else:
                    row.append(0)
            self.capacity.append(row)

        self.alpha = []
        for r in self.capacity:
            row = []
            for i in r:
                if i:
                    row.append(0.5e-6)  # 修改为 0.5 微秒
                else:
                    row.append(-1)
            self.alpha.append(row)

    def set_switch_indicies(self) -> None:
        super().set_switch_indicies()
