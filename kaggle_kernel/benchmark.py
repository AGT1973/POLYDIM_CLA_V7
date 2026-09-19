import subprocess, sys
# Force CUDA PyTorch on Kaggle GPU runner
try:
    import torch
    if not torch.cuda.is_available():
        print('[!] CUDA not available, installing torch+cu121...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
            'torch', '--index-url', 'https://download.pytorch.org/whl/cu121'])
        print('[OK] torch+cu121 installed')
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q',
        'torch', '--index-url', 'https://download.pytorch.org/whl/cu121'])
    print('[OK] torch+cu121 installed from scratch')

"""
POLYDIM V755 - CLOUD GPU BENCHMARK SUITE (KAGGLE RUNNER)
Hardware Target: NVIDIA Tesla T4 / P100 / A100 (CUDA / Triton / PyTorch FP64)
Validates High-Dimensional Spherical Geometry S^{D-1} at Silicon Scale.
"""

import sys
import os
import time
import math
import json
import torch

def get_hardware_info():
    info = {
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "torch_version": torch.__version__,
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        info["total_memory_gb"] = round(props.total_memory / (1024**3), 2)
        info["compute_capability"] = f"{props.major}.{props.minor}"
    return info

def rodrigues_pytorch_gpu(y, u, v, theta):
    """
    Fused Rodrigues Geodesic Rotation on S^{D-1} in pure FP64 CUDA tensor math.
    Zero 1D text collapse. Direct high-dimensional manifold operation.
    """
    # Pass 1: Reductions in FP64
    uu = torch.dot(u, u)
    vv = torch.dot(v, v)
    uv = torch.dot(u, v)
    yu = torch.dot(y, u)
    yv = torch.dot(y, v)

    u_norm = torch.sqrt(uu)
    v_proj = uv / uu
    v_ortho_norm_sq = vv - (uv * uv) / uu
    v_ortho_norm = torch.sqrt(torch.clamp(v_ortho_norm_sq, min=1e-30))

    # Kahan Versine
    half_theta = theta * 0.5
    versine = 2.0 * (torch.sin(half_theta) ** 2)
    sin_theta = torch.sin(theta)

    a_val = yu / u_norm
    b_val = (yv - v_proj * yu) / v_ortho_norm

    # Pass 2: Tangent Space Projection & Update
    u_unit = u / u_norm
    v_unit = (v - v_proj * u) / v_ortho_norm

    delta = -versine * (a_val * u_unit + b_val * v_unit) + sin_theta * (a_val * v_unit - b_val * u_unit)
    y_next = y + delta
    return y_next

def fwht_pytorch_gpu(x):
    """
    In-place Fast Walsh-Hadamard Transform on GPU with fused final normalization.
    """
    D = x.numel()
    h = 1
    x = x.clone()
    final_scale = 1.0 / math.sqrt(D)
    while h < D:
        # Reshape to butterfly blocks
        x = x.view(-1, 2 * h)
        u = x[:, :h].clone()
        v = x[:, h:].clone()
        if (h * 2) == D:
            x[:, :h] = (u + v) * final_scale
            x[:, h:] = (u - v) * final_scale
        else:
            x[:, :h] = u + v
            x[:, h:] = u - v
        h *= 2
    return x.view(-1)

def cholqr2_pytorch_gpu(X):
    """
    Twice-Iterated Cholesky QR on GPU (K x D).
    Computes Q such that Q Q^T = I_K.
    """
    # Iteration 1
    G1 = torch.mm(X, X.T)
    L1 = torch.linalg.cholesky(G1)
    Q1 = torch.linalg.solve_triangular(L1, X, upper=False)

    # Iteration 2
    G2 = torch.mm(Q1, Q1.T)
    L2 = torch.linalg.cholesky(G2)
    Q2 = torch.linalg.solve_triangular(L2, Q1, upper=False)
    return Q2

def main():
    hw = get_hardware_info()
    device = torch.device("cuda" if hw["cuda_available"] else "cpu")

    print("=" * 95)
    print(f"     POLYDIM V755 CLOUD SILICON BENCHMARK (KAGGLE GPU ENGINE)")
    print(f"     Hardware: {hw['device_name']} | Memory: {hw.get('total_memory_gb', 'N/A')} GB | PyTorch: {hw['torch_version']}")
    print("=" * 95)

    results = {"hardware": hw, "suites": {}}

    # -------------------------------------------------------------------------
    # SUITE 1: RODRIGUES ROTATION ON S^{D-1}
    # -------------------------------------------------------------------------
    print(f"\n>>> SUITE 1: Rotacion Geodesica en S^{{D-1}} (FP64 en {hw['device_name']})")
    header1 = f"{'D':>10} | {'Warmup':<7} | {'Tiempo (ms)':>11} | {'Throughput (GB/s)':>18} | {'Drift (|norm-1|)':>18} | {'Status'}"
    print(header1)
    print("-" * len(header1))

    suite1_res = []
    dims = [1_000, 10_000, 100_000, 1_000_000, 5_000_000, 10_000_000]
    theta = torch.tensor(0.123456789, dtype=torch.float64, device=device)

    for D in dims:
        # Check memory limit before allocating D=10M FP64
        needed_gb = (3 * D * 8) / (1024**3)
        if hw["cuda_available"] and needed_gb > hw["total_memory_gb"] * 0.7:
            print(f"{D:>10,} | SKIP (Exceeds 70% VRAM)")
            continue

        u = torch.randn(D, dtype=torch.float64, device=device); u /= torch.linalg.norm(u)
        v = torch.randn(D, dtype=torch.float64, device=device); v -= torch.dot(v, u) * u; v /= torch.linalg.norm(v)
        y = torch.randn(D, dtype=torch.float64, device=device); y /= torch.linalg.norm(y)

        # Warmup
        for _ in range(5):
            _ = rodrigues_pytorch_gpu(y, u, v, theta)
        if hw["cuda_available"]: torch.cuda.synchronize()

        # Benchmark
        t0 = time.perf_counter()
        iters = 20 if D <= 100_000 else 5
        for _ in range(iters):
            y_rot = rodrigues_pytorch_gpu(y, u, v, theta)
        if hw["cuda_available"]: torch.cuda.synchronize()
        dt_ms = ((time.perf_counter() - t0) / iters) * 1000.0

        drift = abs(torch.linalg.norm(y_rot).item() - 1.0)
        bytes_trans = 3 * D * 8  # y, u, v
        throughput = (bytes_trans / (dt_ms / 1000.0)) / (1024**3) if dt_ms > 0 else 0.0

        status = "PASS (FP64 Exact)" if drift < 1e-14 else "FAIL"
        print(f"{D:>10,} | {'OK':<7} | {dt_ms:>11.3f} | {throughput:>18.2f} | {drift:>18.2e} | {status}")
        suite1_res.append({"D": D, "ms": dt_ms, "gb_s": throughput, "drift": drift})

    results["suites"]["rodrigues"] = suite1_res

    # -------------------------------------------------------------------------
    # SUITE 2: MULTI-HOP 1,000 ROTATIONS STRESS
    # -------------------------------------------------------------------------
    print(f"\n>>> SUITE 2: Multi-Hop Geodesic Stress (1,000 Rotaciones Consecutivas en D=50,000)")
    D_hop = 50_000
    y_hop = torch.randn(D_hop, dtype=torch.float64, device=device); y_hop /= torch.linalg.norm(y_hop)
    theta_hop = torch.tensor(0.05, dtype=torch.float64, device=device)

    t0_hop = time.perf_counter()
    for _ in range(1000):
        u_h = torch.randn(D_hop, dtype=torch.float64, device=device); u_h /= torch.linalg.norm(u_h)
        v_h = torch.randn(D_hop, dtype=torch.float64, device=device); v_h -= torch.dot(v_h, u_h) * u_h; v_h /= torch.linalg.norm(v_h)
        y_hop = rodrigues_pytorch_gpu(y_hop, u_h, v_h, theta_hop)
    if hw["cuda_available"]: torch.cuda.synchronize()
    total_hop_ms = (time.perf_counter() - t0_hop) * 1000.0
    drift_hop = abs(torch.linalg.norm(y_hop).item() - 1.0)

    print(f"  - 1,000 Rotaciones completadas en: {total_hop_ms:.2f} ms ({total_hop_ms/1000.0:.3f} ms/hop)")
    print(f"  - Deriva Acumulada Final tras 1,000 Hops: {drift_hop:.2e} -> {'PASS (Deriva Acotada O(eps))' if drift_hop < 1e-12 else 'FAIL'}")
    results["suites"]["multihop"] = {"total_ms": total_hop_ms, "ms_per_hop": total_hop_ms/1000.0, "final_drift": drift_hop}

    # -------------------------------------------------------------------------
    # SUITE 3: FAST WALSH-HADAMARD TRANSFORM (FWHT ISOMETRIA)
    # -------------------------------------------------------------------------
    print(f"\n>>> SUITE 3: Fast Walsh-Hadamard Transform (FWHT) Isometria en GPU")
    header3 = f"{'D (2^N)':>10} | {'Tiempo (ms)':>11} | {'Error de Isometria':>20} | {'Status'}"
    print(header3)
    print("-" * len(header3))

    suite3_res = []
    for D_fwht in [1024, 4096, 16384, 65536, 262144, 1048576]:
        x = torch.randn(D_fwht, dtype=torch.float64, device=device); x /= torch.linalg.norm(x)
        
        # Warmup
        _ = fwht_pytorch_gpu(x)
        if hw["cuda_available"]: torch.cuda.synchronize()

        t0 = time.perf_counter()
        hx = fwht_pytorch_gpu(x)
        if hw["cuda_available"]: torch.cuda.synchronize()
        dt_fwht = (time.perf_counter() - t0) * 1000.0

        iso_err = abs(torch.linalg.norm(hx).item() - 1.0)
        status = "PASS (Isometria OK)" if iso_err < 1e-14 else "FAIL"
        print(f"{D_fwht:>10,} | {dt_fwht:>11.3f} | {iso_err:>20.2e} | {status}")
        suite3_res.append({"D": D_fwht, "ms": dt_fwht, "error": iso_err})

    results["suites"]["fwht"] = suite3_res

    # -------------------------------------------------------------------------
    # SUITE 4: TWICE-ITERATED CHOLESKY QR (CHOLQR2 ORTOGONALIZACION)
    # -------------------------------------------------------------------------
    print(f"\n>>> SUITE 4: Twice-Iterated Cholesky QR (CholQR2) en GPU")
    header4 = f"{'K x D':>14} | {'Tiempo (ms)':>11} | {'||Q Q^T - I||_F':>20} | {'Status'}"
    print(header4)
    print("-" * len(header4))

    K = 8
    suite4_res = []
    for D_chol in [10_000, 100_000, 1_000_000]:
        X = torch.randn(K, D_chol, dtype=torch.float64, device=device)

        # Warmup
        _ = cholqr2_pytorch_gpu(X)
        if hw["cuda_available"]: torch.cuda.synchronize()

        t0 = time.perf_counter()
        Q = cholqr2_pytorch_gpu(X)
        if hw["cuda_available"]: torch.cuda.synchronize()
        dt_chol = (time.perf_counter() - t0) * 1000.0

        gram = torch.mm(Q, Q.T)
        eye = torch.eye(K, dtype=torch.float64, device=device)
        ortho_err = torch.linalg.norm(gram - eye).item()
        status = "PASS (Ortogonalidad OK)" if ortho_err < 1e-14 else "FAIL"
        print(f"{f'{K}x{D_chol:,}':>14} | {dt_chol:>11.3f} | {ortho_err:>20.2e} | {status}")
        suite4_res.append({"shape": f"{K}x{D_chol}", "ms": dt_chol, "ortho_err": ortho_err})

    results["suites"]["cholqr2"] = suite4_res

    # Save to working directory for export
    out_dir = "/kaggle/working" if os.path.exists("/kaggle/working") else "."
    res_path = os.path.join(out_dir, "polydim_v755_gpu_benchmark_results.json")
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Resultados guardados en {res_path}")

if __name__ == "__main__":
    main()
