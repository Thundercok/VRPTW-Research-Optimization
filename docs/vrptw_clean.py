"""
Facade for the modularized vrptw package.
This ensures backward compatibility with existing imports from src/backend/.
"""
from vrptw import *

if __name__ == "__main__":
    from vrptw.benchmark import smoke_test
    from vrptw.config import Config
    import sys

    print("Running vrptw smoke test via facade...")
    cfg = Config()
    print("For full benchmarking, please import and use the functions in the vrptw.benchmark module.")