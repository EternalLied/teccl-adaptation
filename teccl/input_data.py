from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Union, Optional


def parse_data_size(size_str: Union[str, float, int]) -> float:
    """
    Parse data size string with unit suffix and convert to MB.
    
    Args:
        size_str: Can be:
            - String with unit: "1KB", "4MB", "2GB", "1.5GB", etc.
            - Numeric value (interpreted as MB for backward compatibility)
    
    Returns:
        float: Size in MB
    
    Examples:
        "1KB" -> 0.0009765625
        "256KB" -> 0.25
        "4MB" -> 4.0
        "2GB" -> 2048.0
        1024 -> 1024.0 (interpreted as MB)
    """
    if isinstance(size_str, (int, float)):
        # Backward compatibility: numeric values are MB
        return float(size_str)
    
    # Parse string with unit
    size_str = str(size_str).strip().upper()
    
    # Match number (int or float) followed by optional unit
    match = re.match(r'^([0-9]*\.?[0-9]+)\s*(KB|MB|GB|K|M|G|B)?$', size_str, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Invalid data size format: {size_str}. Expected format: '1KB', '4MB', '2GB', or numeric value.")
    
    value = float(match.group(1))
    unit = (match.group(2) or 'MB').upper()  # Default to MB if no unit
    
    # Normalize unit aliases
    if unit in ['K', 'KB']:
        return value / 1024  # KB to MB
    elif unit in ['M', 'MB', 'B']:  # 'B' alone defaults to MB for backward compat
        return value
    elif unit in ['G', 'GB']:
        return value * 1024  # GB to MB
    else:
        raise ValueError(f"Unsupported unit: {unit}. Use KB, MB, or GB.")


@dataclass
class TopologyParams:
    name: str = "DGX1"
    chassis: int = 1
    total_data_MB: float = 1024  # Total data in MB (will be converted to chunk_size internally)
    total_data: Optional[str] = None  # Alternative: data size with unit like "1KB", "4GB", etc.
    chunk_size: float = 0.0  # in GB, auto-calculated from total_data_MB
    alpha: tuple = (0, 0)  # (link alpha, switch alpha)
    side_length: int = 4  # Only for Mesh and Torus topology
    
    def __post_init__(self):
        """Parse total_data if provided and override total_data_MB"""
        if self.total_data is not None:
            self.total_data_MB = parse_data_size(self.total_data)

@dataclass
class GurobiParams:
    time_limit: float = 0.5         # in hrs (30 minutes) https://www.gurobi.com/documentation/10.0/refman/timelimit.html 
    feasibility_tol: float = 1e-4   # https://www.gurobi.com/documentation/10.0/refman/feasibilitytol.html
    intfeas_tol: float = 1e-4       # https://www.gurobi.com/documentation/10.0/refman/intfeastol.html
    optimality_tol: float = 1e-4    # https://www.gurobi.com/documentation/10.0/refman/optimalitytol.html
    output_flag: int = 1            # https://www.gurobi.com/documentation/10.0/refman/outputflag.html
    log_file: str = ""              # https://www.gurobi.com/documentation/10.0/refman/logfile.html#parameter:LogFile
    log_to_console: int = 0         # https://www.gurobi.com/documentation/10.0/refman/logtoconsole.html
    mip_gap: float = 1e-4           # https://www.gurobi.com/documentation/10.0/refman/mipgap2.html
    mip_focus: int = 0              # https://www.gurobi.com/documentation/10.0/refman/mipfocus.html    
    crossover: int = -1             # https://www.gurobi.com/documentation/10.0/refman/crossover.html
    method: int = -1                # https://www.gurobi.com/documentation/10.0/refman/method.html
    heuristics: float = 0.05        # https://www.gurobi.com/documentation/9.5/refman/heuristics.html
    presolve: int = -1              # https://www.gurobi.com/documentation/9.5/refman/presolve.html
    solution_limit: int = 2000000 # https://www.gurobi.com/documentation/9.5/refman/solutionlimit.html

class ObjectiveType(Enum):
    """
        Different objective functions for AllGather.
        1 - BINARY_USED_EPOCHS - Uses a binary variable for each epoch and minimizes the number of used epochs.
        2 - TOTAL_DEMAND - Gives a reward starting from the epoch all the demands are met.
        3 - PAPER - For each demand met, gives a reward starting from the epoch the demand is met.
        4 - ASTAR - Motivate the solver to make as much progress towards the goal of satisfying all demands as possible in each epoch.
    """
    BINARY_USED_EPOCHS = 1 
    TOTAL_DEMAND = 2
    PAPER = 3
    ASTAR = 4

class Collective(Enum):
    ALLGATHER = 1
    ALLTOALL = 2

class EpochType(Enum):
    """ 
        Epoch_type is used to set the epoch duration. 
            1 - FASTEST_LINK - set epoch duration based on the fastest link (fine-grained epoch duration)
            2 - SLOWEST_LINK - set epoch duration based on the slowest link (coarse-grained epoch duration)
            3 - USER_INPUT - uses the input epoch duration 
    """
    FASTEST_LINK = 1
    SLOWEST_LINK = 2    
    USER_INPUT = 3

class SolutionMethod(Enum):
    """
        1 - One shot - The optimization is run till the time limit is reached or it finds a solution within the specified mip gap
        2 - Iterative - The optimization is run iteratively using binary search to find a solution within limit of num_epochs.
    """
    ONE_SHOT = 1
    ITERATIVE = 2

@dataclass
class InstanceParams:
    collective: Collective = Collective.ALLGATHER
    num_chunks: int = 1 # Number of chunks to be transferred from each node to each other node
    epoch_type: EpochType = EpochType.FASTEST_LINK 
    epoch_duration: float = -1
    epoch_multiplier: int = 1   # Multiplier for epoch duration (helpful for epoch_type != -1)
    num_epochs:int = -1         # Number of epochs to be run (-1 to automatically figure out the number of epochs)
    epsilon: float = pow(10, -1)
    alpha_threshold: float = 0.1 # Link alpha to epoch duration ratio threshold below which alpha is taken as 0
    alpha_epoch_duration_ratio_max: int = 200 # Maximum ratio of alpha to epoch duration (if exceeded, epoch duration is increased)
    switch_copy: bool = True # If True, switch can copy the chunks
    switch_to_gpu_link_on: bool = False # If False, the link from switch to node is taken as instantaneous 
    debug: bool = False # If True, prints debug information
    debug_output_file: str = "" # If debug is True, prints debug information to this file
    objective_type: ObjectiveType = ObjectiveType.PAPER # The objective function to be used (3 - The objective function used in the paper)
    solution_method: SolutionMethod = SolutionMethod.ONE_SHOT
    schedule_output_folder: str = "teccl/examples/schedules" # Default output folder for schedule files. Filename is auto-generated.
    allow_flow_splitting: bool = False # If True, AlltoAll uses LP (continuous flow variables); if False, uses MILP (integer flow variables)
    lower: bool = False # If true will use the lowering code from Meghan to lower the input.
    lower_xml: str = "" # If not empty, the XML is written to this file. Default is "Topology-Chunks-chunksize-timestamp.xml"
    warmstart: str = "" # If not empty, the warmstart file is used to warmstart the optimization.
    symmetry: bool = False # If true, nodes that are given as symmetric are constrainted to have same number of total flows. 
    
class UserInputParams:
    topology: TopologyParams = TopologyParams()
    gurobi: GurobiParams = GurobiParams()
    instance: InstanceParams = InstanceParams()