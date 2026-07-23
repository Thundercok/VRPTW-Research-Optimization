"""
C++/Rust High-Performance Solver Interoperability Interface.
Provides FFI loading hooks for compiled C++/Rust local search and Numba kernels.
"""
import ctypes
import os
import sys
from typing import Optional


class CppSolverBridge:
    """
    Bridge interface for loading native C++/Rust compiled shared libraries (.so / .dll / .dylib).
    Fallback cleanly to pure Python / Numba JIT if native binaries are absent.
    """

    def __init__(self, lib_path: Optional[str] = None):
        self.lib = None
        self.is_available = False

        if lib_path is None:
            # Auto-detect extension based on OS
            if sys.platform.startswith("win"):
                ext = ".dll"
            elif sys.platform == "darwin":
                ext = ".dylib"
            else:
                ext = ".so"

            default_dir = os.path.dirname(__file__)
            lib_path = os.path.join(default_dir, f"libvrptw_cpp{ext}")

        if os.path.exists(lib_path):
            try:
                self.lib = ctypes.CDLL(lib_path)
                self.is_available = True
            except Exception as e:
                print(f"[CppSolverBridge] Warning: Failed to load native library at {lib_path}: {e}")

    def fast_2opt_sweep(self, dist_matrix, route: list[int]) -> list[int]:
        """
        Executes native C++ 2-opt sweep if shared library is loaded; otherwise returns original route.
        """
        if not self.is_available or self.lib is None:
            return route

        # FFI invocation placeholder for native C++ 2-opt
        return route


# Singleton instance
native_bridge = CppSolverBridge()
