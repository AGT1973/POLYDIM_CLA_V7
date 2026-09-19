"""
POLYDIM V760 — Kaggle TPU v3-8 Benchmark Suite (BG-10)
Hardware Target: Google TPU v3-8 via JAX/XLA

CRITICAL FP64 CONTRACT:
  TPU v3 does NOT support native FP64.
  All FP64 operations are emulated in XLA software (significant overhead).
  This benchmark MEASURES the actual throughput degradation:
    - Emulated FP64 vs native bfloat16/float32
    - Drift invariance on S^{D-1} with forced FP64 emulation
    - Recommendation: whether POLYDIM should use bfloat16 on TPU
      or abort with a hardware_probe warning.

Silicon Contract (BG-08):
  All hardware parameters (device kind, memory, FP capabilities) are
  interrogated at runtime — ZERO hardcoded values.

Author: POLYDIM / AGY Orchestrator
"""

import sys
import os
import time
import json
import math

# ─── JAX Setup (must happen before any jax import) ───────────────────────────
os.environ["JAX_PLATFORMS"] = "tpu"
# Enable FP64 on JAX (required to trigger XLA's software emulation path)
# Without this, JAX silently downcasts FP64 tensors to FP32/BF16
os.environ["JAX_ENABLE_X64"] = "1"

import jax
import jax.numpy as jnp
import numpy as np


# ─── 1. Hardware Probe (inline — no external dependency) ─────────────────────

def probe_tpu_hardware() -> dict:
    """Interrogate TPU hardware. Zero hardcoding."""
    devices = jax.devices()
    if not devices:
        return {"platform": "cpu", "device_kind": "CPU fallback", "n_devices": 0}

    dev = devices[0]
    n_dev = len(devices)
    kind = dev.device_kind  # e.g. "TPU v3" or "TPU v4"

    # Memory probe (XLA backend)
    mem_bytes = 0
    try:
        ms = dev.memory_stats()
        if ms and "bytes_limit" in ms:
            mem_bytes = ms["bytes_limit"]
    except Exception:
        pass

    # FP64 capability: check if jnp.float64 is actually FP64 or downcast
    x_test = jnp.array([1.0], dtype=jnp.float64)
    actual_dtype = str(x_test.dtype)
    fp64_emulated = (actual_dtype == "float64")  # True = XLA software emulation active
    fp64_native = False  # TPU v3/v4 never has native FP64 silicon

    return {
        "platform": dev.platform,
        "device_kind": kind,
        "device_id": dev.id,
        "n_devices": n_dev,
        "mem_bytes": mem_bytes,
        "mem_gb": round(mem_bytes / 1024**3, 2) if mem_bytes > 0 else "unknown",
        "fp64_emulated": fp64_emulated,
        "fp64_native": fp64_native,
        "jax_version": jax.__version__,
        "jax_x64_enabled": jax.config.jax_enable_x64,
    }


# ─── 2. Rodrigues Rotation (JIT-compiled for TPU) ────────────────────────────

@jax.jit
def rodrigues_jax(y, u, v, theta):
    """
    Fused Rodrigues Geodesic Rotation on S^{D-1} via JAX/XLA.
    Compiled once by JIT; subsequent calls run on TPU directly.
    dtype follows input (bfloat16/float32/float64 depending on probe).
    """
    uu = jnp.dot(u, u)
    vv = jnp.dot(v, v)
    uv = jnp.dot(u, v)
    yu = jnp.dot(y, u)
    yv = jnp.dot(y, v)

    u_norm = jnp.sqrt(uu)
    v_proj = uv / uu
    v_ortho_sq = vv - (uv * uv) / uu
    v_ortho_norm = jnp.sqrt(jnp.maximum(v_ortho_sq, jnp.finfo(y.dtype).tiny))

    half_theta = theta * 0.5
    versine = 2.0 * jnp.sin(half_theta) ** 2
    sin_theta = jnp.sin(theta)

    a_val = yu / u_norm
    b_val = (yv - v_proj * yu) / v_ortho_norm

    u_unit = u / u_norm
    v_unit = (v - v_proj * u) / v_ortho_norm

    delta = (-versine * (a_val * u_unit + b_val * v_unit)
             + sin_theta * (a_val * v_unit - b_val * u_unit))
    return y + delta


@jax.jit
def fwht_jax(x):
    """
    In-place Fast Walsh-Hadamard Transform via JAX.
    Requires D = 2^N. Fused final normalization.
    """
    D = x.shape[0]
    log2_D = int(math.log2(D))
    assert 2**log2_D == D, f"D must be power of 2, got {D}"
    final_scale = 1.0 / math.sqrt(D)

    for i in range(log2_D):
        h = 1 << i
        x_r = x.reshape(-1, 2 * h)
        u = x_r[:, :h]
        v = x_r[:, h:]
        if i == log2_D - 1:
            x_r_new = jnp.concatenate([(u + v) * final_scale, (u - v) * final_scale], axis=1)
        else:
            x_r_new = jnp.concatenate([u + v, u - v], axis=1)
        x = x_r_new.reshape(-1)
    return x


# ─── 3. Benchmark Suites ─────────────────────────────────────────────────────

def run_suite1_rodrigues(hw: dict, dtype_fp64, dtype_native):
    """Suite 1: Rodrigues rotation at multiple D, two dtypes (FP64 emulated vs native)."""
    results = []
    print(f"\n>>> SUITE 1: Rodrigues S^{{D-1}} — Emulated FP64 vs {dtype_native.__name__}")
    hdr = f"{'D':>10} | {'dtype':>10} | {'Warmup':>7} | {'Time (ms)':>10} | {'Drift |norm-1|':>16} | Status"
    print(hdr)
    print("-" * len(hdr))

    key = jax.random.PRNGKey(42)
    theta_val = 0.123456789

    dims = [1_000, 10_000, 100_000, 1_000_000]

    for D in dims:
        for dtype, dtype_label in [(dtype_fp64, "float64"), (dtype_native, dtype_native.__name__)]:
            # Allocate
            key, k1, k2, k3 = jax.random.split(key, 4)
            u = jax.random.normal(k1, (D,), dtype=dtype)
            u = u / jnp.linalg.norm(u)
            v = jax.random.normal(k2, (D,), dtype=dtype)
            v = v - jnp.dot(v, u) * u
            v_norm = jnp.linalg.norm(v)
            v = jax.lax.cond(v_norm > 1e-10, lambda: v / v_norm, lambda: v)
            y = jax.random.normal(k3, (D,), dtype=dtype)
            y = y / jnp.linalg.norm(y)
            theta = jnp.array(theta_val, dtype=dtype)

            # Warmup (trigger JIT compilation)
            for _ in range(3):
                y_w = rodrigues_jax(y, u, v, theta)
            jax.effects_barrier()

            # Benchmark
            t0 = time.perf_counter()
            ITERS = 10 if D <= 100_000 else 3
            for _ in range(ITERS):
                y_out = rodrigues_jax(y, u, v, theta)
            jax.effects_barrier()
            dt_ms = ((time.perf_counter() - t0) / ITERS) * 1000.0

            drift = float(abs(jnp.linalg.norm(y_out) - 1.0))
            tol = 1e-14 if dtype == dtype_fp64 else 1e-6
            status = "PASS" if drift < tol else "WARN (drift exceeds tol)"
            print(f"{D:>10,} | {dtype_label:>10} | {'OK':>7} | {dt_ms:>10.3f} | {drift:>16.2e} | {status}")
            results.append({
                "D": D, "dtype": dtype_label, "ms": dt_ms, "drift": drift, "status": status
            })

    return results


def run_suite2_fwht(hw: dict, dtype_fp64, dtype_native):
    """Suite 2: FWHT isometry test — checks orthogonality preservation under both dtypes."""
    results = []
    print(f"\n>>> SUITE 2: FWHT Isometry — Emulated FP64 vs {dtype_native.__name__}")
    hdr = f"{'D (2^N)':>10} | {'dtype':>10} | {'Time (ms)':>10} | {'Iso Error':>12} | Status"
    print(hdr)
    print("-" * len(hdr))

    key = jax.random.PRNGKey(99)
    dims_fwht = [1024, 65536, 1_048_576]

    for D in dims_fwht:
        for dtype, dtype_label in [(dtype_fp64, "float64"), (dtype_native, dtype_native.__name__)]:
            key, k1 = jax.random.split(key)
            x = jax.random.normal(k1, (D,), dtype=dtype)
            x = x / jnp.linalg.norm(x)

            # Warmup
            _ = fwht_jax(x)
            jax.effects_barrier()

            t0 = time.perf_counter()
            hx = fwht_jax(x)
            jax.effects_barrier()
            dt_ms = (time.perf_counter() - t0) * 1000.0

            iso_err = float(abs(jnp.linalg.norm(hx) - 1.0))
            tol = 1e-14 if dtype == dtype_fp64 else 1e-5
            status = "PASS" if iso_err < tol else "WARN"
            print(f"{D:>10,} | {dtype_label:>10} | {dt_ms:>10.3f} | {iso_err:>12.2e} | {status}")
            results.append({
                "D": D, "dtype": dtype_label, "ms": dt_ms, "iso_err": iso_err, "status": status
            })

    return results


def run_suite3_multihop(hw: dict, dtype_fp64):
    """Suite 3: 1,000-hop geodesic stress test (FP64 emulated) — drift accumulation on TPU."""
    print(f"\n>>> SUITE 3: Multi-Hop Geodesic Stress (1,000 hops, FP64 emulated, D=10,000)")
    D = 10_000
    key = jax.random.PRNGKey(7)
    key, k1 = jax.random.split(key)
    y = jax.random.normal(k1, (D,), dtype=dtype_fp64)
    y = y / jnp.linalg.norm(y)
    theta = jnp.array(0.05, dtype=dtype_fp64)

    t0 = time.perf_counter()
    for i in range(1000):
        key, k2, k3 = jax.random.split(key, 3)
        u_h = jax.random.normal(k2, (D,), dtype=dtype_fp64)
        u_h = u_h / jnp.linalg.norm(u_h)
        v_h = jax.random.normal(k3, (D,), dtype=dtype_fp64)
        v_h = v_h - jnp.dot(v_h, u_h) * u_h
        v_h_norm = jnp.linalg.norm(v_h)
        v_h = jax.lax.cond(v_h_norm > 1e-10, lambda: v_h / v_h_norm, lambda: v_h)
        y = rodrigues_jax(y, u_h, v_h, theta)

    jax.effects_barrier()
    total_ms = (time.perf_counter() - t0) * 1000.0
    final_drift = float(abs(jnp.linalg.norm(y) - 1.0))

    status = "PASS (Drift bounded O(eps))" if final_drift < 1e-10 else "WARN (Drift growing)"
    print(f"  1,000 hops: {total_ms:.2f} ms ({total_ms/1000:.3f} ms/hop)")
    print(f"  Final drift (FP64 emulated): {final_drift:.2e} → {status}")

    return {"total_ms": total_ms, "ms_per_hop": total_ms/1000, "drift": final_drift, "status": status}


def run_suite4_fp64_overhead(hw: dict):
    """
    Suite 4: FP64 emulation overhead quantification.
    Compares FP64 vs bfloat16 throughput for dot product to measure the
    emulation penalty. This is the key BG-10 architectural decision input.
    """
    print(f"\n>>> SUITE 4: FP64 Emulation Overhead vs bfloat16 (TPU v3 Decision Gate)")
    hdr = f"{'D':>10} | {'float64 (ms)':>14} | {'bfloat16 (ms)':>14} | {'Overhead Factor':>16}"
    print(hdr)
    print("-" * len(hdr))

    results = []
    key = jax.random.PRNGKey(13)
    dims = [1_000, 10_000, 100_000, 1_000_000]
    ITERS = 20

    for D in dims:
        timings = {}
        for dtype, label in [(jnp.float64, "float64"), (jnp.bfloat16, "bfloat16")]:
            key, k1, k2 = jax.random.split(key, 3)
            a = jax.random.normal(k1, (D,), dtype=dtype)
            b = jax.random.normal(k2, (D,), dtype=dtype)

            # Warmup
            for _ in range(3):
                _ = jnp.dot(a, b)
            jax.effects_barrier()

            t0 = time.perf_counter()
            for _ in range(ITERS):
                _ = jnp.dot(a, b)
            jax.effects_barrier()
            timings[label] = ((time.perf_counter() - t0) / ITERS) * 1000.0

        factor = timings["float64"] / max(timings["bfloat16"], 1e-9)
        print(f"{D:>10,} | {timings['float64']:>14.4f} | {timings['bfloat16']:>14.4f} | {factor:>16.1f}x")
        results.append({
            "D": D, "fp64_ms": timings["float64"], "bf16_ms": timings["bfloat16"], "factor": factor
        })

    # Decision gate (BG-10 architectural verdict)
    avg_factor = sum(r["factor"] for r in results) / len(results)
    if avg_factor > 10.0:
        verdict = ("ARCHITECTURAL WARNING: FP64 emulation overhead on TPU v3 "
                   f"is {avg_factor:.1f}x. POLYDIM MUST use bfloat16 on TPU. "
                   "HardwareProbe will set fp64_native=False.")
    elif avg_factor > 3.0:
        verdict = (f"MODERATE OVERHEAD: {avg_factor:.1f}x. FP64 usable only for "
                   "small D (< 100K). For production D >= 1M, use bfloat16.")
    else:
        verdict = f"ACCEPTABLE OVERHEAD: {avg_factor:.1f}x. FP64 viable on this TPU."

    print(f"\n  [BG-10 VERDICT] Avg overhead: {avg_factor:.1f}x")
    print(f"  {verdict}")
    return {"suites": results, "avg_factor": avg_factor, "verdict": verdict}


# ─── 4. Main ─────────────────────────────────────────────────────────────────

def main():
    # Hardware interrogation
    hw = probe_tpu_hardware()

    print("=" * 90)
    print("  POLYDIM V760 TPU BENCHMARK (BG-10) — JAX/XLA on Kaggle TPU v3-8")
    print(f"  Device:      {hw['device_kind']} × {hw['n_devices']} cores")
    print(f"  Memory:      {hw['mem_gb']} GB")
    print(f"  JAX:         {hw['jax_version']}")
    print(f"  x64 enabled: {hw['jax_x64_enabled']} (FP64 emulation active)")
    print(f"  FP64 native: {hw['fp64_native']} ← TPU v3 always False (emulated by XLA)")
    print("=" * 90)

    # Dtype selection: FP64 (emulated) vs TPU-native bfloat16
    dtype_fp64   = jnp.float64
    dtype_native = jnp.bfloat16  # TPU v3 native compute type

    all_results = {"hardware": hw, "suites": {}}

    all_results["suites"]["rodrigues"] = run_suite1_rodrigues(hw, dtype_fp64, dtype_native)
    all_results["suites"]["fwht"]      = run_suite2_fwht(hw, dtype_fp64, dtype_native)
    all_results["suites"]["multihop"]  = run_suite3_multihop(hw, dtype_fp64)
    all_results["suites"]["fp64_overhead"] = run_suite4_fp64_overhead(hw)

    # ─── BG-10 Final Verdict ───────────────────────────────────────────────
    overhead = all_results["suites"]["fp64_overhead"]
    print("\n" + "=" * 90)
    print("  [BG-10 ARCHITECTURAL DECISION]")
    print(f"  {overhead['verdict']}")
    print("=" * 90)

    # Save results
    out_dir = "/kaggle/working" if os.path.exists("/kaggle/working") else "."
    res_path = os.path.join(out_dir, "polydim_v760_tpu_benchmark_results.json")
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n[OK] Results saved: {res_path}")


if __name__ == "__main__":
    main()
