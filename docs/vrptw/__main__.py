from .benchmark import smoke_test
from .generators import SyntheticVRPTWGenerator

if __name__ == "__main__":
    print("Launching VRPTW Application...")
    inst = SyntheticVRPTWGenerator(n_nodes=25, distribution="RC", seed=42).generate()
    smoke_test(inst, seed=42)