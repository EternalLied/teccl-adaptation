from teccl.input_data import TopologyParams
from teccl.topologies.topology import Topology


class Torus(Topology):
    """
    Torus topology implementation.
    In a Torus, nodes are arranged in a 2D grid with wraparound connections:
    - Horizontal wraparound: rightmost node in each row connects to leftmost node in same row
    - Vertical wraparound: bottom node in each column connects to top node in same column
    
    This provides shorter paths compared to Mesh topology due to the wraparound connections.
    """
    def __init__(self, topo_input: TopologyParams):
        super().__init__(topo_input)

    def construct_topology(self, topo_input: TopologyParams):
        self.node_per_chassis = self.side_length ** 2

        speed = 50 / self.chunk_size  # 50 GB/s link speed
        # Each node is connected to its 4 neighbors with wraparound
        self.capacity = []
        for i in range(self.node_per_chassis):
            i_row = i // self.side_length
            i_col = i % self.side_length
            row = []
            for j in range(self.node_per_chassis):
                j_row = j // self.side_length
                j_col = j % self.side_length
                
                is_neighbor = False
                
                # Horizontal neighbors (with wraparound)
                if i_row == j_row:
                    # Regular horizontal neighbor
                    if abs(i_col - j_col) == 1:
                        is_neighbor = True
                    # Wraparound: leftmost ↔ rightmost in same row
                    elif (i_col == 0 and j_col == self.side_length - 1) or \
                         (i_col == self.side_length - 1 and j_col == 0):
                        is_neighbor = True
                
                # Vertical neighbors (with wraparound)
                if i_col == j_col:
                    # Regular vertical neighbor
                    if abs(i_row - j_row) == 1:
                        is_neighbor = True
                    # Wraparound: top ↔ bottom in same column
                    elif (i_row == 0 and j_row == self.side_length - 1) or \
                         (i_row == self.side_length - 1 and j_row == 0):
                        is_neighbor = True
                
                if is_neighbor:
                    row.append(speed)
                else:
                    row.append(0)
            self.capacity.append(row)

        # Set alpha (propagation delay) for all links
        self.alpha = []
        for r in self.capacity:
            row = []
            for i in r:
                if i:
                    row.append(0.5e-6)  # 0.5 microsecond propagation delay
                else:
                    row.append(-1)
            self.alpha.append(row)

    def set_switch_indicies(self) -> None:
        """Torus has no switches, all nodes are GPUs"""
        super().set_switch_indicies()
