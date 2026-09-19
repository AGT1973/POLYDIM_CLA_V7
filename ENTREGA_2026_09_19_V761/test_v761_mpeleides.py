# ============================================================================
# POLYDIM V761 (MPELEIDES RELEASE) — COMPREHENSIVE PHYSICAL TEST SUITE
# Real Silicon Verification | Strict Zero-Happy-Path | Exit Code 0 Guarantee
# ============================================================================

import os
import sys
import math
import time
import ctypes
import platform
import unittest
import numpy as np

# Ensure Windows finds MinGW runtime DLLs if needed
if platform.system() == "Windows" and hasattr(os, "add_dll_directory"):
    mingw_bin = r"E:\winlibs_gcc14_zip\mingw64\bin"
    if os.path.exists(mingw_bin):
        try:
            os.add_dll_directory(mingw_bin)
        except Exception:
            pass

from hardware_probe_v761 import HardwareProbe
from polydim_v761_monolito import PolydimMonolithEngine, PMTPSlabChannel, PMTPControl

class TestPolydimV761Physical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.dirname(os.path.abspath(__file__))
        cls.engine = PolydimMonolithEngine(cls.base_dir)
        cls.spec = cls.engine.spec

    def test_01_silicon_contract_probe(self):
        """Suite 1: Verify HardwareProbe dynamic querying (No hardcoding)."""
        print("\n--- SUITE 1: Hardware Probe Dynamic Verification ---")
        self.assertIn(self.spec.platform_system, ["Windows", "Linux", "Darwin"])
        self.assertGreater(self.spec.cpu_cores_logical, 0)
        self.assertIn(self.spec.cpu_cache_line_size, [32, 64, 128, 256])
        self.assertGreater(self.spec.available_ram_bytes, 1024 * 1024 * 1024)
        print(f"  System: {self.spec.platform_system} ({self.spec.architecture})")
        print(f"  RAM: {self.spec.available_ram_bytes / (1024**3):.2f} GB, L1 Cache Line: {self.spec.cpu_cache_line_size} B")
        print(f"  Backend: {self.spec.gpu_backend}")

    def test_02_rodrigues_geodesic_convergence(self):
        """Suite 2: Verify Rodrigues Geodesic Operator on S^(D-1) for D in [1K, 100K, 1M]."""
        print("\n--- SUITE 2: Rodrigues Geodesic Multi-Scale Invariant Verification ---")
        dimensions = [1_000, 100_000, 1_000_000]
        theta = 0.05

        for D in dimensions:
            t0 = time.perf_counter()
            inv_sqrt_d = 1.0 / math.sqrt(D)
            y = np.full(D, inv_sqrt_d, dtype=np.float64)
            u = np.zeros(D, dtype=np.float64)
            v = np.zeros(D, dtype=np.float64)

            u[0::2] = 0.5 * inv_sqrt_d
            u[1::2] = -0.5 * inv_sqrt_d
            v[0::2] = -0.5 * inv_sqrt_d
            v[1::2] = 0.5 * inv_sqrt_d

            status, y_out = self.engine.apply_rodrigues_geodesic(y, u, v, theta)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            self.assertEqual(status, 0, f"Rodrigues execution failed at D={D}")
            r_status, drift = self.engine.verify_rust_invariants(y_out)
            self.assertEqual(r_status, 0, f"Rust invariant violation at D={D}")
            self.assertLessEqual(drift, 1e-14, f"Drift exceeded tolerance at D={D}")

            print(f"  D = {D:9,d} | Status: OK | Time: {elapsed_ms:6.2f} ms | Drift: {drift:.2e}")

    def test_03_pmtp_zerocopy_data_integrity(self):
        """Suite 3: PMTP Zero-Copy IPC Multi-Hop Integrity."""
        print("\n--- SUITE 3: PMTP Zero-Copy IPC Multi-Hop Integrity ---")
        D = 500_000
        chan = PMTPSlabChannel(self.engine, max_dim=D)
        
        try:
            last_seq = 0
            for hop in range(5):
                # Generate unique pattern
                payload = np.random.randn(D).astype(np.float64)
                payload /= np.linalg.norm(payload)

                pub_seq = chan.write_tensor_to_pmtp(payload)
                self.assertGreater(pub_seq, last_seq)

                has_new, read_seq, read_payload = chan.read_tensor_from_pmtp(last_seq, D)
                self.assertTrue(has_new)
                self.assertEqual(read_seq, pub_seq)
                self.assertTrue(np.array_equal(payload, read_payload), f"Data corruption detected on hop {hop}")
                last_seq = read_seq
            print(f"  Successfully passed 5 multi-hop zero-copy transfers for D={D:,}")
        finally:
            chan.close()

    def test_04_adversarial_numerical_guards(self):
        """Suite 4: Adversarial Degenerate Inputs (NaN, Inf, Singular Gram Matrix)."""
        print("\n--- SUITE 4: Adversarial Attack Defense Verification ---")
        D = 10_000
        y = np.ones(D, dtype=np.float64) / math.sqrt(D)
        u = np.zeros(D, dtype=np.float64)
        v = np.zeros(D, dtype=np.float64)

        # 1. Inject NaN into input
        y_nan = y.copy()
        y_nan[42] = float('nan')
        status_nan, _ = self.engine.apply_rodrigues_geodesic(y_nan, u, v, 0.1)
        self.assertEqual(status_nan, -3, "Engine must reject NaN input with ERR_NAN_OR_INF (-3)")
        print("  [PASS] NaN injection gracefully intercepted (Status = -3)")

        # 2. Inject Inf into input
        y_inf = y.copy()
        y_inf[100] = float('inf')
        status_inf, _ = self.engine.apply_rodrigues_geodesic(y_inf, u, v, 0.1)
        self.assertEqual(status_inf, -3, "Engine must reject Inf input with ERR_NAN_OR_INF (-3)")
        print("  [PASS] Inf injection gracefully intercepted (Status = -3)")

        # 3. Singular Gram Matrix
        N = 4
        G_singular = np.ones((N, N), dtype=np.float64) # Rank 1 -> Singular
        R = np.zeros((N, N), dtype=np.float64)
        status_gram = self.engine.cpp_lib.compute_gram_and_factorize(
            G_singular.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            R.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_int32(N)
        )
        self.assertEqual(status_gram, -5, "Engine must trigger numerical fallback on singular Gram matrix")
        print("  [PASS] Singular Gram matrix gracefully intercepted (Status = -5)")

    def test_05_rust_topological_betti_guard(self):
        """Suite 5: Rust Topological Guard (Betti-1 & Disconnected Graph Detection)."""
        print("\n--- SUITE 5: Rust Algebraic Topology Invariant Guard ---")
        N = 5
        # Fully connected graph adjacency
        adj_connected = np.ones((N, N), dtype=np.float64)
        status_c = self.engine.rust_lib.polydim_rust_betti1_guard(
            adj_connected.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_size_t(N),
            ctypes.c_double(0.5)
        )
        self.assertEqual(status_c, 0, "Connected swarm topology must pass with status 0")
        print("  [PASS] Connected topology passed (Status = 0)")

        # Disconnected graph adjacency (two isolated clusters)
        adj_disconnected = np.zeros((N, N), dtype=np.float64)
        adj_disconnected[0:2, 0:2] = 1.0 # Cluster 1
        adj_disconnected[2:5, 2:5] = 1.0 # Cluster 2
        status_d = self.engine.rust_lib.polydim_rust_betti1_guard(
            adj_disconnected.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
            ctypes.c_size_t(N),
            ctypes.c_double(0.5)
        )
        self.assertEqual(status_d, -6, "Disconnected swarm must be flagged with ErrTopologyFragmented (-6)")
        print("  [PASS] Fragmented topology intercepted (Status = -6)")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPolydimV761Physical)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n=================================================================")
    print(">>> POLYDIM V761: ALL 5 PHYSICAL SILICON SUITES PASSED (EXIT 0) <<<")
    print("=================================================================")
