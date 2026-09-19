import ctypes
import numpy as np
import sys
import os
import multiprocessing.shared_memory as shm

from hardware_probe_v760 import HardwareProbe

F64_TINY = np.finfo(np.float64).tiny

# BG-05: Strict Boundary Sanitization
def require_f64_vector(x, dim=None, reject_subnormal=True):
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"FATAL: Expected 1D, got {arr.ndim}")
    if dim is not None and arr.shape[0] != dim:
        raise ValueError(f"FATAL: Dimension mismatch. Expected {dim}, got {arr.shape[0]}")
    
    if not np.all(np.isfinite(arr)):
        raise ValueError("FATAL: NaN/Inf detected in tensor")
    
    subnormal = (arr != 0.0) & (np.abs(arr) < F64_TINY)
    if np.any(subnormal):
        if reject_subnormal:
            raise ValueError("FATAL: Subnormal detected in tensor")
        arr = arr.copy()
        arr[subnormal] = 0.0
        
    if not arr.flags.c_contiguous:
        arr = np.ascontiguousarray(arr, dtype=np.float64)
    return arr


class PMTP_Orchestrator_V760:
    """
    POLYDIM V760 — Polymorphic Zero-Copy PMTP Orchestrator
    Dynamically binds CUDA, AMD ROCm/HIP, or CPU OpenMP backend via HardwareProbe.
    """
    def __init__(self, d_dim, cpp_dll_path=None, rust_dll_path=None, runner_path=None):
        self.D = d_dim
        
        # Interrogate Hardware
        self.spec = HardwareProbe.contract()
        print(f"[PMTP V760] Backend: {self.spec.backend.upper()} | Device: {self.spec.device_name}")
        
        # Load C++ Kernel
        if cpp_dll_path and os.path.exists(cpp_dll_path):
            self.cpp_lib = ctypes.CDLL(cpp_dll_path)
            self.cpp_lib.polydim_publish_write.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64]
        else:
            self.cpp_lib = None
            
        # Load Rust Guard
        if rust_dll_path and os.path.exists(rust_dll_path):
            self.rust_lib = ctypes.CDLL(rust_dll_path)
        else:
            self.rust_lib = None
            
        # Polymorphic Runner Dispatch
        self.runner_lib = None
        if runner_path and os.path.exists(runner_path):
            self.runner_lib = ctypes.CDLL(runner_path)
            if self.spec.backend == "cuda":
                self.runner_lib.launch_triton_cubin.argtypes = [
                    ctypes.c_char_p, ctypes.c_char_p, 
                    ctypes.POINTER(ctypes.c_uint64),
                    ctypes.c_int,
                    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                    ctypes.c_uint
                ]
            elif self.spec.backend == "rocm":
                self.runner_lib.launch_triton_hsaco.argtypes = [
                    ctypes.c_char_p, ctypes.c_char_p, 
                    ctypes.POINTER(ctypes.c_uint64),
                    ctypes.c_int,
                    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                    ctypes.c_uint, ctypes.c_uint, ctypes.c_uint,
                    ctypes.c_uint
                ]

    def write_tensor_to_pmtp(self, x, ctrl_ptr, buffer_idx, next_seq):
        """Writes tensor to inactive buffer and atomically publishes it."""
        safe_x = require_f64_vector(x, dim=self.D)
        if self.cpp_lib:
            self.cpp_lib.polydim_publish_write(ctypes.c_void_p(ctrl_ptr), buffer_idx, next_seq)
            
    def launch_accelerator_kernel(self, binary_path, kernel_name, gpu_pointers):
        """Polymorphic kernel launch (CUDA CUBIN or AMD HSACO)."""
        if not self.runner_lib:
            raise RuntimeError("No accelerator runner loaded.")
            
        num_args = len(gpu_pointers)
        args_array = (ctypes.c_uint64 * num_args)()
        for i, ptr in enumerate(gpu_pointers):
            args_array[i] = ctypes.c_uint64(ptr)
            
        b_bin = binary_path.encode('utf-8')
        b_kernel = kernel_name.encode('utf-8')
        
        if self.spec.backend == "cuda":
            self.runner_lib.launch_triton_cubin(
                b_bin, b_kernel, args_array, num_args,
                1024, 1, 1, 128, 1, 1, 0
            )
        elif self.spec.backend == "rocm":
            self.runner_lib.launch_triton_hsaco(
                b_bin, b_kernel, args_array, num_args,
                1024, 1, 1, 128, 1, 1, 0
            )

if __name__ == "__main__":
    print(HardwareProbe.report())
    orch = PMTP_Orchestrator_V760(d_dim=1_000_000)
    print("[POLYDIM V760] Orchestrator Initialized Successfully.")
