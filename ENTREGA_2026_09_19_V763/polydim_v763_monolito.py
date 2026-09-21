# ============================================================================
# POLYDIM V763 — MONOLITHIC PRODUCTION ORCHESTRATOR
# IEEE-754 Strict Precision | S^(D-1) Manifold Geometry | PMTP Zero-Copy IPC
# Multi-Platform Hardware Agnostic | C++/Rust/Triton FFI | Topological Guard
# ============================================================================

import os
import sys
import gc
import time
import mmap
import ctypes
import platform
import numpy as np
from typing import Tuple, Optional, Dict, Any

# Ensure Windows finds MinGW runtime DLLs
if platform.system() == "Windows" and hasattr(os, "add_dll_directory"):
    mingw_bin = r"E:\winlibs_gcc14_zip\mingw64\bin"
    if os.path.exists(mingw_bin):
        try:
            os.add_dll_directory(mingw_bin)
        except Exception:
            pass

# ============================================================================
# 1. HARDWARE PROBE & DYNAMIC SILICON DISCOVERY
# ============================================================================
class HardwareProbe:
    @staticmethod
    def detect_environment() -> Dict[str, Any]:
        info = {
            "os": sys.platform,
            "cpu_threads": os.cpu_count() or 4,
            "cuda_available": False,
            "rocm_available": False,
            "recommended_backend": "CPU_OPENMP"
        }
        try:
            import torch
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                info["cuda_available"] = True
                info["gpu_name"] = device_name
                info["recommended_backend"] = "CUDA_TRITON"
        except Exception:
            pass

        return info

# ============================================================================
# 2. PMTP ZERO-COPY SHARED MEMORY CHANNEL
# ============================================================================
class PMTPSlabChannel:
    def __init__(self, tag: str, dimension: int, create: bool = True):
        self.tag = tag
        self.D = dimension
        self.tensor_bytes = dimension * 8
        # Header: 64 bytes Control (Byte 0: atomic state) + 3 slots of D * 8 bytes
        self.total_bytes = 64 + 3 * self.tensor_bytes
        self.shm_name = f"polydim_pmtp_{tag}"
        self.create = create
        
        if sys.platform == "win32":
            self.mmap_obj = mmap.mmap(-1, self.total_bytes, tagname=self.shm_name, access=mmap.ACCESS_WRITE)
        else:
            import posix_ipc
            flags = posix_ipc.O_CREAT if create else 0
            self.posix_shm = posix_ipc.SharedMemory(f"/{self.shm_name}", flags, size=self.total_bytes)
            self.mmap_obj = mmap.mmap(self.posix_shm.fd, self.total_bytes)

        if create:
            # Estado inicial: newest=2, middle=1, oldest=0, fresh=0 -> 0b00100100 = 0x24
            self.mmap_obj[0] = 0x24

    def write_tensor(self, tensor_f64: np.ndarray) -> int:
        assert tensor_f64.dtype == np.float64 and tensor_f64.size == self.D
        # 1. Extraer slot newest (bits 4-5)
        state = self.mmap_obj[0]
        slot = (state >> 4) & 3
        
        # 2. Copia directa en el slot newest
        offset = 64 + slot * self.tensor_bytes
        dest_view = np.frombuffer(self.mmap_obj, dtype=np.float64, count=self.D, offset=offset)
        np.copyto(dest_view, tensor_f64)
        del dest_view
        
        # 3. Commit: swap newest y middle, marcar bit 6 (fresh)
        oldest = state & 3
        middle = (state >> 2) & 3
        newest = slot
        new_state = oldest | (newest << 2) | (middle << 4) | (1 << 6)
        self.mmap_obj[0] = new_state
        return slot

    def read_tensor(self) -> Optional[np.ndarray]:
        state = self.mmap_obj[0]
        # Si bit 6 no está activo, no hay dato nuevo
        if not (state & (1 << 6)):
            return None
        
        oldest = state & 3
        middle = (state >> 2) & 3
        newest = (state >> 4) & 3
        # Swap middle y oldest, apagar bit 6 (fresh)
        new_state = middle | (oldest << 2) | (newest << 4)
        self.mmap_obj[0] = new_state
        
        offset = 64 + middle * self.tensor_bytes
        # Copia inmutable desacoplada de la memoria compartida viva
        src_view = np.frombuffer(self.mmap_obj, dtype=np.float64, count=self.D, offset=offset)
        tensor_copy = np.copy(src_view)
        del src_view
        return tensor_copy

    def close(self):
        gc.collect()
        if hasattr(self, 'mmap_obj') and self.mmap_obj:
            try:
                self.mmap_obj.close()
            except BufferError:
                pass

# ============================================================================
# 3. NATIVE FFI KERNEL WRAPPER (C++ & RUST)
# ============================================================================
class PolydimNativeCore:
    def __init__(self, cpp_dll_path: str, rust_dll_path: str):
        if not os.path.exists(cpp_dll_path):
            raise FileNotFoundError(f"C++ Kernel DLL not found: {cpp_dll_path}")
        if not os.path.exists(rust_dll_path):
            raise FileNotFoundError(f"Rust Guard DLL not found: {rust_dll_path}")

        bin_dir = os.path.dirname(os.path.abspath(cpp_dll_path))
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(bin_dir)
            except Exception:
                pass

        self.cpp_lib = ctypes.CDLL(cpp_dll_path)
        self.rust_lib = ctypes.CDLL(rust_dll_path)

        # C++ Rodrigues
        self.cpp_lib.polydim_rodrigues_geodesic_f64.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_double, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_void_p
        ]
        self.cpp_lib.polydim_rodrigues_geodesic_f64.restype = ctypes.c_int32

        # C++ Stiefel Cayley-SMW
        self.cpp_lib.polydim_stiefel_cayley_smw_f64.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_uint64, ctypes.c_uint32, ctypes.c_double,
            ctypes.c_void_p, ctypes.c_void_p
        ]
        self.cpp_lib.polydim_stiefel_cayley_smw_f64.restype = ctypes.c_int32

        # C++ Selftest (P1.4: detect -ffast-math at load time)
        self.cpp_lib.polydim_selftest_all.argtypes = []
        self.cpp_lib.polydim_selftest_all.restype = ctypes.c_int32
        rc = self.cpp_lib.polydim_selftest_all()
        if rc != 0:
            raise RuntimeError(f"polydim_selftest_all FAILED: rc={rc} — DLL compiled with -ffast-math?")

        # C++ Build Info
        self.cpp_lib.polydim_build_info.argtypes = []
        self.cpp_lib.polydim_build_info.restype = ctypes.c_char_p

        # Rust Invariant Guard (5 args: y, u, v, d, *mut VerifyReport)
        class VerifyReport(ctypes.Structure):
            _fields_ = [
                ('norm_drift', ctypes.c_double),
                ('basis_uu_err', ctypes.c_double),
                ('basis_vv_err', ctypes.c_double),
                ('basis_uv_err', ctypes.c_double),
                ('bound_used', ctypes.c_double),
                ('subnormal_count', ctypes.c_uint64),
                ('nonfinite_count', ctypes.c_uint64),
            ]
        self.VerifyReport = VerifyReport

        self.rust_lib.polydim_rust_verify_invariants.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
            ctypes.c_size_t, ctypes.POINTER(VerifyReport)
        ]
        self.rust_lib.polydim_rust_verify_invariants.restype = ctypes.c_int32


    def apply_rodrigues_geodesic(
        self,
        y: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        theta: float
    ) -> Tuple[np.ndarray, int]:
        assert y.dtype == np.float64 and u.dtype == np.float64 and v.dtype == np.float64
        D = y.size
        y_out = np.empty(D, dtype=np.float64)

        status = self.cpp_lib.polydim_rodrigues_geodesic_f64(
            y.ctypes.data,
            u.ctypes.data,
            v.ctypes.data,
            y_out.ctypes.data,
            ctypes.c_double(theta),
            ctypes.c_uint64(D),
            None,
            None
        )
        return y_out, status

    def apply_stiefel_retraction(
        self,
        X: np.ndarray,
        G: np.ndarray,
        tau: float
    ) -> Tuple[np.ndarray, int]:
        assert X.dtype == np.float64 and G.dtype == np.float64
        D, K = X.shape
        Y_out = np.empty((D, K), dtype=np.float64)

        status = self.cpp_lib.polydim_stiefel_cayley_smw_f64(
            X.ctypes.data,
            G.ctypes.data,
            Y_out.ctypes.data,
            ctypes.c_uint64(D),
            ctypes.c_uint32(K),
            ctypes.c_double(tau),
            None,
            None
        )
        return Y_out, status

    def verify_rust_invariants(self, tensor: np.ndarray) -> Tuple[int, float]:
        assert tensor.dtype == np.float64
        D = tensor.size
        report = self.VerifyReport()
        status = self.rust_lib.polydim_rust_verify_invariants(
            tensor.ctypes.data,
            None,
            None,
            ctypes.c_size_t(D),
            ctypes.byref(report)
        )
        return status, report.norm_drift

    def verify_betti1(self, adj_matrix: np.ndarray, threshold: float = 0.5) -> int:
        assert adj_matrix.dtype == np.float64
        N = adj_matrix.shape[0]
        return self.rust_lib.polydim_rust_betti1_guard(
            adj_matrix.ctypes.data,
            ctypes.c_size_t(N),
            ctypes.c_double(threshold)
        )

# ============================================================================
# 4. CANARY & SANITY EXECUTION ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    print("============================================================================")
    print("POLYDIM V762 — PRODUCTION MONOLITH INGESTION CANARY")
    print("============================================================================")
    hw = HardwareProbe.detect_environment()
    print(f"Hardware Discovery: {hw}")
