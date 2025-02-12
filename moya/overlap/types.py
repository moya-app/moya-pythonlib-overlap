from tenseal import BFVVector

OPRFPoint = tuple[int, int]
OPRFPoints = list[OPRFPoint]
VectorMatrix = list[list[BFVVector | None]]
IntMatrix = list[list[int]]

# Plain input and output number sets for running the overlap on
RawNumbers = list[int]
