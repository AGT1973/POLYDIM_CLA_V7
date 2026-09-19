# ============================================================================
# POLYDIM V761 — MONOLITH PYTHON ORCHESTRATOR & ZERO-COPY IPC ENGINE
# IEEE-754 Strict Precision | S^(D-1) Manifold Geometry | PMTP Double-Buffer IPC
# ============================================================================

import os
import sys
import gc
import mmap
import math
import ctypes
import platform
import numpy as np
from typing import Tuple, Optional
from hardware_probe_v761 import HardwareProbe, HardwareSpec

# Ensure Windows finds MinGW runtime DLLs if needed
if platform.system() == "Windows" and hasattr(os, "add_dll_directory"):
    mingw_bin = r"E:\winlibs_gcc14_zip\mingw64\bin"
    if os.path.exists(mingw_bin):
        try:
            os.add_dll_directory(mingw_bin)
        except Exception:
            pass

# ============================================================================
# 1. C-TYPES STRUCTURES & BINDINGS
# ============================================================================
class PMTPControl(ctypes.Structure):
    _fields_ = [("state", ctypes.c_uint64)]

class PolydimMonolithEngine:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.spec = HardwareProbe.probe()
        
        dll_ext = ".dll" if platform.system() == "Windows" else ".so"
        bin_dir = os.path.join(self.base_dir, "bin")
        if platform.system() == "Windows" and hasattr(os, "add_dll_directory") and os.path.exists(bin_dir):
            try:
                os.add_dll_directory(bin_dir)
            except Exception:
                pass

        cpp_dll_path = os.path.join(bin_dir, f"polydim_kernel{dll_ext}")
        rust_dll_path = os.path.join(bin_dir, f"polydim_rust_guard{dll_ext}")

        if not os.path.exists(cpp_dll_path):
            raise FileNotFoundError(f"C++ Kernel DLL missing: {cpp_dll_path}")
        if not os.path.exists(rust_dll_path):
            raise FileNotFoundError(f"Rust Guard DLL missing: {rust_dll_path}")

        self.cpp_lib = ctypes.CDLL(cpp_dll_path)
        self.rust_lib = ctypes.CDLL(rust_dll_path)

        self._setup_bindings()

    def _setup_bindings(self):
        # C++ bindings
        self.cpp_lib.polydim_init_control.argtypes = [ctypes.POINTER(PMTPControl)]
        self.cpp_lib.polydim_init_control.restype = None

        self.cpp_lib.polydim_publish_write.argtypes = [ctypes.POINTER(PMTPControl), ctypes.c_uint64, ctypes.c_uint64]
        self.cpp_lib.polydim_publish_write.restype = None

        self.cpp_lib.polydim_acquire_read.argtypes = [
            ctypes.POINTER(PMTPControl),
            ctypes.POINTER(ctypes.c_uint64),
            ctypes.POINTER(ctypes.c_uint64)
        ]
        self.cpp_lib.polydim_acquire_read.restype = ctypes.c_bool

        self.cpp_lib.polydim_apply_rodrigues_geodesic_f64.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_double,
            ctypes.c_uint64
        ]
        self.cpp_lib.polydim_apply_rodrigues_geodesic_f64.restype = ctypes.c_int32

        self.cpp_lib.compute_gram_and_factorize.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int32
        ]
        self.cpp_lib.compute_gram_and_factorize.restype = ctypes.c_int32

        self.cpp_lib.polydim_stiefel_cayley_smw_retraction_f64.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_uint64,
            ctypes.c_uint32,
            ctypes.c_double
        ]
        self.cpp_lib.polydim_stiefel_cayley_smw_retraction_f64.restype = ctypes.c_int32

        # Rust bindings
        self.rust_lib.polydim_rust_verify_invariants.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_double)
        ]
        self.rust_lib.polydim_rust_verify_invariants.restype = ctypes.c_int32

        self.rust_lib.polydim_rust_betti1_guard.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_size_t,
            ctypes.c_double
        ]
        self.rust_lib.polydim_rust_betti1_guard.restype = ctypes.c_int32

    def apply_rodrigues_geodesic(
        self,
        y: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        theta: float
    ) -> Tuple[int, np.ndarray]:
        D = y.shape[0]
        y_c = np.ascontiguousarray(y, dtype=np.float64)
        u_c = np.ascontiguousarray(u, dtype=np.float64)
        v_c = np.ascontiguousarray(v, dtype=np.float64)
        y_out = np.zeros(D, dtype=np.float64)

        status = self.cpp_lib.polydim_apply_rodrigues_geodesic_f64(
            y_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            u_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            v_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            y_out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_double(theta),
            ctypes.c_uint64(D)
        )
        return status, y_out

    def apply_stiefel_cayley_smw(
        self,
        X: np.ndarray,
        G: np.ndarray,
        tau: float = 0.01
    ) -> Tuple[int, np.ndarray]:
        """Matrix-Free Cayley-SMW retraction for St(D, K) with K >= 1 agents."""
        D, K = X.shape
        X_c = np.ascontiguousarray(X, dtype=np.float64)
        G_c = np.ascontiguousarray(G, dtype=np.float64)
        Y_out = np.zeros((D, K), dtype=np.float64)

        status = self.cpp_lib.polydim_stiefel_cayley_smw_retraction_f64(
            X_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            G_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            Y_out.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_uint64(D),
            ctypes.c_uint32(K),
            ctypes.c_double(tau)
        )
        return status, Y_out

    def verify_rust_invariants(self, y: np.ndarray) -> Tuple[int, float]:
        D = y.shape[0]
        y_c = np.ascontiguousarray(y, dtype=np.float64)
        drift_out = ctypes.c_double(0.0)
        status = self.rust_lib.polydim_rust_verify_invariants(
            y_c.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_size_t(D),
            ctypes.byref(drift_out)
        )
        return status, drift_out.value

# ============================================================================
# 2. PMTP ZERO-COPY IPC SHM SLAB WITH MEMORY PINNING
# ============================================================================
class PMTPSlabChannel:
    def __init__(self, engine: PolydimMonolithEngine, max_dim: int = 1_000_000):
        self.engine = engine
        self.max_dim = max_dim
        self.vector_bytes = max_dim * 8
        self.ctrl_size = 64
        # Layout: Control Block (64B) + Buffer 0 (vector_bytes) + Buffer 1 (vector_bytes)
        self.total_bytes = self.ctrl_size + 2 * self.vector_bytes

        # Allocate anonymous shared memory
        self.mm = mmap.mmap(-1, self.total_bytes)
        self._pin_memory()

        # Initialize Control Block
        self.ctrl_ptr = PMTPControl.from_buffer(self.mm, 0)
        self.engine.cpp_lib.polydim_init_control(ctypes.byref(self.ctrl_ptr))
        
        self.seq_counter = 0

    def _pin_memory(self):
        """Pins virtual memory to RAM to prevent OS page faults during DMA."""
        system = platform.system()
        addr = ctypes.c_void_p.from_buffer(self.mm).value
        size = ctypes.c_size_t(self.total_bytes)
        if system == "Windows":
            try:
                kernel32 = ctypes.WinDLL("kernel32")
                kernel32.VirtualLock(addr, size)
            except Exception:
                pass
        elif system == "Linux":
            try:
                libc = ctypes.CDLL("libc.so.6")
                libc.mlock(addr, size)
            except Exception:
                pass

    def write_tensor_to_pmtp(self, x: np.ndarray) -> int:
        """Copies tensor into inactive double-buffer and publishes atomic generation tag."""
        safe_x = np.ascontiguousarray(x, dtype=np.float64)
        D = safe_x.size
        if D > self.max_dim:
            raise ValueError(f"Tensor dimension {D} exceeds allocated capacity {self.max_dim}")

        # Determine target buffer (ping-pong: alternate 0 and 1)
        target_buf_idx = (self.seq_counter + 1) % 2
        buf_offset = self.ctrl_size + target_buf_idx * self.vector_bytes

        # Write actual data into shared memory buffer (P0 FIX)
        raw_slice = np.frombuffer(self.mm, dtype=np.float64, count=D, offset=buf_offset)
        np.copyto(raw_slice, safe_x)

        # Increment monotonic sequence and publish
        self.seq_counter += 1
        self.engine.cpp_lib.polydim_publish_write(
            ctypes.byref(self.ctrl_ptr),
            ctypes.c_uint64(target_buf_idx),
            ctypes.c_uint64(self.seq_counter)
        )
        return self.seq_counter

    def read_tensor_from_pmtp(self, observed_seq: int, D: int) -> Tuple[bool, int, Optional[np.ndarray]]:
        """Reads latest tensor zero-copy if newer sequence exists."""
        obs_seq_c = ctypes.c_uint64(observed_seq)
        safe_buf_c = ctypes.c_uint64(0)

        has_new = self.engine.cpp_lib.polydim_acquire_read(
            ctypes.byref(self.ctrl_ptr),
            ctypes.byref(obs_seq_c),
            ctypes.byref(safe_buf_c)
        )

        if not has_new:
            return False, observed_seq, None

        new_seq = obs_seq_c.value
        active_buf = safe_buf_c.value
        buf_offset = self.ctrl_size + active_buf * self.vector_bytes
        tensor = np.frombuffer(self.mm, dtype=np.float64, count=D, offset=buf_offset).copy()
        return True, new_seq, tensor

    def close(self):
        if hasattr(self, 'ctrl_ptr'):
            del self.ctrl_ptr
        gc.collect()
        if hasattr(self, 'mm') and self.mm:
            try:
                self.mm.close()
            except Exception:
                pass

if __name__ == "__main__":
    print("=== POLYDIM V761 MONOLITH ENGINE SMOKE TEST ===")
    engine = PolydimMonolithEngine()
    D = 1_000_000
    print(f"Creating PMTP slab channel for D={D:,}...")
    chan = PMTPSlabChannel(engine, max_dim=D)

    # Test tensor write & read
    x = np.ones(D, dtype=np.float64) / math.sqrt(D)
    seq = chan.write_tensor_to_pmtp(x)
    print(f"Published tensor sequence: {seq}")

    has_new, read_seq, read_x = chan.read_tensor_from_pmtp(0, D)
    print(f"Acquired tensor: has_new={has_new}, seq={read_seq}, shape={read_x.shape}")
    assert np.allclose(x, read_x), "PMTP Zero-Copy Data must match perfectly"

    # Test geodesic
    u = np.zeros(D, dtype=np.float64)
    v = np.zeros(D, dtype=np.float64)
    u[0::2] = 0.5 / math.sqrt(D)
    u[1::2] = -0.5 / math.sqrt(D)
    v[0::2] = -0.5 / math.sqrt(D)
    v[1::2] = 0.5 / math.sqrt(D)

    status, y_out = engine.apply_rodrigues_geodesic(x, u, v, theta=0.05)
    print(f"Rodrigues Step: Status={status}")
    assert status == 0, "Rodrigues geodesic must succeed"

    r_status, drift = engine.verify_rust_invariants(y_out)
    print(f"Rust Invariant Guard: Status={r_status}, Drift={drift:.4e}")
    assert r_status == 0, "Rust invariant must be preserved"

    chan.close()
    print(">>> POLYDIM V761 MONOLITH ENGINE: ALL SMOKE TESTS PASSED (EXIT CODE 0) <<<")
