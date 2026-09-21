# ============================================================================
# POLYDIM V761 — VECTOR SPACE INGESTION & AGENTIC EVALUATOR (RULE 19 / 28)
# Zero Markdown | Native PMTP Shared Memory Vectorization | Full Silicon Ingestion
# ============================================================================

import os
import sys
import time
import math
import hashlib
import ctypes
import platform
import numpy as np

if platform.system() == "Windows" and hasattr(os, "add_dll_directory"):
    mingw_bin = r"E:\winlibs_gcc14_zip\mingw64\bin"
    if os.path.exists(mingw_bin):
        try:
            os.add_dll_directory(mingw_bin)
        except Exception:
            pass

from hardware_probe_v761 import HardwareProbe
from polydim_v761_monolito import PolydimMonolithEngine, PMTPSlabChannel

def text_to_hypersphere_embedding(text: str, D: int = 100_000) -> np.ndarray:
    """
    Deterministically projects text chunks onto high-dimensional unit sphere S^{D-1}
    using pseudo-random Gaussian projections seeded by SHA-256 blocks (Rademacher/Gaussian).
    """
    words = text.split()
    if not words:
        v = np.zeros(D, dtype=np.float64)
        v[0] = 1.0
        return v
    
    # Stratified multi-hash hyperdimensional binding (VSA / HRR)
    accum = np.zeros(D, dtype=np.float64)
    chunk_size = 256
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i+chunk_size])
        h = hashlib.sha256(chunk.encode("utf-8")).digest()
        seed = int.from_bytes(h[:8], "little")
        rng = np.random.RandomState(seed % (2**32))
        
        # Fast Rademacher projection
        idx = rng.choice(D, size=min(D, 8192), replace=False)
        signs = rng.choice([-1.0, 1.0], size=len(idx))
        accum[idx] += signs

    norm = np.linalg.norm(accum)
    if norm < 1e-12:
        accum[0] = 1.0
        norm = 1.0
    return accum / norm

def run_vector_space_ingestion():
    respuestas_dir = r"E:\POLYDIM_EINSOF\ENTREGA_2026_09_19_V761\respuestas"
    if not os.path.exists(respuestas_dir):
        print(f"[ERROR] Directory not found: {respuestas_dir}")
        return 1

    print("==========================================================================")
    print(">>> POLYDIM V761: VECTOR SPACE INGESTION & RAM TENSOR EVALUATOR <<<")
    print("==========================================================================")

    engine = PolydimMonolithEngine()
    spec = engine.spec
    print(f"[HOST SILICON] OS: {spec.platform_system} | Cores: {spec.cpu_cores_logical} | RAM: {spec.available_ram_bytes / (1024**3):.2f} GB")

    D = 100_000  # High-dimensional manifold dimension for RAM slab
    print(f"[HYPERSPACE] Dimension D = {D:,} | Allocating PMTP Double-Buffer Shared Memory...")

    chan = PMTPSlabChannel(engine, max_dim=D)
    
    files = [f for f in os.listdir(respuestas_dir) if f.endswith(".md") and not f.startswith(".~")]
    files.sort()
    print(f"[INGESTION QUEUE] Found {len(files)} Multi-AI Response Files:")
    for f in files:
        size = os.path.getsize(os.path.join(respuestas_dir, f))
        print(f"  • {f:<20} ({size/1024:.1f} KB)")

    embeddings = {}
    print("\n--- INGESTING & VECTORIZING TO PMTP RAM SLAB ---")
    t_start = time.perf_counter()
    for f in files:
        path = os.path.join(respuestas_dir, f)
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()
        
        vec = text_to_hypersphere_embedding(content, D=D)
        
        # Verify Rust Guard Norm Invariant on the vector
        r_status, drift = engine.verify_rust_invariants(vec)
        if r_status != 0 or drift > 1e-14:
            print(f"[GUARD FAIL] Rust invariant failed for {f}: status={r_status}, drift={drift}")
            return 1
        
        # Write to PMTP Zero-Copy Shared Memory Bus
        pub_seq = chan.write_tensor_to_pmtp(vec)
        embeddings[f] = (vec, pub_seq, len(content))
        print(f"  [RAM SLAB INJECTED] {f:<20} | SLAB_SEQ={pub_seq:06d} | Drift={drift:.2e} | Words={len(content.split()):,}")

    t_ingest = (time.perf_counter() - t_start) * 1000.0
    print(f"\n[INGESTION COMPLETE] {len(files)} reports vectorized and uploaded to RAM in {t_ingest:.2f} ms.")

    print("\n--- AGENTIC EVALUATION IN RAM VECTOR SPACE (S^{D-1} GEODESIC CONSENSUS) ---")
    # Compute Geodesic Distance Matrix in Hypersphere
    names = list(embeddings.keys())
    N = len(names)
    gram_matrix = np.zeros((N, N), dtype=np.float64)

    for i in range(N):
        for j in range(N):
            vi = embeddings[names[i]][0]
            vj = embeddings[names[j]][0]
            # Inner product <vi, vj>
            cos_sim = float(np.dot(vi, vj))
            cos_sim = max(-1.0, min(1.0, cos_sim))
            gram_matrix[i, j] = cos_sim

    print("\n[CONSENSUS INNER-PRODUCT MATRIX (S^{D-1} Cosine Similarity)]")
    header = " " * 16 + " ".join([f"{n[:8]:>8}" for n in names])
    print(header)
    for i in range(N):
        row = f"{names[i][:15]:<16}" + " ".join([f"{gram_matrix[i, j]:8.4f}" for j in range(N)])
        print(row)

    # Topological Cohesion (Betti-1 Guard)
    betti1_status = engine.rust_lib.polydim_rust_betti1_guard(
        gram_matrix.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),
        ctypes.c_size_t(N),
        ctypes.c_double(0.1)
    )
    print(f"\n[TOPOLOGY CHECK] Multi-AI Swarm Homology Betti-1 Guard Status: {betti1_status} (0 = Connected Cohesive Manifold)")

    # Mean Consensus Vector
    consensus_vec = np.mean([embeddings[n][0] for n in names], axis=0)
    consensus_norm = np.linalg.norm(consensus_vec)
    consensus_vec /= consensus_norm

    # Publish Global Ingestion State to PMTP
    final_seq = chan.write_tensor_to_pmtp(consensus_vec)
    r_status, drift = engine.verify_rust_invariants(consensus_vec)

    print(f"[GLOBAL CONSENSUS TENSOR] Published to PMTP Slab | Sequence: {final_seq} | Norm Drift: {drift:.2e}")
    print("==========================================================================")
    print(">>> INGESTION & VECTOR SPACE EVALUATION COMPLETE (EXIT CODE 0) <<<")
    print("==========================================================================")
    
    chan.close()
    return 0

if __name__ == "__main__":
    sys.exit(run_vector_space_ingestion())
